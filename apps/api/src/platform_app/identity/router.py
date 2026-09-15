"""OIDC-Codefluss und lokale Sitzungen ohne Entwicklungs-Auth-Bypass."""

import hmac
from datetime import UTC, datetime
from typing import Annotated, Any, TypeVar
from urllib.parse import unquote, urlencode, urlsplit
from uuid import UUID, uuid4

import httpx
import jwt
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from platform_app.identity.dependencies import ActorContext, lookup_session, require_admin
from platform_app.identity.models import (
    AuthEvent,
    AuthSession,
    MembershipRole,
    OIDCLoginAttempt,
    Organization,
    OrganizationMembership,
    User,
)
from platform_app.identity.security import (
    LOGIN_LIFETIME,
    ROLE_CODES,
    SESSION_ABSOLUTE,
    SESSION_IDLE,
    clear_cookie,
    cookie_name,
    opaque_token,
    permissions_for,
    pkce_challenge,
    set_cookie,
    token_hash,
    valid_token,
    verify_csrf,
)
from platform_app.shared.audit import append_audit
from platform_app.shared.config import get_settings
from platform_app.shared.db import auth_session, tenant_session

router = APIRouter(prefix="/api/v1")
ResponseType = TypeVar("ResponseType", bound=Response)


def internal_url(url: str) -> str:
    settings = get_settings()
    issuer = settings.oidc_issuer.rstrip("/")
    if not isinstance(url, str) or not url.startswith(issuer + "/"):
        raise HTTPException(503, "Der Anmeldedienst enthält einen unerlaubten Endpunkt.")
    parsed = urlsplit(url)
    decoded_path = unquote(parsed.path)
    if (
        parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or any(segment in {".", ".."} for segment in decoded_path.split("/"))
        or "\\" in decoded_path
        or "%" in decoded_path
        or "//" in decoded_path
    ):
        raise HTTPException(503, "Der Anmeldedienst enthält einen unerlaubten Endpunkt.")
    realm_path = urlsplit(issuer).path.removeprefix("/identity")
    return settings.oidc_internal_base_url.rstrip("/") + realm_path + url[len(issuer) :]


def metadata() -> dict[str, Any]:
    settings = get_settings()
    with httpx.Client(timeout=8, follow_redirects=False) as client:
        response = client.get(
            internal_url(settings.oidc_issuer + "/.well-known/openid-configuration")
        )
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, dict) or data.get("issuer") != settings.oidc_issuer:
        raise HTTPException(503, "Der Aussteller des Anmeldedienstes stimmt nicht überein.")
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        if not isinstance(data.get(key), str):
            raise HTTPException(503, "Der Anmeldedienst liefert unvollständige Endpunkte.")
        internal_url(data[key])
    return data


def validate_id_token(id_token: str, jwks: dict[str, Any], expected_nonce: bytes) -> dict[str, Any]:
    """Feste Algorithmen und Claim-Bindung; JWT-Claims sind keine Rollenquelle."""
    settings = get_settings()
    if not isinstance(id_token, str) or not 1 <= len(id_token) <= 65536:
        raise ValueError("id_token")
    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    if header.get("alg") != "RS256" or not isinstance(kid, str) or not kid or header.get("crit"):
        raise ValueError("algorithm_or_key")
    if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
        raise ValueError("jwks")
    matches = [key for key in jwks["keys"] if isinstance(key, dict) and key.get("kid") == kid]
    if len(matches) != 1:
        raise ValueError("key_selection")
    key = matches[0]
    if (
        key.get("kty") != "RSA"
        or key.get("use", "sig") != "sig"
        or key.get("alg", "RS256") != "RS256"
        or (
            "key_ops" in key
            and (not isinstance(key["key_ops"], list) or "verify" not in key["key_ops"])
        )
    ):
        raise ValueError("key_purpose")
    public_key = jwt.PyJWK.from_dict(key, algorithm="RS256").key
    if not isinstance(public_key, RSAPublicKey) or public_key.key_size < 2048:
        raise ValueError("key_strength")
    claims = jwt.decode(
        id_token,
        public_key,
        algorithms=["RS256"],
        audience=settings.oidc_client_id,
        issuer=settings.oidc_issuer,
        options={"require": ["exp", "iat", "iss", "aud", "sub", "nonce"]},
        leeway=10,
    )
    nonce, subject = claims.get("nonce"), claims.get("sub")
    if not isinstance(nonce, str) or not hmac.compare_digest(token_hash(nonce), expected_nonce):
        raise ValueError("nonce")
    if not isinstance(subject, str) or not 1 <= len(subject) <= 255:
        raise ValueError("subject")
    if (
        type(claims["iat"]) is not int
        or type(claims["exp"]) is not int
        or claims["exp"] <= claims["iat"]
    ):
        raise ValueError("claim_times")
    if "azp" in claims and claims["azp"] != settings.oidc_client_id:
        raise ValueError("azp")
    if isinstance(claims["aud"], list) and len(claims["aud"]) > 1 and "azp" not in claims:
        raise ValueError("azp_required")
    return claims


