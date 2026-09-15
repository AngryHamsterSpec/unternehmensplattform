"""Echte PostgreSQL-Transaktionen für CSV, Jobs, RLS und Versionsfreigabe."""

import base64
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
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
ORG_A = UUID("10000000-0000-4000-8000-000000000001")
SOURCE = b"Name;Ort\n Anna ;\nAnna;Berlin\n"


def upload(client, source=SOURCE):
    result = client.post(
        "/api/v1/datasets",
        json={
            "name": "Synthetischer Datentest " + str(uuid4()),
            "filename": "test.csv",
            "content_base64": base64.b64encode(source).decode(),
            "delimiter": ";",
        },
    )
    assert result.status_code == 202, result.text
    return result.json()


def finish(client, job):
    from platform_app.data.service import process_one

    for _ in range(15):
        current = client.get(f"/api/v1/datasets/{job['dataset_id']}/jobs/{job['id']}").json()
        if current["status"] != "QUEUED":
            return current
        process_one(ORG_A)
    raise AssertionError("Auftrag nicht abgeschlossen")


def preview(client, dataset_id):
    result = client.post(
        f"/api/v1/datasets/{dataset_id}/previews",
        json={
            "source_version": 1,
            "steps": [
                {"operation": "trim", "column": "Name"},
                {"operation": "fill_missing", "column": "Ort", "value": "Berlin"},
                {"operation": "drop_duplicates"},
            ],
        },
    )
    assert result.status_code == 202, result.text
    return finish(client, result.json())


def test_csv_full_flow_idempotence_original_export_and_tenants():
    with client_for("analyst") as client:
        initial = upload(client)
        did = initial["dataset_id"]
        result = finish(client, initial)
        assert result["status"] == "SUCCEEDED", result
        detail = client.get(f"/api/v1/datasets/{did}").json()
        original_hash = detail["original_hash"]
        assert detail["current_version"] == 1
        assert client.get(f"/api/v1/datasets/{did}/original").content == SOURCE
        candidate = preview(client, did)
        assert candidate["profile"]["rows"] == 1
        assert client.get(f"/api/v1/datasets/{did}").json()["current_version"] == 1
        body = {
            "preview_id": candidate["id"],
            "result_hash": candidate["result_hash"],
            "expected_current_version": 1,
        }
        assert (
            client.post(
                f"/api/v1/datasets/{did}/versions", json={**body, "result_hash": "0" * 64}
            ).status_code
            == 409
        )
        committed = client.post(f"/api/v1/datasets/{did}/versions", json=body)
        assert committed.status_code == 201 and committed.json()["version_no"] == 2
        assert client.post(f"/api/v1/datasets/{did}/versions", json=body).json() == committed.json()
        detail = client.get(f"/api/v1/datasets/{did}").json()
        assert (
            detail["original_hash"] == original_hash
            and detail["versions"][1]["profile"]["rows"] == 2
        )
        assert detail["versions"][0]["steps"][0]["operation"] == "trim"
        export = client.get(f"/api/v1/datasets/{did}/versions/2/export")
        assert export.status_code == 200 and b'"Anna";"Berlin"' in export.content
        assert client.get(f"/api/v1/datasets/{did}/versions/2/rows").json()["total"] == 1
        with client_for("viewer") as viewer:
            assert viewer.get(f"/api/v1/datasets/{did}").status_code == 200
            assert viewer.get(f"/api/v1/datasets/{did}/versions/2/export").status_code == 200
            assert viewer.post(f"/api/v1/datasets/{did}/versions", json=body).status_code == 403
            assert viewer.post("/api/v1/datasets", json={}).status_code == 403
        with client_for("mandant-b") as other:
            for path in [
                f"/{did}",
                f"/{did}/original",
                f"/{did}/jobs/{candidate['id']}",
                f"/{did}/versions/2/export",
                f"/{did}/versions/2/rows",
            ]:
                assert other.get("/api/v1/datasets" + path).status_code == 404
            assert other.post(f"/api/v1/datasets/{did}/versions", json=body).status_code == 404
            assert all(item["id"] != did for item in other.get("/api/v1/datasets").json()["items"])


def test_bad_csv_persists_failure_and_worker_continues():
    with client_for("analyst") as client:
        job = upload(client, b"a;b\n1")
        result = finish(client, job)
        assert result["status"] == "FAILED"
        assert "Spaltenanzahl" in result["error"]
        assert client.get(f"/api/v1/datasets/{job['dataset_id']}").json()["current_version"] == 0
        valid = upload(client)
        assert finish(client, valid)["status"] == "SUCCEEDED"


def test_database_immutability_and_no_context():
    from platform_app.shared.db import engine_for, tenant_session

    with client_for("analyst") as client:
        job = upload(client)
        finish(client, job)
    with engine_for().connect() as db:
        for table in ("datasets", "data_blobs", "data_jobs", "data_versions"):
            assert db.scalar(text(f"SELECT count(*) FROM {table}")) == 0
    for statement in (
        "UPDATE data_blobs SET content='changed'::bytea",
        "DELETE FROM data_versions",
        "UPDATE datasets SET original_hash='changed'",
        "UPDATE data_jobs SET status='FAILED', error='changed' WHERE status='SUCCEEDED'",
    ):
        with pytest.raises(DBAPIError), tenant_session(ORG_A) as db:
            db.execute(text(statement))


