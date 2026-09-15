"""Neuer Importversuch aus Originalbytes: Rechte, Idempotenz und vollständiger Ablauf."""

import os
from uuid import UUID

import pytest
from platform_app.data.models import DataJob
from platform_app.shared.db import tenant_session
from test_database_integration import client_for
from test_database_integration import stack as database_stack  # noqa: F401
from test_large_data_integration import finish, upload

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("database_stack"),
    pytest.mark.skipif(
        os.environ.get("RUN_DB_TESTS") != "1", reason="Echte PostgreSQL-Testdatenbank erforderlich"
    ),
]


def test_retry_preserves_failure_and_original_then_allows_transform():
    content = b"A,B\n1," + b"x" * 175026 + b"\n"
    with client_for("analyst") as client:
        _, first = upload(client, content)  # Bestehender Helfer wählt absichtlich Semikolon.
        failed = finish(client, first)
        assert failed["status"] == "FAILED" and "wahrscheinlich Komma" in failed["error"]
        did = first["dataset_id"]
        path = f"/api/v1/datasets/{did}/retry-import"
        assert client.post(path, json={}, headers={"X-CSRF-Token": "wrong"}).status_code == 403
        with client_for("viewer") as reader:
            assert reader.post(path, json={}).status_code == 403
        with client_for("mandant-b") as other:
            assert other.post(path, json={}).status_code == 404
        second = client.post(path, json={})
        assert second.status_code == 202, second.text
        assert client.post(path, json={}).json()["id"] == second.json()["id"]
        assert client.post(path, json={"delimiter": ";"}).status_code == 409
        success = finish(client, second.json())
        assert success["status"] == "SUCCEEDED", success
        assert success["profile"]["import_info"]["delimiter"] == ","
        assert client.get(f"/api/v1/datasets/{did}/original").content == content
        assert client.get(f"/api/v1/datasets/{did}/jobs/{first['id']}").json()["status"] == "FAILED"
        assert client.post(path, json={}).status_code == 409
        preview = client.post(
            f"/api/v1/datasets/{did}/previews",
            json={"source_version": 1, "steps": [{"operation": "uppercase", "column": "B"}]},
        )
        ready = finish(client, preview.json())
        assert ready["status"] == "SUCCEEDED", ready
        assert ready["profile"]["import_info"]["delimiter"] == ","
        committed = client.post(
            f"/api/v1/datasets/{did}/versions",
            json={
                "preview_id": ready["id"],
                "result_hash": ready["result_hash"],
                "expected_current_version": 1,
            },
        )
        assert committed.status_code == 201
        result = client.get(f"/api/v1/datasets/{did}/versions/2/export")
        assert b"X" * 175026 in result.content
        assert client.get(f"/api/v1/datasets/{did}/original").content == content
        with tenant_session(UUID("10000000-0000-4000-8000-000000000001")) as db:
            original = db.get(DataJob, UUID(first["id"]))
            assert original.import_options["delimiter"] == ";"
