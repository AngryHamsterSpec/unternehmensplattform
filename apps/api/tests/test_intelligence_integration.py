"""Echte PostgreSQL-/HTTP-Abläufe für M2, einschließlich Quellen-RLS und Freigaben."""

import os
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from platform_app.data.intelligence_models import DataTask
from platform_app.data.intelligence_worker import process_task
from platform_app.intake.models import now
from platform_app.shared.db import engine_for, tenant_session
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_data_integration import upload as legacy_upload
from test_database_integration import client_for
from test_database_integration import stack as database_stack  # noqa: F401
from test_large_data_integration import finish, upload

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("database_stack"),
    pytest.mark.skipif(
        os.environ.get("RUN_DB_TESTS") != "1", reason="Echtes PostgreSQL erforderlich"
    ),
]
ORG = UUID("10000000-0000-4000-8000-000000000001")


def queued(client, path, body, key=None):
    response = client.post(
        "/api/v1" + path, json=body, headers={"Idempotency-Key": key or str(uuid4())}
    )
    assert response.status_code in {201, 202}, response.text
    return response.json()


def done(client, task):
    for _ in range(40):
        result = client.get("/api/v1/data-tasks/" + task["id"]).json()
        if result["status"] not in {"QUEUED", "RUNNING"}:
            return result
        process_task(ORG)
    raise AssertionError("Analyseauftrag nicht abgeschlossen")


def dataset(client, legacy=False):
    data = b"Name;X;Y;Datum\n Anna ;1;2;2026-01-01\n Anna ;1;2;2026-01-01\nBob;3;6;2026-02-01\n"
    job = legacy_upload(client, data) if legacy else upload(client, data)[1]
    completed = finish(client, job)
    assert completed["status"] == "SUCCEEDED", completed
    return job["dataset_id"], data


@pytest.mark.parametrize("legacy", [False, True])
def test_analysis_rules_report_idempotence_tenants_and_immutable_results(legacy):
    with client_for("analyst") as client:
        did, raw = dataset(client, legacy)
        rule = queued(
            client,
            "/data-rule-sets",
            {
                "name": "Betragsprüfung",
                "rules": [{"column": "X", "operation": "range", "minimum": "0", "maximum": "2"}],
            },
        )
        newer = queued(
            client,
            "/data-rule-sets",
            {
                "name": "Betragsprüfung v2",
                "rules": [{"column": "Name", "operation": "required"}],
                "replaces_id": rule["id"],
            },
        )
        assert newer["replaces_id"] == rule["id"]
        body = {
            "version_no": 1,
            "ruleset_id": rule["id"],
            "date_column": "Datum",
            "time_metric": "X",
        }
        key = str(uuid4())
        task = queued(client, f"/datasets/{did}/analyses", body, key)
        assert queued(client, f"/datasets/{did}/analyses", body, key)["id"] == task["id"]
        assert (
            client.post(
                f"/api/v1/datasets/{did}/analyses",
                json={**body, "time_metric": "Y"},
                headers={"Idempotency-Key": key},
            ).status_code
            == 409
        )
        result = done(client, task)
        assert result["status"] == "SUCCEEDED", result
        report = result["result"]
        assert report["rules"][0]["failed"] == 1 and report["numeric"][0]["count"] == 3
        assert report["ruleset"]["id"] == rule["id"]
        history = client.get(f"/api/v1/data-tasks?dataset_id={did}").json()["items"]
        summary = next(item for item in history if item["id"] == task["id"])
        assert summary["status"] == "SUCCEEDED" and summary["result_hash"] == result["result_hash"]
        assert "result" not in summary and "request" not in summary
        assert client.get(f"/api/v1/datasets/{did}/original").content == raw
        for suffix in ("?format=html", "?format=json"):
            exported = client.get(f"/api/v1/data-tasks/{task['id']}/report" + suffix)
            assert exported.status_code == 200 and result["result_hash"] in exported.text
            assert result["created_by_user_id"] in exported.text
            assert exported.headers["x-content-type-options"] == "nosniff"
            if suffix.endswith("json"):
                assert datetime.fromisoformat(
                    exported.json()["finished_at"]
                ) == datetime.fromisoformat(result["finished_at"])
        with client_for("viewer") as viewer:
            assert viewer.get(f"/api/v1/data-tasks/{task['id']}/report").status_code == 200
            assert (
                viewer.post(
                    f"/api/v1/datasets/{did}/analyses",
                    json=body,
                    headers={"Idempotency-Key": str(uuid4())},
                ).status_code
                == 403
            )
        with client_for("mandant-b") as other:
            assert other.get(f"/api/v1/data-tasks/{task['id']}").status_code == 404
            assert other.get(f"/api/v1/data-tasks/{task['id']}/report").status_code == 404
            assert rule["id"] not in {
                r["id"] for r in other.get("/api/v1/data-rule-sets").json()["items"]
            }
            assert other.get("/api/v1/data-tasks?before=" + task["id"]).status_code == 404
        with engine_for().connect() as db:
            assert db.scalar(text("SELECT count(*) FROM data_tasks")) == 0
            assert db.scalar(text("SELECT count(*) FROM data_rule_sets")) == 0
        for sql, value in (
            ("UPDATE data_tasks SET result='{}' WHERE id=:id", task["id"]),
            ("UPDATE data_rule_sets SET name='x' WHERE id=:id", rule["id"]),
        ):
            with pytest.raises(DBAPIError), tenant_session(ORG) as db:
                db.execute(text(sql), {"id": value})