def audit_auth(
    db: Session,
    request: Request,
    kind: str,
    outcome: str,
    user_id: UUID | None = None,
    organization_id: UUID | None = None,
) -> None:
    db.add(
        AuthEvent(
            event_type=kind,
            outcome=outcome,
            user_id=user_id,
            organization_id=organization_id,
            request_id=getattr(request.state, "request_id", uuid4()),
            event_metadata={},
        )
    )


def create_session(
    db: Session,
    user: User,
    org_id: UUID | None = None,
    *,
    absolute_expires_at: datetime | None = None,
) -> tuple[str, str]:
    now = datetime.now(UTC)
    raw = opaque_token()
    csrf = opaque_token()
    absolute_expires_at = absolute_expires_at or now + SESSION_ABSOLUTE
    db.add(
        AuthSession(
            session_token_hash=token_hash(raw),
            csrf_secret_hash=token_hash(csrf),
            user_id=user.id,
            active_organization_id=org_id,
            auth_epoch=user.auth_epoch,
            created_at=now,
            last_seen_at=now,
            idle_expires_at=min(now + SESSION_IDLE, absolute_expires_at),
            absolute_expires_at=absolute_expires_at,
        )
    )
    return raw, csrf


def session_response[ResponseType: Response](
    response: ResponseType, raw: str, csrf: str
) -> ResponseType:
    settings = get_settings()
    set_cookie(response, settings, "session", raw, 28800)
    set_cookie(response, settings, "csrf", csrf, 28800, httponly=False)
    return response


@router.get("/auth/login", include_in_schema=False)
def login(request: Request) -> RedirectResponse:
    settings = get_settings()
    meta = metadata()
    state, nonce, binding, verifier = (opaque_token() for _ in range(4))
    now = datetime.now(UTC)
    with auth_session() as db:
        db.add(
            OIDCLoginAttempt(
                state_hash=token_hash(state),
                nonce_hash=token_hash(nonce),
                browser_binding_hash=token_hash(binding),
                pkce_verifier_ciphertext=Fernet(settings.oidc_encryption_key.encode()).encrypt(
                    verifier.encode()
                ),
                encryption_key_id="runtime-v1",
                created_at=now,
                expires_at=now + LOGIN_LIFETIME,
                return_path="/",
            )
        )
    query = urlencode(
        {
            "client_id": settings.oidc_client_id,
            "response_type": "code",
            "redirect_uri": settings.public_origin + "/api/v1/auth/callback",
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
        }
    )
    response = RedirectResponse(meta["authorization_endpoint"] + "?" + query, status_code=303)
    set_cookie(response, settings, "login", binding, 300)
    return response


