"""Abschnittsupload, RLS, Versionierung, Worker-Lease und echte Downloads."""

import hashlib
import os
from datetime import timedelta
from uuid import UUID

import pytest
from platform_app.data.models import DataJob
from platform_app.data.service import process_one
from platform_app.intake.models import now
from platform_app.shared.db import engine_for, tenant_session
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_database_integration import client_for
from test_database_integration import stack as database_stack  # noqa: F401

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("database_stack"),
    pytest.mark.skipif(
        os.environ.get("RUN_DB_TESTS") != "1", reason="Echte PostgreSQL-Testdatenbank erforderlich"
    ),
]
ORG = UUID("10000000-0000-4000-8000-000000000001")
CHUNK = 4194304


def start(client, size):
    response = client.post(
        "/api/v1/data-uploads",
        json={
            "name": "Synthetischer großer Import",
            "filename": "gross.csv",
            "total_bytes": size,
            "delimiter": ";",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, content):
    obj = start(client, len(content))
    for ordinal, offset in enumerate(range(0, len(content), CHUNK)):
        response = client.put(
            f"/api/v1/data-uploads/{obj['id']}/chunks/{ordinal}",
            content=content[offset : offset + CHUNK],
        )
        assert response.status_code == 200, response.text
    response = client.post(f"/api/v1/data-uploads/{obj['id']}/complete")
    assert response.status_code == 202, response.text
    return obj, response.json()


def finish(client, job):
    for _ in range(30):
        result = client.get(f"/api/v1/datasets/{job['dataset_id']}/jobs/{job['id']}").json()
        if result["status"] not in {"QUEUED", "RUNNING"}:
            return result
        process_one(ORG)
    raise AssertionError("Auftrag nicht abgeschlossen")


def test_multi_chunk_import_versions_original_export_paging_and_rls():
    content = b"Name;Betrag\n" + (b" Anna ;0.1\n" * 400000)
    with client_for("analyst") as client:
        obj, job = upload(client, content)
        repeated = client.post(f"/api/v1/data-uploads/{obj['id']}/complete")
        assert repeated.json()["id"] == job["id"]
        result = finish(client, job)
        assert result["status"] == "SUCCEEDED", result
        assert result["profile"]["rows"] == 400000 and result["profile"]["duplicate_rows"] == 399999
        assert result["profile"]["columns"][1]["mean"] == "0.100000"
        did = job["dataset_id"]
        original = client.get(f"/api/v1/datasets/{did}/original")
        assert original.content == content
        assert original.headers["x-content-sha256"] == hashlib.sha256(content).hexdigest()
        page = client.get(f"/api/v1/datasets/{did}/versions/1/rows?offset=399975").json()
        assert page["total"] == 400000 and len(page["rows"]) == 25
        preview = client.post(
            f"/api/v1/datasets/{did}/previews",
            json={
                "source_version": 1,
                "steps": [
                    {"operation": "trim", "column": "Name"},
                    {"operation": "drop_duplicates"},
                ],
            },
        )
        calculated = finish(client, preview.json())
        assert calculated["status"] == "SUCCEEDED", calculated
        assert calculated["profile"]["rows"] == 1
        response = client.post(
            f"/api/v1/datasets/{did}/versions",
            json={
                "preview_id": calculated["id"],
                "result_hash": calculated["result_hash"],
                "expected_current_version": 1,
            },
        )
        assert response.status_code == 201
        exported = client.get(f"/api/v1/datasets/{did}/versions/2/export")
        assert exported.content == b'\xef\xbb\xbf"Name";"Betrag"\r\n"Anna";"0.1"\r\n'
        assert exported.headers["x-content-sha256"] == hashlib.sha256(exported.content).hexdigest()
        assert client.get(f"/api/v1/datasets/{did}/original").content == content
        with client_for("mandant-b") as other:
            assert other.get(f"/api/v1/data-uploads/{obj['id']}").status_code == 404
            assert (
                other.put(f"/api/v1/data-uploads/{obj['id']}/chunks/0", content=b"x").status_code
                == 404
            )
            assert other.get(f"/api/v1/datasets/{did}/versions/1/export").status_code == 404
        with client_for("viewer") as viewer:
            assert viewer.get(f"/api/v1/datasets/{did}/versions/1/rows").status_code == 200
            assert viewer.post("/api/v1/data-uploads", json={}).status_code == 403


def test_chunks_retry_order_limits_cancel_and_csrf():
    with client_for("analyst") as client:
        obj = start(client, 4)
        path = f"/api/v1/data-uploads/{obj['id']}"
        assert client.put(path + "/chunks/1", content=b"ab").status_code == 409
        assert client.put(path + "/chunks/0", content=b"ab").status_code == 200
        assert client.put(path + "/chunks/0", content=b"ab").json()["received_bytes"] == 2
        assert client.put(path + "/chunks/0", content=b"cd").status_code == 409
        assert client.post(path + "/complete").status_code == 409
        assert client.put(path + "/chunks/1", content=b"123").status_code == 413
        assert (
            client.put(
                path + "/chunks/1", content=b"cd", headers={"X-CSRF-Token": "wrong"}
            ).status_code
            == 403
        )
        assert client.put(path + "/chunks/1", content=b"x" * (CHUNK + 1)).status_code == 413
        assert client.post(path + "/cancel").json()["status"] == "CANCELLED"
        assert client.post(path + "/cancel").status_code == 200
        assert client.put(path + "/chunks/1", content=b"cd").status_code == 409
        assert (
            client.post(
                "/api/v1/data-uploads",
                json={"name": "Test", "filename": "test.csv", "total_bytes": 1073741825},
            ).status_code
            == 422
        )
    with tenant_session(ORG) as db:
        assert (
            db.scalar(
                text("SELECT count(*) FROM data_chunks WHERE object_id=:id"),
                {"id": UUID(obj["id"])},
            )
            == 0
        )


def test_lease_recovery_and_job_cancellation():
    with client_for("analyst") as client:
        _, job = upload(client, b"A\n1\n")
        with tenant_session(ORG) as db:
            current = db.get(DataJob, UUID(job["id"]))
            current.status = "RUNNING"
            current.lease_token = UUID("99999999-0000-4000-8000-000000000001")
            current.lease_until = now() - timedelta(seconds=1)
            current.attempts = 1
        result = finish(client, job)
        assert result["status"] == "SUCCEEDED", result
        with tenant_session(ORG) as db:
            assert db.get(DataJob, UUID(job["id"])).attempts == 2
        _, cancelled = upload(client, b"A\n2\n")
        path = f"/api/v1/datasets/{cancelled['dataset_id']}/jobs/{cancelled['id']}"
        assert client.post(path + "/cancel").json()["status"] == "CANCELLED"
        process_one(ORG)
        assert client.get(path).json()["status"] == "CANCELLED"
        assert (
            client.get(f"/api/v1/datasets/{cancelled['dataset_id']}").json()["current_version"] == 0
        )


def test_chunk_database_immutability_and_fail_closed_context():
    with client_for("analyst") as client:
        obj, _ = upload(client, b"A\n1\n")
    with engine_for().connect() as db:
        assert db.scalar(text("SELECT count(*) FROM data_objects")) == 0
        assert db.scalar(text("SELECT count(*) FROM data_chunks")) == 0
    for sql in [
        "DELETE FROM data_chunks WHERE object_id=:id",
        "UPDATE data_objects SET status='OPEN' WHERE id=:id",
        "INSERT INTO data_chunks(organization_id,object_id,ordinal,content,content_hash) VALUES(:org,:id,1,'x'::bytea,repeat('a',64))",
    ]:
        with pytest.raises(DBAPIError), tenant_session(ORG) as db:
            db.execute(text(sql), {"id": UUID(obj["id"]), "org": ORG})


def test_open_uploads_can_be_found_after_reload():
    with client_for("analyst") as client:
        obj = start(client, 100)
        pending = client.get("/api/v1/data-uploads").json()["items"]
        selected = next(item for item in pending if item["id"] == obj["id"])
        assert selected["filename"] == "gross.csv" and selected["expected_bytes"] == 100
        with client_for("mandant-b") as other:
            assert all(
                item["id"] != obj["id"]
                for item in other.get("/api/v1/data-uploads").json()["items"]
            )
        client.post(f"/api/v1/data-uploads/{obj['id']}/cancel")


def test_cancel_during_computation_prevents_publication(monkeypatch):
    from platform_app.data import stream_worker

    original_build = stream_worker.build
    with client_for("analyst") as client:
        _, job = upload(client, b"A\n1\n")

        def cancel_during_build(*args, **kwargs):
            response = client.post(f"/api/v1/datasets/{job['dataset_id']}/jobs/{job['id']}/cancel")
            assert response.json()["status"] == "CANCELLED"
            return original_build(*args, **kwargs)

        monkeypatch.setattr(stream_worker, "build", cancel_during_build)
        result = finish(client, job)
        assert result["status"] == "CANCELLED"
        assert client.get(f"/api/v1/datasets/{job['dataset_id']}").json()["current_version"] == 0


def test_lost_worker_lease_cannot_publish(monkeypatch):
    from uuid import uuid4

    from platform_app.data import stream_worker

    original_build = stream_worker.build
    with client_for("analyst") as client:
        _, job = upload(client, b"A\n1\n")

        def replace_lease(*args, **kwargs):
            with tenant_session(ORG) as db:
                current = db.get(DataJob, UUID(job["id"]))
                current.lease_token = uuid4()
                current.lease_until = now() + timedelta(seconds=90)
            return original_build(*args, **kwargs)

        monkeypatch.setattr(stream_worker, "build", replace_lease)
        for _ in range(10):
            process_one(ORG)
            with tenant_session(ORG) as db:
                if db.get(DataJob, UUID(job["id"])).status == "RUNNING":
                    break
        assert client.get(f"/api/v1/datasets/{job['dataset_id']}").json()["current_version"] == 0
        client.post(f"/api/v1/datasets/{job['dataset_id']}/jobs/{job['id']}/cancel")
