import base64
import json
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from platform_app.api import cursor_decode
from platform_app.main import _requests, app


@pytest.fixture
def client():
    _requests.clear()
    with TestClient(app) as value:
        yield value


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [1, 2],
        ["2026-09-10", "bad"],
        [],
        ["2026-09-10T00:00:00", "10000000-0000-4000-8000-000000000001"],
    ],
)
def test_invalid_cursors_fail_with_validation_error(payload):
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    with pytest.raises(HTTPException) as caught:
        cursor_decode(cursor)
    assert caught.value.status_code == 422


def test_live_health_and_unauthenticated_boundary(client):
    health = client.get("/api/v1/health/live")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert client.get("/api/v1/scenarios").status_code == 401
    assert client.get("/api/v1/me").status_code == 401


def test_size_limits_and_security_headers_apply_to_early_errors(client):
    response = client.post("/api/v1/scenarios", content=b"x" * 262145)
    assert response.status_code == 413
    assert response.headers["Content-Type"].startswith("application/problem+json")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert UUID(response.headers["X-Request-ID"])
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_openapi_includes_serialized_result_contract(client):
    data = client.get("/api/openapi.json")
    assert data.status_code == 200
    schemas = data.json()["components"]["schemas"]
    assert "AssessmentView" in schemas
    assert "ScenarioView" in schemas
