"""Kleine, unabhängig prüfbare Regeln für Cookies, Token und Sitzungsgrenzen."""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, Response

from platform_app.shared.config import AppSettings

SESSION_IDLE = timedelta(minutes=30)
SESSION_ABSOLUTE = timedelta(hours=8)
LOGIN_LIFETIME = timedelta(minutes=5)
ROLE_CODES = frozenset({"ORG_ADMIN", "ARCHITECTURE_ANALYST", "VIEWER"})
WRITE_ROLES = frozenset({"ORG_ADMIN", "ARCHITECTURE_ANALYST"})
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "VIEWER": frozenset({"scenario:read", "assessment:read"}),
    "ARCHITECTURE_ANALYST": frozenset(
        {
            "scenario:read",
            "assessment:read",
            "scenario:write",
            "assessment:create",
            "explanation:create",
        }
    ),
    "ORG_ADMIN": frozenset(
        {
            "scenario:read",
            "assessment:read",
            "scenario:write",
            "assessment:create",
            "explanation:create",
            "members:manage",
            "audit:read",
        }
    ),
}


def opaque_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def valid_token(value: str | None) -> bool:
    return value is not None and 40 <= len(value) <= 128 and value.isascii()


def pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(token_hash(verifier)).decode("ascii").rstrip("=")


def permissions_for(roles: frozenset[str]) -> list[str]:
    return sorted({permission for role in roles for permission in ROLE_PERMISSIONS.get(role, ())})


def session_is_valid(
    *,
    now: datetime,
    revoked_at: datetime | None,
    idle_expires_at: datetime,
    absolute_expires_at: datetime,
    session_epoch: int,
    user_epoch: int,
    user_status: str,
) -> bool:
    return (
        revoked_at is None
        and user_status == "ACTIVE"
        and session_epoch == user_epoch
        and now < idle_expires_at
        and now < absolute_expires_at
    )


def cookie_name(settings: AppSettings, purpose: str) -> str:
    prefix = "demo-platform-" if settings.http_demo_mode else "__Host-platform-"
    return prefix + purpose


def set_cookie(
    response: Response,
    settings: AppSettings,
    purpose: str,
    value: str,
    max_age: int,
    *,
    httponly: bool = True,
) -> None:
    response.set_cookie(
        cookie_name(settings, purpose),
        value,
        max_age=max_age,
        path="/",
        secure=not settings.http_demo_mode,
        httponly=httponly,
        samesite="lax",
    )


def clear_cookie(
    response: Response, settings: AppSettings, purpose: str, *, httponly: bool = True
) -> None:
    response.delete_cookie(
        cookie_name(settings, purpose),
        path="/",
        secure=not settings.http_demo_mode,
        httponly=httponly,
        samesite="lax",
    )


def verify_csrf(request: Request, settings: AppSettings, stored_hash: bytes) -> str:
    """Double-Submit mit zusätzlicher Bindung an die serverseitige Sitzung."""
    header = request.headers.get("x-csrf-token")
    cookie = request.cookies.get(cookie_name(settings, "csrf"))
    origin = request.headers.get("origin")
    expected_origin = str(settings.public_origin).rstrip("/")
    if (
        origin != expected_origin
        or not valid_token(header)
        or not valid_token(cookie)
        or header is None
        or cookie is None
        or not hmac.compare_digest(header, cookie)
        or not hmac.compare_digest(token_hash(header), stored_hash)
    ):
        raise HTTPException(
            403, "Die Sicherheitsprüfung ist fehlgeschlagen. Bitte die Seite neu laden."
        )
    return header
