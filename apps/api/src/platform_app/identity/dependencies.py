"""Jede Aktion erhält frisch geprüfte Mitgliedschaft und Rollen."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from platform_app.identity.models import (
    AuthSession,
    MembershipRole,
    Organization,
    OrganizationMembership,
    User,
)
from platform_app.identity.security import (
    SESSION_IDLE,
    WRITE_ROLES,
    cookie_name,
    session_is_valid,
    token_hash,
    valid_token,
    verify_csrf,
)
from platform_app.shared.config import get_settings
from platform_app.shared.db import auth_session


@dataclass(frozen=True)
class ActorContext:
    user_id: UUID
    organization_id: UUID
    roles: frozenset[str]
    display_name: str


def lookup_session(request: Request, db: Session) -> tuple[AuthSession, User]:
    settings = get_settings()
    raw = request.cookies.get(cookie_name(settings, "session"))
    if not valid_token(raw):
        raise HTTPException(401, "Bitte anmelden.")
    # Der Lock serialisiert Rotation/Widerruf mit konkurrierenden Requests.
    # Er gilt ausschließlich für die kurze Auth-Transaktion, nie für OIDC-I/O.
    identity = db.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(AuthSession.session_token_hash == token_hash(raw or ""))
        .with_for_update(of=AuthSession)
    ).one_or_none()
    session, user = identity if identity is not None else (None, None)
    now = datetime.now(UTC)
    if (
        session is None
        or user is None
        or not session_is_valid(
            now=now,
            revoked_at=session.revoked_at,
            idle_expires_at=session.idle_expires_at,
            absolute_expires_at=session.absolute_expires_at,
            session_epoch=session.auth_epoch,
            user_epoch=user.auth_epoch,
            user_status=user.status,
        )
    ):
        raise HTTPException(401, "Die Sitzung ist abgelaufen. Bitte erneut anmelden.")
    db.execute(
        text("SELECT set_config('app.authenticated_user_id', :user, true)"), {"user": str(user.id)}
    )
    session.last_seen_at = now
    session.idle_expires_at = min(now + SESSION_IDLE, session.absolute_expires_at)
    return session, user


def get_actor(request: Request) -> ActorContext:
    with auth_session() as db:
        session, user = lookup_session(request, db)
        memberships = db.execute(
            select(Organization, MembershipRole.role_code)
            .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .join(
                MembershipRole,
                (MembershipRole.organization_id == OrganizationMembership.organization_id)
                & (MembershipRole.user_id == OrganizationMembership.user_id),
            )
            .where(
                Organization.id == session.active_organization_id,
                Organization.status == "ACTIVE",
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.status == "ACTIVE",
            )
        ).all()
        if not memberships:
            raise HTTPException(403, "Bitte eine aktive Organisation auswählen.")
        org = memberships[0][0]
        roles = frozenset(row[1] for row in memberships)
        if not roles & {"ORG_ADMIN", "ARCHITECTURE_ANALYST", "VIEWER"}:
            raise HTTPException(
                403, "Für diese Organisation besteht kein freigegebenes Zugriffsrecht."
            )
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            verify_csrf(request, get_settings(), session.csrf_secret_hash)
        return ActorContext(user.id, org.id, roles, user.display_name or "Benutzer")


def check_csrf(request: Request) -> None:
    with auth_session() as db:
        session, _ = lookup_session(request, db)
        verify_csrf(request, get_settings(), session.csrf_secret_hash)


def require_write(request: Request) -> ActorContext:
    actor = get_actor(request)
    if not actor.roles & WRITE_ROLES:
        raise HTTPException(403, "Für diese Aktion fehlen Schreibrechte.")
    return actor


def require_admin(request: Request) -> ActorContext:
    actor = get_actor(request)
    if "ORG_ADMIN" not in actor.roles:
        raise HTTPException(403, "Diese Aktion benötigt Organisationsadministration.")
    return actor
