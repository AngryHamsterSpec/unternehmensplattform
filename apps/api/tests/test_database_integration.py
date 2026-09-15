"""Echte PostgreSQL-Tests. Kein SQLite-Ersatz und kein ORM-Mock."""

import os
from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_DB_TESTS") != "1", reason="Echte Testdatenbank explizit erforderlich"
    ),
]


@pytest.fixture(scope="module")
def stack():
    from platform_app.seed import main
    from platform_app.shared.db import engine_for

    main()
    with engine_for("migration").connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0005"
    yield


@contextmanager
def client_for(username):
    from platform_app.identity.models import User
    from platform_app.identity.router import create_session
    from platform_app.identity.security import cookie_name
    from platform_app.main import app
    from platform_app.shared.config import get_settings
    from platform_app.shared.db import auth_session

    user_ids = {"admin": 1, "analyst": 2, "viewer": 3, "mandant-b": 4}
    uid = UUID("20000000-0000-4000-8000-" + str(user_ids[username]).zfill(12))
    org = UUID("10000000-0000-4000-8000-" + str(2 if username == "mandant-b" else 1).zfill(12))
    # Authentifizierte Session als Testfixture. Der reale OIDC-Codefluss wird getrennt in Playwright geprüft.
    with auth_session() as db:
        user = db.get(User, uid)
        raw, csrf = create_session(db, user, org)
    settings = get_settings()
    with TestClient(app, base_url=settings.public_origin) as client:
        client.cookies.set(cookie_name(settings, "session"), raw)
        client.cookies.set(cookie_name(settings, "csrf"), csrf)
        client.headers.update({"Origin": settings.public_origin, "X-CSRF-Token": csrf})
        yield client


def scenario(client):
    from platform_app.decisions.demo import demo_scenario

    data = demo_scenario()
    data["name"] = "Integration " + str(uuid4())
    result = client.post("/api/v1/scenarios", json=data)
    assert result.status_code == 201, result.text
    return result.json()


def test_runtime_roles_and_fail_closed_rls(stack):
    from platform_app.shared.db import engine_for

    for role in ("app", "auth"):
        with engine_for(role).connect() as connection:
            assert connection.execute(
                text(
                    "SELECT rolsuper, rolbypassrls, rolcreaterole FROM pg_roles WHERE rolname=current_user"
                )
            ).one() == (False, False, False)
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace "
                        "AND relkind='r' AND relname!='alembic_version' AND (NOT relrowsecurity OR NOT relforcerowsecurity)"
                    )
                )
                == 0
            )
    with engine_for().connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM company_profiles")) == 0
        with pytest.raises(DBAPIError):
            connection.execute(text("SELECT * FROM users"))


def test_versioning_idempotence_and_tenant_isolation(stack):
    with client_for("analyst") as analyst:
        saved = scenario(analyst)
        source = saved["version"]["data"]
        payload = {
            "scenario_version_id": saved["version"]["id"],
            "weight_profile": "ECONOMIC",
            "horizon_months": 36,
        }
        key = str(uuid4())
        first = analyst.post("/api/v1/assessments", json=payload, headers={"Idempotency-Key": key})
        assert first.status_code == 201, first.text
        result = first.json()
        assert result["verification"]["valid"]
        repeated = analyst.post(
            "/api/v1/assessments", json=payload, headers={"Idempotency-Key": key}
        )
        assert repeated.status_code == 200 and repeated.json()["id"] == result["id"]
        conflict = analyst.post(
            "/api/v1/assessments",
            json={**payload, "horizon_months": 12},
            headers={"Idempotency-Key": key},
        )
        assert conflict.status_code == 409
        modified = {**source, "name": "Neue Fassung", "expected_current_version": 1}
        version = analyst.post("/api/v1/scenarios/" + saved["id"] + "/versions", json=modified)
        assert version.status_code == 201
        detail = analyst.get("/api/v1/scenarios/" + saved["id"]).json()
        assert [v["version_no"] for v in detail["versions"]] == [2, 1]
        cursor = None
        while True:
            page = analyst.get(
                "/api/v1/scenarios", params={"limit": 100, **({"cursor": cursor} if cursor else {})}
            ).json()
            found = next((item for item in page["items"] if item["id"] == saved["id"]), None)
            if found:
                assert found["current_version"] == 2
                assert [v["version_no"] for v in found["versions"]] == [2]
                break
            cursor = page["next_cursor"]
            assert cursor, "Szenario fehlt in der paginierten Liste"

        assert (
            analyst.post(
                "/api/v1/scenarios/" + saved["id"] + "/versions", json=modified
            ).status_code
            == 409
        )
        assert (
            analyst.get("/api/v1/scenarios/" + saved["id"] + "/versions/1").json()["data"] == source
        )
        assert (
            analyst.get("/api/v1/assessments/" + result["id"]).json()["result_hash"]
            == result["result_hash"]
        )
        with client_for("mandant-b") as other:
            assert other.get("/api/v1/scenarios/" + saved["id"]).status_code == 404
            assert other.get("/api/v1/assessments/" + result["id"]).status_code == 404
            assert (
                other.get("/api/v1/assessments/compare", params={"ids": result["id"]}).status_code
                == 404
            )
            assert (
                other.get("/api/v1/assessments/" + result["id"] + "/explanations").status_code
                == 404
            )
            assert (
                other.post(
                    "/api/v1/assessments", json=payload, headers={"Idempotency-Key": str(uuid4())}
                ).status_code
                == 404
            )
            audit = other.get("/api/v1/audit-events").json()["items"]
            assert all(row["entity_id"] != saved["id"] for row in audit)