@router.get("/auth/callback", include_in_schema=False)
def callback(request: Request, code: str = "", state: str = "") -> RedirectResponse:
    settings = get_settings()
    if not code or not valid_token(state) or len(code) > 4096:
        raise HTTPException(400, "Ungültige Anmeldung.")
    binding = request.cookies.get(cookie_name(settings, "login"), "")
    with auth_session() as db:
        attempt = db.scalar(
            select(OIDCLoginAttempt)
            .where(OIDCLoginAttempt.state_hash == token_hash(state))
            .with_for_update()
        )
        if (
            not attempt
            or attempt.consumed_at
            or attempt.expires_at <= datetime.now(UTC)
            or not hmac.compare_digest(attempt.browser_binding_hash, token_hash(binding))
        ):
            raise HTTPException(
                400, "Die Anmeldung ist abgelaufen oder nicht diesem Browser zugeordnet."
            )
        attempt.consumed_at = datetime.now(UTC)
        expected_nonce = attempt.nonce_hash
        try:
            verifier = (
                Fernet(settings.oidc_encryption_key.encode())
                .decrypt(attempt.pkce_verifier_ciphertext)
                .decode()
            )
        except (InvalidToken, UnicodeError):
            raise HTTPException(401, "Die Anmeldung konnte nicht bestätigt werden.") from None
    try:
        meta = metadata()
        with httpx.Client(timeout=8, follow_redirects=False) as client:
            tokens = client.post(
                internal_url(meta["token_endpoint"]),
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.oidc_client_id,
                    "client_secret": settings.oidc_client_secret,
                    "code": code,
                    "code_verifier": verifier,
                    "redirect_uri": settings.public_origin + "/api/v1/auth/callback",
                },
            )
            tokens.raise_for_status()
            id_token = tokens.json()["id_token"]
            keys = client.get(internal_url(meta["jwks_uri"]))
            keys.raise_for_status()
        claims = validate_id_token(id_token, keys.json(), expected_nonce)
    except (httpx.HTTPError, jwt.PyJWTError, ValueError, KeyError, TypeError):
        with auth_session() as db:
            audit_auth(db, request, "login", "DENIED")
        raise HTTPException(401, "Die Anmeldung konnte nicht bestätigt werden.") from None
    session_tokens: tuple[str, str] | None = None
    with auth_session() as db:
        user = db.scalar(
            select(User).where(
                User.oidc_issuer == claims["iss"], User.oidc_subject == claims["sub"]
            )
        )
        if not user or user.status != "ACTIVE":
            audit_auth(db, request, "login", "DENIED")
        else:
            user.display_name = str(
                claims.get("name") or claims.get("preferred_username") or "Benutzer"
            )[:200]
            # Bei erneuter Anmeldung wird auch die vorherige lokale Sitzung widerrufen.
            old_raw = request.cookies.get(cookie_name(settings, "session"))
            if valid_token(old_raw):
                db.execute(
                    update(AuthSession)
                    .where(
                        AuthSession.session_token_hash == token_hash(old_raw or ""),
                        AuthSession.revoked_at.is_(None),
                    )
                    .values(revoked_at=datetime.now(UTC))
                )
            session_tokens = create_session(db, user)
            audit_auth(db, request, "login", "SUCCESS", user.id)
    if session_tokens is None:
        raise HTTPException(403, "Für diese Identität besteht keine aktive Plattformzuordnung.")
    raw, csrf = session_tokens
    response = session_response(RedirectResponse("/", status_code=303), raw, csrf)
    clear_cookie(response, settings, "login")
    return response


