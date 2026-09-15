"""SQLite-Snapshot durch echte RLS-/Worker-/Versions- und Exportpfade."""

import os
import sqlite3
from contextlib import closing

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


def test_sqlite_retry_preview_commit_tenant_roles_and_original(tmp_path):
    source = tmp_path / "source.db"
    with closing(sqlite3.connect(source)) as db:
        db.executescript(
            "CREATE TABLE Daten(Name TEXT, Wert); CREATE TABLE Hinweis(Text); INSERT INTO Daten VALUES (' Anna ', 1.25), ('Bob', NULL);"
        )
        db.commit()
    content = source.read_bytes()
    with client_for("analyst") as client:
        upload = client.post(
            "/api/v1/data-uploads",
            json={
                "name": "Synthetischer SQLite-Nachweis",
                "filename": "test.DB",
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
        failed = finish(client, queued.json())
        assert failed["status"] == "FAILED" and "Tabellennamen" in failed["error"]
        did = failed["dataset_id"]
        with client_for("mandant-b") as other:
            assert other.get(f"/api/v1/datasets/{did}/original").status_code == 404
            assert (
                other.post(
                    f"/api/v1/datasets/{did}/retry-import", json={"table_name": "Daten"}
                ).status_code
                == 404
            )
        with client_for("viewer") as viewer:
            assert (
                viewer.post(
                    f"/api/v1/datasets/{did}/retry-import", json={"table_name": "Daten"}
                ).status_code
                == 403
            )
        retry = client.post(f"/api/v1/datasets/{did}/retry-import", json={"table_name": "Daten"})
        assert retry.status_code == 202
        job = finish(client, retry.json())
        assert job["status"] == "SUCCEEDED", job
        assert job["import_options"]["table_name"] == "Daten"
        assert job["profile"]["source_format"] == "sqlite"
        assert job["profile"]["source_table"] == "Daten" and job["profile"]["rows"] == 2
        assert client.get(f"/api/v1/datasets/{did}/original").content == content
        preview = client.post(
            f"/api/v1/datasets/{did}/previews",
            json={
                "source_version": 1,
                "steps": [{"operation": "trim", "column": "Name"}],
            },
        )
        assert preview.status_code == 202
        ready = finish(client, preview.json())
        assert ready["status"] == "SUCCEEDED", ready
        assert ready["profile"]["source_table"] == "Daten"
        assert ready["profile"]["source_format"] == "sqlite"
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
        history = client.get(f"/api/v1/datasets/{did}").json()
        assert all(v["profile"]["source_table"] == "Daten" for v in history["versions"])
        assert any(j["id"] == failed["id"] and j["status"] == "FAILED" for j in history["jobs"])