def test_viewer_csrf_last_admin_and_disabled_provider(stack):
    with client_for("viewer") as viewer:
        from platform_app.decisions.demo import demo_scenario

        assert viewer.get("/api/v1/scenarios").status_code == 200
        assert viewer.post("/api/v1/scenarios", json=demo_scenario()).status_code == 403
        assert viewer.get("/api/v1/organizations/current/members").status_code == 403
        assert viewer.get("/api/v1/audit-events").status_code == 403
    with client_for("admin") as admin:
        assert (
            admin.post(
                "/api/v1/scenarios",
                json=demo_scenario(),
                headers={"Origin": "https://foreign.invalid"},
            ).status_code
            == 403
        )
        assert (
            admin.post(
                "/api/v1/scenarios", json=demo_scenario(), headers={"X-CSRF-Token": "bad"}
            ).status_code
            == 403
        )
        members = admin.get("/api/v1/organizations/current/members").json()["items"]
        own = next(m for m in members if m["user_id"].endswith("000000000001"))
        response = admin.patch(
            "/api/v1/organizations/current/members/" + own["user_id"],
            json={"roles": ["VIEWER"], "status": "ACTIVE", "expected_revision": own["revision"]},
        )
        assert response.status_code == 409
        assert (
            admin.post(
                "/api/v1/assessments/" + str(uuid4()) + "/explanations",
                json={"approve_external_processing": True},
                headers={"Idempotency-Key": str(uuid4())},
            ).status_code
            == 403
        )


def test_immutable_rows_composite_fk_and_atomic_audit(stack):
    from platform_app.assessments.models import AuditEvent
    from platform_app.decisions.demo import demo_scenario
    from platform_app.decisions.schemas import ScenarioInput
    from platform_app.identity.dependencies import ActorContext
    from platform_app.intake.models import CompanyProfile, ProfileVersion
    from platform_app.intake.service import save_version
    from platform_app.shared.db import engine_for, tenant_session

    org = UUID("10000000-0000-4000-8000-000000000001")
    other = UUID("10000000-0000-4000-8000-000000000002")
    actor = ActorContext(
        UUID("20000000-0000-4000-8000-000000000002"),
        org,
        frozenset({"ARCHITECTURE_ANALYST"}),
        "Test",
    )
    uid = uuid4()
    with pytest.raises(RuntimeError):
        with tenant_session(org) as db:
            profile = CompanyProfile(
                id=uid, organization_id=org, created_by_user_id=actor.user_id, name="Rollback"
            )
            db.add(profile)
            db.flush()
            save_version(db, actor, ScenarioInput.model_validate(demo_scenario()), profile, 1)
            db.flush()
            raise RuntimeError("Simulierter Fehler vor Commit")
    with tenant_session(org) as db:
        assert db.get(CompanyProfile, uid) is None
        assert db.scalar(select(AuditEvent).where(AuditEvent.entity_id == uid)) is None
    with client_for("analyst") as client:
        saved = scenario(client)
    with pytest.raises(DBAPIError):
        with tenant_session(org) as db:
            db.execute(
                text("UPDATE company_profile_versions SET industry='manipuliert' WHERE id=:id"),
                {"id": saved["version"]["id"]},
            )
    with pytest.raises(DBAPIError):
        with tenant_session(other) as db:
            db.add(
                ProfileVersion(
                    organization_id=other,
                    company_profile_id=UUID(saved["id"]),
                    created_by_user_id=UUID("20000000-0000-4000-8000-000000000004"),
                    version_no=99,
                    industry="Fremd",
                    content_hash="0" * 64,
                    data={},
                )
            )
            db.flush()
    with engine_for().connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM company_profiles")) == 0