@router.get("/me")
def me(request: Request) -> dict[str, Any]:
    from platform_app.explanations.router import available

    with auth_session() as db:
        session, user = lookup_session(request, db)
        memberships = db.scalars(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id, OrganizationMembership.status == "ACTIVE"
            )
        ).all()
        orgs: list[dict[str, Any]] = []
        for membership in memberships:
            org = db.get(Organization, membership.organization_id)
            if not org or org.status != "ACTIVE":
                continue
            roles = db.scalars(
                select(MembershipRole.role_code).where(
                    MembershipRole.organization_id == org.id, MembershipRole.user_id == user.id
                )
            ).all()
            orgs.append({"id": str(org.id), "name": org.name, "roles": roles})
        active = next((o for o in orgs if o["id"] == str(session.active_organization_id)), None)
        roles = active["roles"] if active else []
        csrf = request.cookies.get(cookie_name(get_settings(), "csrf"), "")
        if not hmac.compare_digest(token_hash(csrf), session.csrf_secret_hash):
            raise HTTPException(401, "Die Sicherheitskennung fehlt. Bitte erneut anmelden.")
        return {
            "user": {"id": str(user.id), "display_name": user.display_name, "email": user.email},
            "organization": active,
            "organizations": orgs,
            "active_organization_id": str(session.active_organization_id) if active else None,
            "roles": roles,
            "permissions": permissions_for(frozenset(roles)),
            "csrf_token": csrf,
            "openai_available": available(session.active_organization_id) if active else False,
            "session_expires_at": session.absolute_expires_at.isoformat(),
        }


class OrganizationChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_id: UUID


@router.post("/session/organization")
def switch_org(body: OrganizationChoice, request: Request) -> JSONResponse:
    with auth_session() as db:
        session, user = lookup_session(request, db)
        verify_csrf(request, get_settings(), session.csrf_secret_hash)
        org = db.get(Organization, body.organization_id)
        membership = db.get(OrganizationMembership, (body.organization_id, user.id))
        if not org or org.status != "ACTIVE" or not membership or membership.status != "ACTIVE":
            raise HTTPException(403, "Organisation nicht verfügbar.")
        session.revoked_at = datetime.now(UTC)
        raw, csrf = create_session(
            db, user, body.organization_id, absolute_expires_at=session.absolute_expires_at
        )
        audit_auth(db, request, "organization.selected", "SUCCESS", user.id, org.id)
    return session_response(JSONResponse({"selected": str(body.organization_id)}), raw, csrf)


@router.post("/auth/logout")
def logout(request: Request) -> JSONResponse:
    with auth_session() as db:
        session, user = lookup_session(request, db)
        verify_csrf(request, get_settings(), session.csrf_secret_hash)
        session.revoked_at = datetime.now(UTC)
        audit_auth(db, request, "logout", "SUCCESS", user.id, session.active_organization_id)
    response = JSONResponse({"message": "Abgemeldet."})
    clear_cookie(response, get_settings(), "session")
    clear_cookie(response, get_settings(), "csrf", httponly=False)
    return response


class MemberCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    roles: list[str] = Field(min_length=1, max_length=3)


class MemberUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    roles: list[str] = Field(min_length=1, max_length=3)
    status: str = "ACTIVE"
    expected_revision: int = Field(ge=1)


def lock_and_check_admin(db: Session, actor: ActorContext) -> None:
    """Nach dem Organisations-Lock aktuelle Rechte prüfen, bevor Rollen geändert werden."""
    org = db.scalar(
        select(Organization).where(Organization.id == actor.organization_id).with_for_update()
    )
    membership = db.get(OrganizationMembership, (actor.organization_id, actor.user_id))
    admin = db.get(MembershipRole, (actor.organization_id, actor.user_id, "ORG_ADMIN"))
    if (
        not org
        or org.status != "ACTIVE"
        or not membership
        or membership.status != "ACTIVE"
        or not admin
    ):
        raise HTTPException(403, "Diese Aktion benötigt eine aktive Organisationsadministration.")


@router.get("/organizations/current/members")
def members(actor: Annotated[ActorContext, Depends(require_admin)]) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        rows = db.scalars(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == actor.organization_id
            )
        ).all()
        return {
            "items": [
                {
                    "user_id": str(m.user_id),
                    "status": m.status,
                    "revision": m.revision,
                    "roles": db.scalars(
                        select(MembershipRole.role_code).where(
                            MembershipRole.organization_id == actor.organization_id,
                            MembershipRole.user_id == m.user_id,
                        )
                    ).all(),
                }
                for m in rows
            ]
        }


