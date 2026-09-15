"""JSON durch dieselbe persistente, geprüfte Tabellenpipeline."""

import os

import pytest
from test_database_integration import client_for
from test_database_integration import stack as database_stack  # noqa: F401
from test_large_data_integration import finish

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("database_stack"),
    pytest.mark.skipif(
        os.environ.get("RUN_DB_TESTS") != "1", reason="Echte PostgreSQL-Datenbank erforderlich"
    ),
]


@pytest.mark.parametrize(
    ("extension", "content"),
    [
        ("json", b'[{"Name":" Anna ","Wert":1.25},{"Wert":null,"Name":"Bob"}]'),
        ("jsonl", b'{"Name":" Anna ","Wert":1.25}\n{"Wert":null,"Name":"Bob"}\n'),
    ],
)
def test_json_upload_preview_commit_original_and_export(extension, content):
    with client_for("analyst") as client:
        upload = client.post(
            "/api/v1/data-uploads",
            json={
                "name": "Synthetischer JSON-Nachweis",
                "filename": "test." + extension,
                "total_bytes": len(content),
            },
        )
        assert upload.status_code == 201
        oid = upload.json()["id"]
        assert (
            client.put(f"/api/v1/data-uploads/{oid}/chunks/0", content=content).status_code == 200
        )
        queued = client.post(f"/api/v1/data-uploads/{oid}/complete")
        assert queued.status_code == 202
        job = finish(client, queued.json())
        assert job["status"] == "SUCCEEDED", job
        assert job["profile"]["source_format"] == extension
        assert job["profile"]["rows"] == 2
        did = job["dataset_id"]
        assert client.get(f"/api/v1/datasets/{did}/original").content == content
        with client_for("mandant-b") as other:
            assert other.get(f"/api/v1/datasets/{did}/original").status_code == 404
        preview = client.post(
            f"/api/v1/datasets/{did}/previews",
            json={
                "source_version": 1,
                "steps": [{"operation": "trim", "column": "Name"}],
            },
        )
        ready = finish(client, preview.json())
        assert ready["status"] == "SUCCEEDED"
        assert ready["profile"]["source_format"] == extension
        committed = client.post(
            f"/api/v1/datasets/{did}/versions",
            json={
                "preview_id": ready["id"],
                "result_hash": ready["result_hash"],
                "expected_current_version": 1,
            },
        )
        assert committed.status_code == 201
        exported = client.get(f"/api/v1/datasets/{did}/versions/2/export")
        assert b'"Anna";"1.25"' in exported.content
        assert client.get(f"/api/v1/datasets/{did}/original").content == content