def test_provider_failure_idempotence_budget_and_snapshot_are_atomic(stack, monkeypatch):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from datetime import UTC, datetime
    from decimal import Decimal
    from unittest.mock import AsyncMock

    from platform_app.explanations import router as explanation_router
    from platform_app.explanations.models import ProviderBudgetDay
    from platform_app.shared.config import get_settings
    from platform_app.shared.db import tenant_session

    org = UUID("10000000-0000-4000-8000-000000000001")
    configured = get_settings().model_copy(
        update={
            "openai_enabled": True,
            "openai_api_key": "integration-test-double",
            "openai_model": "test-only",
            "openai_price_version": "test-only",
            "openai_input_per_million": "1.25",
            "openai_output_per_million": "10",
            "openai_daily_budget": "100",
            "openai_organization_ids": str(org),
        }
    )
    monkeypatch.setattr(explanation_router, "get_settings", lambda: configured)

    async def unavailable(_payload):
        await asyncio.sleep(0.2)
        raise TimeoutError("Test-Double: kein externer Aufruf")

    provider = AsyncMock(side_effect=unavailable)
    monkeypatch.setattr(explanation_router.OpenAIExplanationProvider, "explain", provider)
    day = datetime.now(UTC).date()
    with tenant_session(org) as db:
        previous = db.get(ProviderBudgetDay, (org, day))
        before = previous.reserved_usd if previous else Decimal(0)
    with client_for("analyst") as client:
        saved = scenario(client)
        result = client.post(
            "/api/v1/assessments",
            json={"scenario_version_id": saved["version"]["id"]},
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
    route = "/api/v1/assessments/" + result["id"] + "/explanations"
    key = str(uuid4())

    def submit(_index):
        with client_for("analyst") as client:
            return client.post(
                route, json={"approve_external_processing": True}, headers={"Idempotency-Key": key}
            )

    with ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(submit, range(4)))
    assert all(r.status_code in {200, 201, 202} for r in responses)
    ids = {r.json()["id"] for r in responses}
    assert len(ids) == 1
    assert provider.await_count == 1
    request_id = ids.pop()
    with tenant_session(org) as db:
        balance = db.get(ProviderBudgetDay, (org, day)).reserved_usd
        assert balance == before + Decimal("0.02200000")
    configured.openai_daily_budget = str(balance)
    with client_for("analyst") as client:
        status = client.get("/api/v1/explanation-requests/" + request_id)
        assert status.status_code == 200 and status.json()["status"] == "FAILED"
        assert (
            client.get("/api/v1/assessments/" + result["id"]).json()["result_hash"]
            == result["result_hash"]
        )
        denied = client.post(
            route,
            json={"approve_external_processing": True},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert denied.status_code == 429
        assert (
            client.post(
                route,
                json={"approve_external_processing": False},
                headers={"Idempotency-Key": str(uuid4())},
            ).status_code
            == 403
        )
    with client_for("mandant-b") as other:
        assert other.get("/api/v1/explanation-requests/" + request_id).status_code == 404
    assert provider.await_count == 1


def test_membership_revocation_takes_effect_for_existing_session(stack):
    with client_for("viewer") as viewer, client_for("admin") as admin:
        members = admin.get("/api/v1/organizations/current/members").json()["items"]
        member = next(item for item in members if item["user_id"].endswith("000000000003"))
        route = "/api/v1/organizations/current/members/" + member["user_id"]
        try:
            revoked = admin.patch(
                route,
                json={
                    "roles": member["roles"],
                    "status": "REVOKED",
                    "expected_revision": member["revision"],
                },
            )
            assert revoked.status_code == 200, revoked.text
            assert viewer.get("/api/v1/scenarios").status_code == 403
        finally:
            current = next(
                item
                for item in admin.get("/api/v1/organizations/current/members").json()["items"]
                if item["user_id"] == member["user_id"]
            )
            restored = admin.patch(
                route,
                json={
                    "roles": member["roles"],
                    "status": "ACTIVE",
                    "expected_revision": current["revision"],
                },
            )
            assert restored.status_code == 200, restored.text
