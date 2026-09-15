"""Negative Unit-Prüfungen; DB/IdP-Doubles ersetzen keine PostgreSQL-/OIDC-Abnahme."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import jwt
import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, Request, Response
from platform_app.identity import dependencies
from platform_app.identity import router as identity
from platform_app.identity.models import (
    AuthSession,
    MembershipRole,
    OIDCLoginAttempt,
    Organization,
    OrganizationMembership,
    User,
)
from platform_app.identity.security import (
    cookie_name,
    opaque_token,
    permissions_for,
    pkce_challenge,
    session_is_valid,
    set_cookie,
    token_hash,
    verify_csrf,
)
from platform_app.shared.config import AppSettings
from sqlalchemy.orm import Session


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> AppSettings:
    configured = AppSettings(
        _env_file=None,
        oidc_client_secret="synthetic-test-client-" + "x" * 24,
        session_secret="synthetic-test-session-" + "x" * 32,
        oidc_encryption_key=Fernet.generate_key().decode(),
        public_origin="http://localhost:8080",
        oidc_issuer="http://localhost:8080/identity/realms/platform",
        oidc_internal_base_url="http://keycloak:8080/identity",
        oidc_client_id="platform",
        environment="test",
        http_demo_mode=True,
        openai_enabled=False,
    )
    monkeypatch.setattr(identity, "get_settings", lambda: configured)
    monkeypatch.setattr(dependencies, "get_settings", lambda: configured)
    return configured


def browser_request(
    settings: AppSettings,
    *,
    method: str = "POST",
    csrf: str | None = None,
    header: str | None = None,
    origin: str | None = "http://localhost:8080",
    login: str | None = None,
    session: str | None = None,
) -> Request:
    cookies = {
        cookie_name(settings, purpose): value
        for purpose, value in {"csrf": csrf, "login": login, "session": session}.items()
        if value is not None
    }
    headers = {"cookie": "; ".join(f"{key}={value}" for key, value in cookies.items())}
    if header is not None:
        headers["x-csrf-token"] = header
    if origin is not None:
        headers["origin"] = origin
    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/api/v1/example",
            "headers": [(key.encode(), value.encode()) for key, value in headers.items()],
        }
    )


def test_csrf_requires_both_cookie_and_header_with_session_hash(settings: AppSettings) -> None:
    token = opaque_token()
    request = browser_request(settings, csrf=token, header=token)
    assert verify_csrf(request, settings, token_hash(token)) == token


@pytest.mark.parametrize(
    "failure",
    [
        "no_origin",
        "wrong_origin",
        "origin_prefix",
        "no_cookie",
        "no_header",
        "wrong_header",
        "wrong_session_hash",
        "short_header",
    ],
)
def test_csrf_denies_cross_origin_and_unbound_tokens(settings: AppSettings, failure: str) -> None:
    token = opaque_token()
    values: dict[str, Any] = {"csrf": token, "header": token}
    if failure == "no_origin":
        values["origin"] = None
    elif failure == "wrong_origin":
        values["origin"] = "https://attacker.example"
    elif failure == "origin_prefix":
        values["origin"] = settings.public_origin + ".attacker.example"
    elif failure == "no_cookie":
        values["csrf"] = None
    elif failure == "no_header":
        values["header"] = None
    elif failure == "wrong_header":
        values["header"] = opaque_token()
    elif failure == "short_header":
        values["header"] = "short"
    expected = token_hash(opaque_token() if failure == "wrong_session_hash" else token)
    with pytest.raises(HTTPException) as rejected:
        verify_csrf(browser_request(settings, **values), settings, expected)
    assert rejected.value.status_code == 403


def test_https_session_cookie_is_host_bound_and_httponly(settings: AppSettings) -> None:
    secure = settings.model_copy(
        update={"http_demo_mode": False, "public_origin": "https://app.example"}
    )
    response = Response()
    set_cookie(response, secure, "session", opaque_token(), 28800)
    value = response.headers["set-cookie"]
    assert value.startswith("__Host-platform-session=")
    for expected in ("HttpOnly", "Secure", "Path=/", "SameSite=lax"):
        assert expected in value
    assert "Domain=" not in value


@pytest.mark.parametrize("failure", ["idle", "absolute", "revoked", "epoch", "disabled"])
def test_expired_or_revoked_session_cannot_be_reused(failure: str) -> None:
    now = datetime.now(UTC)
    values: dict[str, Any] = {
        "now": now,
        "revoked_at": None,
        "idle_expires_at": now + timedelta(minutes=30),
        "absolute_expires_at": now + timedelta(hours=8),
        "session_epoch": 2,
        "user_epoch": 2,
        "user_status": "ACTIVE",
    }
    assert session_is_valid(**values)
    if failure == "idle":
        values["idle_expires_at"] = now
    elif failure == "absolute":
        values["absolute_expires_at"] = now
    elif failure == "revoked":
        values["revoked_at"] = now
    elif failure == "epoch":
        values["user_epoch"] = 3
    else:
        values["user_status"] = "DISABLED"
    assert not session_is_valid(**values)


def test_sessions_store_hashes_and_rotation_preserves_absolute_limit() -> None:
    db = MagicMock(spec=Session)
    user = User(id=uuid4(), auth_epoch=7)
    deadline = datetime.now(UTC) + timedelta(minutes=2)
    raw, csrf = identity.create_session(db, user, absolute_expires_at=deadline)
    record = db.add.call_args.args[0]
    assert isinstance(record, AuthSession)
    assert record.session_token_hash == token_hash(raw)
    assert record.csrf_secret_hash == token_hash(csrf)
    assert len(record.session_token_hash) == len(record.csrf_secret_hash) == 32
    assert len(raw) >= 43 and raw != csrf
    assert record.absolute_expires_at == deadline == record.idle_expires_at


def test_rbac_does_not_infer_platform_or_unknown_role_permissions() -> None:
    assert "scenario:write" not in permissions_for(frozenset({"VIEWER"}))
    assert "members:manage" not in permissions_for(frozenset({"ARCHITECTURE_ANALYST"}))
    assert permissions_for(frozenset({"PLATFORM_ADMIN", "UNKNOWN"})) == []
    assert "members:manage" in permissions_for(frozenset({"ORG_ADMIN"}))


@pytest.fixture(scope="module")
def rsa_keys() -> tuple[Any, dict[str, Any]]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    jwk.update({"kid": "unit-key", "alg": "RS256", "use": "sig"})
    return private, {"keys": [jwk]}


def valid_claims(settings: AppSettings) -> dict[str, Any]:
    now = int(datetime.now(UTC).timestamp())
    return {
        "iss": settings.oidc_issuer,
        "aud": settings.oidc_client_id,
        "sub": "synthetic-subject",
        "iat": now,
        "exp": now + 300,
        "nonce": "nonce-for-this-browser-attempt",
    }


def encoded(private: Any, claims: dict[str, Any]) -> str:
    return jwt.encode(claims, private, algorithm="RS256", headers={"kid": "unit-key"})


def test_signed_oidc_token_matches_exact_issuer_audience_nonce(
    settings: AppSettings,
    rsa_keys: tuple[Any, dict[str, Any]],
) -> None:
    private, jwks = rsa_keys
    claims = valid_claims(settings)
    assert (
        identity.validate_id_token(encoded(private, claims), jwks, token_hash(claims["nonce"]))
        == claims
    )


@pytest.mark.parametrize(
    "change",
    [
        {"iss": "https://attacker.example"},
        {"aud": "different-client"},
        {"nonce": "another-attempt"},
        {"nonce": {"malformed": "value"}},
        {"exp": 1},
        {"iat": 9999999999},
        {"azp": "attacker-client"},
        {"aud": ["platform", "second-client"]},
        {"sub": ""},
        {"sub": "s" * 256},
        {"iat": True},
    ],
)
def test_oidc_rejects_forged_or_unbound_claims(
    settings: AppSettings,
    rsa_keys: tuple[Any, dict[str, Any]],
    change: dict[str, Any],
) -> None:
    private, jwks = rsa_keys
    claims = valid_claims(settings)
    nonce_hash = token_hash(claims["nonce"])
    claims.update(change)
    with pytest.raises((jwt.PyJWTError, ValueError)):
        identity.validate_id_token(encoded(private, claims), jwks, nonce_hash)


@pytest.mark.parametrize("missing", ["exp", "iat", "iss", "aud", "sub", "nonce"])
def test_oidc_requires_security_claims(
    settings: AppSettings,
    rsa_keys: tuple[Any, dict[str, Any]],
    missing: str,
) -> None:
    private, jwks = rsa_keys
    claims = valid_claims(settings)
    nonce_hash = token_hash(claims["nonce"])
    del claims[missing]
    with pytest.raises((jwt.PyJWTError, ValueError)):
        identity.validate_id_token(encoded(private, claims), jwks, nonce_hash)


@pytest.mark.parametrize("key_change", [{"use": "enc"}, {"alg": "RS512"}, {"key_ops": ["encrypt"]}])
def test_oidc_rejects_wrong_key_purpose(
    settings: AppSettings,
    rsa_keys: tuple[Any, dict[str, Any]],
    key_change: dict[str, Any],
) -> None:
    private, jwks = rsa_keys
    claims = valid_claims(settings)
    altered = {"keys": [{**jwks["keys"][0], **key_change}]}
    with pytest.raises(ValueError):
        identity.validate_id_token(encoded(private, claims), altered, token_hash(claims["nonce"]))


def test_oidc_rejects_ambiguous_keys_and_invalid_signature(
    settings: AppSettings,
    rsa_keys: tuple[Any, dict[str, Any]],
) -> None:
    private, jwks = rsa_keys
    claims = valid_claims(settings)
    token = encoded(private, claims)
    with pytest.raises(ValueError):
        identity.validate_id_token(token, {"keys": jwks["keys"] * 2}, token_hash(claims["nonce"]))
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(jwt.InvalidSignatureError):
        identity.validate_id_token(encoded(other, claims), jwks, token_hash(claims["nonce"]))


@pytest.mark.parametrize("algorithm", ["none", "HS256"])
def test_oidc_rejects_unsigned_tokens_and_algorithm_confusion(
    settings: AppSettings,
    rsa_keys: tuple[Any, dict[str, Any]],
    algorithm: str,
) -> None:
    claims = valid_claims(settings)
    token = jwt.encode(
        claims,
        "" if algorithm == "none" else "x" * 32,
        algorithm=algorithm,
        headers={"kid": "unit-key"},
    )
    with pytest.raises(ValueError):
        identity.validate_id_token(token, rsa_keys[1], token_hash(claims["nonce"]))


def test_internal_oidc_transport_preserves_canonical_issuer(settings: AppSettings) -> None:
    assert identity.internal_url(settings.oidc_issuer + "/protocol/openid-connect/token") == (
        "http://keycloak:8080/identity/realms/platform/protocol/openid-connect/token"
    )


@pytest.mark.parametrize(
    "suffix",
    [
        "/../../admin",
        "/%2e%2e/admin",
        "/%252e%252e/admin",
        "/good#fragment",
        "/good?redirect=unsafe",
        "/back\\slash",
        "//duplicate",
        ".attacker.example/token",
    ],
)
def test_internal_oidc_transport_rejects_prefix_and_path_escape(
    settings: AppSettings, suffix: str
) -> None:
    with pytest.raises(HTTPException) as rejected:
        identity.internal_url(settings.oidc_issuer + suffix)
    assert rejected.value.status_code == 503


@contextmanager
def database_double(db: Session) -> Iterator[Session]:
    """Reines Unit-Double; prüft Kontrollfluss, keine Persistenz-/RLS-Garantien."""
    yield db


def test_login_uses_s256_and_encrypts_pkce_verifier(
    settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = MagicMock(spec=Session)
    monkeypatch.setattr(identity, "auth_session", lambda: database_double(db))
    monkeypatch.setattr(
        identity,
        "metadata",
        lambda: {"authorization_endpoint": settings.oidc_issuer + "/protocol/openid-connect/auth"},
    )
    response = identity.login(browser_request(settings, method="GET"))
    query = parse_qs(urlsplit(response.headers["location"]).query)
    attempt = db.add.call_args.args[0]
    verifier = (
        Fernet(settings.oidc_encryption_key.encode())
        .decrypt(attempt.pkce_verifier_ciphertext)
        .decode()
    )
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == [pkce_challenge(verifier)]
    assert attempt.state_hash == token_hash(query["state"][0])
    assert attempt.nonce_hash == token_hash(query["nonce"][0])
    assert verifier.encode() != attempt.pkce_verifier_ciphertext
    assert attempt.expires_at - attempt.created_at == timedelta(minutes=5)


@pytest.mark.parametrize("failure", ["expired", "consumed", "other_browser", "unknown_state"])
def test_oidc_callback_rejects_replay_and_browser_mismatch_before_network(
    settings: AppSettings,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    state, binding = opaque_token(), opaque_token()
    now = datetime.now(UTC)
    attempt = OIDCLoginAttempt(
        state_hash=token_hash(state),
        browser_binding_hash=token_hash(binding),
        expires_at=now + timedelta(minutes=5),
        consumed_at=None,
    )
    if failure == "expired":
        attempt.expires_at = now - timedelta(seconds=1)
    elif failure == "consumed":
        attempt.consumed_at = now
    elif failure == "other_browser":
        binding = opaque_token()
    db = MagicMock(spec=Session)
    db.scalar.return_value = None if failure == "unknown_state" else attempt
    network = MagicMock(side_effect=AssertionError("Ungültiger Callback darf keinen IdP aufrufen."))
    monkeypatch.setattr(identity, "auth_session", lambda: database_double(db))
    monkeypatch.setattr(identity, "metadata", network)
    with pytest.raises(HTTPException) as rejected:
        identity.callback(
            browser_request(settings, method="GET", login=binding), code="code", state=state
        )
    assert rejected.value.status_code == 400
    network.assert_not_called()


def test_organization_switch_rotates_session_and_csrf_without_extending_login(
    settings: AppSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csrf, old_raw = opaque_token(), opaque_token()
    user_id, org_id = uuid4(), uuid4()
    old = AuthSession(
        id=uuid4(),
        user_id=user_id,
        csrf_secret_hash=token_hash(csrf),
        absolute_expires_at=datetime.now(UTC) + timedelta(minutes=7),
    )
    user = User(id=user_id, auth_epoch=2)
    org = Organization(id=org_id, status="ACTIVE")
    membership = OrganizationMembership(organization_id=org_id, user_id=user_id, status="ACTIVE")
    db = MagicMock(spec=Session)
    db.get.side_effect = [org, membership]
    monkeypatch.setattr(identity, "auth_session", lambda: database_double(db))
    monkeypatch.setattr(identity, "lookup_session", lambda request, session: (old, user))
    response = identity.switch_org(
        identity.OrganizationChoice(organization_id=org_id),
        browser_request(settings, csrf=csrf, header=csrf, session=old_raw),
    )
    created = next(
        call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], AuthSession)
    )
    assert old.revoked_at is not None
    assert created.active_organization_id == org_id
    assert created.absolute_expires_at == old.absolute_expires_at
    assert created.session_token_hash != token_hash(old_raw)
    assert created.csrf_secret_hash != token_hash(csrf)
    assert len(response.headers.getlist("set-cookie")) == 2


def test_organization_switch_rejects_foreign_membership(
    settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    csrf = opaque_token()
    old = AuthSession(csrf_secret_hash=token_hash(csrf), revoked_at=None)
    db = MagicMock(spec=Session)
    db.get.side_effect = [Organization(status="ACTIVE"), None]
    monkeypatch.setattr(identity, "auth_session", lambda: database_double(db))
    monkeypatch.setattr(
        identity, "lookup_session", lambda request, session: (old, User(id=uuid4()))
    )
    with pytest.raises(HTTPException) as rejected:
        identity.switch_org(
            identity.OrganizationChoice(organization_id=uuid4()),
            browser_request(settings, csrf=csrf, header=csrf),
        )
    assert rejected.value.status_code == 403
    assert old.revoked_at is None
    db.add.assert_not_called()


def test_admin_role_is_rechecked_after_organization_lock() -> None:
    actor = dependencies.ActorContext(uuid4(), uuid4(), frozenset({"ORG_ADMIN"}), "Admin")
    db = MagicMock(spec=Session)
    db.scalar.return_value = Organization(status="ACTIVE")
    db.get.side_effect = [OrganizationMembership(status="ACTIVE"), None]
    with pytest.raises(HTTPException) as rejected:
        identity.lock_and_check_admin(db, actor)
    assert rejected.value.status_code == 403


@pytest.mark.parametrize("change", ["revoke", "demote"])
def test_last_active_administrator_cannot_be_removed(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    actor = dependencies.ActorContext(uuid4(), uuid4(), frozenset({"ORG_ADMIN"}), "Admin")
    target = uuid4()
    member = OrganizationMembership(
        organization_id=actor.organization_id, user_id=target, status="ACTIVE", revision=1
    )
    db = MagicMock(spec=Session)
    db.get.return_value = member
    db.scalars.return_value.all.return_value = [MembershipRole(role_code="ORG_ADMIN")]
    db.scalar.return_value = 1
    monkeypatch.setattr(identity, "tenant_session", lambda org: database_double(db))
    monkeypatch.setattr(identity, "lock_and_check_admin", lambda session, context: None)
    body = identity.MemberUpdate(
        roles=["ORG_ADMIN"] if change == "revoke" else ["VIEWER"],
        status="REVOKED" if change == "revoke" else "ACTIVE",
        expected_revision=1,
    )
    with pytest.raises(HTTPException) as rejected:
        identity.update_member(target, body, actor)
    assert rejected.value.status_code == 409
    db.delete.assert_not_called()
    assert member.status == "ACTIVE" and member.revision == 1