@router.post("/organizations/current/members", status_code=201)
def add_member(
    body: MemberCreate, actor: Annotated[ActorContext, Depends(require_admin)]
) -> dict[str, str]:
    if not set(body.roles) <= ROLE_CODES:
        raise HTTPException(422, "Unzulässige Rolle.")
    try:
        with tenant_session(actor.organization_id) as db:
            lock_and_check_admin(db, actor)
            if db.get(OrganizationMembership, (actor.organization_id, body.user_id)):
                raise HTTPException(409, "Mitgliedschaft ist bereits vorhanden.")
            db.add(
                OrganizationMembership(organization_id=actor.organization_id, user_id=body.user_id)
            )
            db.flush()
            for role_code in set(body.roles):
                db.add(
                    MembershipRole(
                        organization_id=actor.organization_id,
                        user_id=body.user_id,
                        role_code=role_code,
                        granted_by_user_id=actor.user_id,
                        grant_actor_type="USER",
                    )
                )
            append_audit(
                db,
                actor,
                "membership.created",
                "user",
                body.user_id,
                {"roles": sorted(set(body.roles))},
            )
    except IntegrityError:
        raise HTTPException(422, "Identität oder Mitgliedschaft nicht verfügbar.") from None
    return {"user_id": str(body.user_id)}


@router.patch("/organizations/current/members/{user_id}")
def update_member(
    user_id: UUID, body: MemberUpdate, actor: Annotated[ActorContext, Depends(require_admin)]
) -> dict[str, Any]:
    if not set(body.roles) <= ROLE_CODES or body.status not in {"ACTIVE", "REVOKED"}:
        raise HTTPException(422, "Unzulässige Rolle oder Status.")
    with tenant_session(actor.organization_id) as db:
        lock_and_check_admin(db, actor)
        member = db.get(OrganizationMembership, (actor.organization_id, user_id))
        if not member:
            raise HTTPException(404, "Mitgliedschaft nicht gefunden.")
        if member.revision != body.expected_revision:
            raise HTTPException(409, "Die Mitgliedschaft wurde inzwischen geändert.")
        roles = db.scalars(
            select(MembershipRole).where(
                MembershipRole.organization_id == actor.organization_id,
                MembershipRole.user_id == user_id,
            )
        ).all()
        removing_admin = (
            member.status == "ACTIVE"
            and any(r.role_code == "ORG_ADMIN" for r in roles)
            and (body.status == "REVOKED" or "ORG_ADMIN" not in body.roles)
        )
        if removing_admin:
            admin_count = db.scalar(
                select(func.count())
                .select_from(MembershipRole)
                .join(
                    OrganizationMembership,
                    (MembershipRole.organization_id == OrganizationMembership.organization_id)
                    & (MembershipRole.user_id == OrganizationMembership.user_id),
                )
                .where(
                    MembershipRole.organization_id == actor.organization_id,
                    MembershipRole.role_code == "ORG_ADMIN",
                    OrganizationMembership.status == "ACTIVE",
                )
            )
            if admin_count is None or admin_count <= 1:
                raise HTTPException(
                    409, "Die letzte aktive Administrationsrolle muss erhalten bleiben."
                )
        for role in roles:
            db.delete(role)
        db.flush()
        for role_code in set(body.roles):
            db.add(
                MembershipRole(
                    organization_id=actor.organization_id,
                    user_id=user_id,
                    role_code=role_code,
                    granted_by_user_id=actor.user_id,
                    grant_actor_type="USER",
                )
            )
        member.status = body.status
        member.revision += 1
        member.revoked_at = datetime.now(UTC) if body.status == "REVOKED" else None
        append_audit(
            db,
            actor,
            "membership.updated",
            "user",
            user_id,
            {"roles": sorted(set(body.roles)), "status": body.status},
        )
    return {"user_id": str(user_id), "revision": member.revision}