def test_concurrent_confirmation_and_stale_preview():
    with client_for("analyst") as client:
        job = upload(client)
        finish(client, job)
        did = job["dataset_id"]
        a, b = preview(client, did), preview(client, did)
        payload = {
            "preview_id": a["id"],
            "result_hash": a["result_hash"],
            "expected_current_version": 1,
        }

    def confirm():
        with client_for("analyst") as client:
            result = client.post(f"/api/v1/datasets/{did}/versions", json=payload)
            assert result.status_code == 201, result.text
            return result.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: confirm(), range(2)))
    assert results[0] == results[1]
    with client_for("analyst") as client:
        assert (
            client.post(
                f"/api/v1/datasets/{did}/versions",
                json={
                    **payload,
                    "preview_id": b["id"],
                    "result_hash": b["result_hash"],
                },
            ).status_code
            == 409
        )


def test_worker_rollback_leaves_job_retryable(monkeypatch):
    import platform_app.data.service as service
    from platform_app.data.models import DataJob
    from platform_app.shared.db import tenant_session

    with client_for("analyst") as client:
        job = upload(client)
        original = service.profile

        def crash(_):
            raise RuntimeError("synthetischer Prozessabbruch")

        with monkeypatch.context() as m:
            m.setattr(service, "profile", crash)
            with pytest.raises(RuntimeError):
                service.process_one(ORG_A)
        with tenant_session(ORG_A) as db:
            assert db.get(DataJob, UUID(job["id"])).status == "QUEUED"
        assert service.profile is original
        assert finish(client, job)["status"] == "SUCCEEDED"


def test_csrf_formula_export_and_unknown_column():
    with client_for("analyst") as client:
        payload = {"name": "Test", "filename": "test.csv", "content_base64": "YQo="}
        assert (
            client.post(
                "/api/v1/datasets", json=payload, headers={"X-CSRF-Token": "bad"}
            ).status_code
            == 403
        )
        job = upload(client, b"Name;Ort\n=1+1;@SUM(A1)\n")
        finish(client, job)
        did = job["dataset_id"]
        result = client.get(f"/api/v1/datasets/{did}/versions/1/export")
        assert result.headers["X-Protected-Cells"] == "2" and b"'=1+1" in result.content
        queued = client.post(
            f"/api/v1/datasets/{did}/previews",
            json={"source_version": 1, "steps": [{"operation": "trim", "column": "unbekannt"}]},
        )
        assert finish(client, queued.json())["status"] == "FAILED"


def test_revoked_writer_cannot_execute_saved_job_or_confirm():
    from fastapi import HTTPException
    from platform_app.data.models import DataJob
    from platform_app.data.router import upload as route_upload
    from platform_app.data.schemas import CommitInput, ImportInput
    from platform_app.data.service import commit_preview, process_one
    from platform_app.identity.dependencies import ActorContext
    from platform_app.identity.models import MembershipRole, OrganizationMembership, User
    from platform_app.intake.models import now
    from platform_app.shared.db import engine_for, tenant_session
    from sqlalchemy.orm import Session

    user_id = uuid4()
    with Session(engine_for("migration")) as db, db.begin():
        db.add(
            User(
                id=user_id,
                oidc_issuer="https://synthetic.invalid",
                oidc_subject=str(user_id),
                display_name="Synthetische Widerrufsprüfung",
            )
        )
        db.flush()
        db.add(OrganizationMembership(organization_id=ORG_A, user_id=user_id))
        db.flush()
        db.add(
            MembershipRole(organization_id=ORG_A, user_id=user_id, role_code="ARCHITECTURE_ANALYST")
        )
    actor = ActorContext(user_id, ORG_A, frozenset({"ARCHITECTURE_ANALYST"}), "Synthetischer Test")
    job = route_upload(
        ImportInput(
            name="Widerrufsprüfung",
            filename="test.csv",
            content_base64=base64.b64encode(SOURCE).decode(),
        ),
        actor,
    )
    with Session(engine_for("migration")) as db, db.begin():
        member = db.get(OrganizationMembership, (ORG_A, user_id))
        member.status, member.revoked_at = "REVOKED", now()
    assert process_one(ORG_A)
    with tenant_session(ORG_A) as db:
        assert db.get(DataJob, job.id).status == "FAILED"
    # Der vor dem Widerruf erhaltene ActorContext ist keine dauerhafte Freigabe.
    with pytest.raises(HTTPException) as denied, tenant_session(ORG_A) as db:
        commit_preview(
            db,
            actor,
            job.dataset_id,
            CommitInput(preview_id=job.id, result_hash="0" * 64, expected_current_version=1),
        )
    assert denied.value.status_code == 403


def test_cross_tenant_blob_reference_is_rejected_by_postgres():
    from platform_app.data.models import Dataset
    from platform_app.shared.db import tenant_session
    from sqlalchemy import select

    with client_for("analyst") as client:
        job = upload(client)
        finish(client, job)
    with tenant_session(ORG_A) as db:
        original = db.scalar(select(Dataset).where(Dataset.id == UUID(job["dataset_id"])))
        foreign_blob = original.original_blob_id
    with (
        pytest.raises(DBAPIError),
        tenant_session(UUID("10000000-0000-4000-8000-000000000002")) as db,
    ):
        db.add(
            Dataset(
                organization_id=UUID("10000000-0000-4000-8000-000000000002"),
                created_by_user_id=UUID("20000000-0000-4000-8000-000000000004"),
                name="Verbotener Querverweis",
                filename="test.csv",
                delimiter=";",
                original_blob_id=foreign_blob,
                original_hash="0" * 64,
                original_bytes=1,
            )
        )
        db.flush()