@pytest.mark.parametrize("legacy", [False, True])
def test_plan_preview_approval_stale_version_and_original_preserved(legacy):
    with client_for("analyst") as client:
        did, raw = dataset(client, legacy)
        key = str(uuid4())
        plan = queued(client, f"/datasets/{did}/plans", {"version_no": 1}, key)
        assert plan["status"] == "SUCCEEDED" and plan["result"]["mode"] == "rules"
        assert queued(client, f"/datasets/{did}/plans", {"version_no": 1}, key)["id"] == plan["id"]
        assert len(plan["result"]["steps"]) == 2
        preview = queued(client, f"/data-tasks/{plan['id']}/preview", None)
        assert queued(client, f"/data-tasks/{plan['id']}/preview", None)["id"] == preview["id"]
        preview = finish(client, preview)
        assert preview["status"] == "SUCCEEDED" and preview["profile"]["rows"] == 2
        assert client.get(f"/api/v1/datasets/{did}").json()["current_version"] == 1
        response = client.post(
            f"/api/v1/datasets/{did}/versions",
            json={
                "preview_id": preview["id"],
                "result_hash": preview["result_hash"],
                "expected_current_version": 1,
            },
        )
        assert response.status_code == 201, response.text
        assert client.get(f"/api/v1/datasets/{did}/original").content == raw
        assert client.post(f"/api/v1/data-tasks/{plan['id']}/preview").status_code == 409
        denied = client.post(
            f"/api/v1/datasets/{did}/plans",
            json={"version_no": 2, "mode": "openai", "approve_external_processing": False},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert denied.status_code == 403


def test_cancellation_retry_expired_lease_and_actor_revocation():
    with client_for("analyst") as client:
        did, _ = dataset(client)
        task = queued(client, f"/datasets/{did}/analyses", {"version_no": 1})
        assert (
            client.post(f"/api/v1/data-tasks/{task['id']}/cancel").json()["status"] == "CANCELLED"
        )
        retry = queued(client, f"/data-tasks/{task['id']}/retry", None)
        with tenant_session(ORG) as db:
            row = db.get(DataTask, UUID(retry["id"]))
            row.status, row.attempts, row.lease_token, row.lease_until = (
                "RUNNING",
                1,
                uuid4(),
                now() - timedelta(seconds=1),
            )
        assert done(client, retry)["status"] == "SUCCEEDED"
        task = queued(client, f"/datasets/{did}/analyses", {"version_no": 1})
        # Ein Rechteentzug wird vor Veröffentlichung erneut durchgesetzt.
        with engine_for("migration").begin() as db:
            db.execute(
                text(
                    "UPDATE organization_memberships SET status='REVOKED', revoked_at=now() WHERE organization_id=:org AND user_id='20000000-0000-4000-8000-000000000002'"
                ),
                {"org": ORG},
            )
        try:
            process_task(ORG)
            with tenant_session(ORG) as db:
                row = db.get(DataTask, UUID(task["id"]))
                assert row.status == "FAILED" and row.result is None
        finally:
            with engine_for("migration").begin() as db:
                db.execute(
                    text(
                        "UPDATE organization_memberships SET status='ACTIVE', revoked_at=NULL WHERE organization_id=:org AND user_id='20000000-0000-4000-8000-000000000002'"
                    ),
                    {"org": ORG},
                )


def test_real_postgresql_snapshot_source_rls_and_normal_processing():
    with client_for("analyst") as client:
        catalog = client.get("/api/v1/data-sources")
        assert (
            catalog.status_code == 200
            and "password" not in catalog.text
            and "host" not in catalog.text
        )
        source = next(s for s in catalog.json()["items"] if s["id"] == "synthetischer-vertrieb")
        task = queued(
            client,
            "/data-sources/import",
            {
                "source_id": source["id"],
                "table": "demo.sales",
                "name": "Synthetischer Quellenintegrationstest",
            },
        )
        result = done(client, task)
        assert result["status"] == "SUCCEEDED", result
        imported = finish(
            client, {"dataset_id": result["result"]["dataset_id"], "id": result["result"]["job_id"]}
        )
        assert imported["status"] == "SUCCEEDED", imported
        assert imported["profile"]["rows"] == 4
        assert imported["profile"]["database_source"]["table"] == "demo.sales"
        original = client.get(f"/api/v1/datasets/{result['result']['dataset_id']}/original")
        assert b"RLS-ausgeschlossen" not in original.content and b" Anna " in original.content
        assert (
            client.post(
                "/api/v1/data-sources/import",
                json={"source_id": source["id"], "table": "public.secrets", "name": "Abgelehnt"},
                headers={"Idempotency-Key": str(uuid4())},
            ).status_code
            == 422
        )


def test_external_plan_test_double_consent_budget_minimization_and_verifier(monkeypatch):
    from platform_app.data.intelligence_schemas import PlanSelection
    from platform_app.data.plan_advisor import OpenAIPlanProvider
    from platform_app.shared.config import get_settings

    settings = get_settings()
    for field, value in {
        "openai_enabled": True,
        "openai_organization_ids": str(ORG),
        "openai_model": "synthetic-contract-double",
        "openai_price_version": "synthetic-test-only",
        "openai_input_per_million": "1",
        "openai_output_per_million": "1",
        "openai_daily_budget": "1000",
    }.items():
        monkeypatch.setattr(settings, field, value)
    calls = []

    async def select(self, settings, payload):
        calls.append(payload)
        assert "Anna" not in str(payload) and "Name" not in str(payload)
        return PlanSelection(candidate_ids=["trim-0"])

    monkeypatch.setattr(OpenAIPlanProvider, "select", select)
    with client_for("analyst") as client:
        did, raw = dataset(client)
        payload = {"version_no": 1, "mode": "openai", "approve_external_processing": True}
        denied = client.post(
            f"/api/v1/datasets/{did}/plans",
            json={**payload, "approve_external_processing": False},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert denied.status_code == 403 and calls == []
        key = str(uuid4())
        result = queued(client, f"/datasets/{did}/plans", payload, key)
        assert result["status"] == "SUCCEEDED" and result["result"]["mode"] == "openai"
        assert result["result"]["model"] == "synthetic-contract-double"
        assert (
            queued(client, f"/datasets/{did}/plans", payload, key)["id"] == result["id"]
            and len(calls) == 1
        )
        assert client.get(f"/api/v1/datasets/{did}").json()["current_version"] == 1
        assert client.get(f"/api/v1/datasets/{did}/original").content == raw
        monkeypatch.setattr(settings, "openai_daily_budget", "0")
        denied = client.post(
            f"/api/v1/datasets/{did}/plans", json=payload, headers={"Idempotency-Key": str(uuid4())}
        )
        assert denied.status_code == 429 and len(calls) == 1
        monkeypatch.setattr(settings, "openai_daily_budget", "1000")

        async def untrusted(self, settings, payload):
            return PlanSelection(candidate_ids=["execute-sql"])

        monkeypatch.setattr(OpenAIPlanProvider, "select", untrusted)
        failed = queued(client, f"/datasets/{did}/plans", payload)
        assert failed["status"] == "FAILED" and failed["result"] is None
        assert client.post(f"/api/v1/data-tasks/{failed['id']}/preview").status_code == 409

        async def interrupted(self, settings, payload):
            raise TimeoutError("Synthetischer Anbieterausfall")

        monkeypatch.setattr(OpenAIPlanProvider, "select", interrupted)
        failed = queued(client, f"/datasets/{did}/plans", payload)
        assert failed["status"] == "FAILED" and failed["result"] is None
        assert (
            client.post(
                f"/api/v1/data-tasks/{failed['id']}/retry",
                headers={"Idempotency-Key": str(uuid4())},
            ).status_code
            == 409
        )
