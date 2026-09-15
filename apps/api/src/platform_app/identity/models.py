"""Relationale Identitätsmodelle ohne Passwort- oder OIDC-Token-Speicherung."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from platform_app.shared.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','SUSPENDED','ARCHIVED')", name="ck_org_status"),
        CheckConstraint("revision > 0", name="ck_org_revision"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("oidc_issuer", "oidc_subject", name="uq_user_oidc_identity"),
        CheckConstraint("status IN ('ACTIVE','DISABLED','PSEUDONYMIZED')", name="ck_user_status"),
        CheckConstraint("auth_epoch >= 0", name="ck_user_auth_epoch"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    oidc_issuer: Mapped[str] = mapped_column(String(512))
    oidc_subject: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    auth_epoch: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','REVOKED')", name="ck_membership_status"),
        CheckConstraint(
            "(status = 'REVOKED' AND revoked_at IS NOT NULL) OR "
            "(status = 'ACTIVE' AND revoked_at IS NULL)",
            name="ck_membership_revocation",
        ),
        CheckConstraint("revision > 0", name="ck_membership_revision"),
        Index("ix_memberships_user_status_org", "user_id", "status", "organization_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="RESTRICT"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=1)


class MembershipRole(Base):
    __tablename__ = "membership_roles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "granted_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "role_code IN ('ORG_ADMIN','ARCHITECTURE_ANALYST','VIEWER')", name="ck_role_code"
        ),
        CheckConstraint(
            "(grant_actor_type = 'USER' AND granted_by_user_id IS NOT NULL) OR "
            "(grant_actor_type = 'SYSTEM' AND granted_by_user_id IS NULL)",
            name="ck_role_grant_actor",
        ),
        Index("ix_roles_grantor", "organization_id", "granted_by_user_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    role_code: Mapped[str] = mapped_column(String(40), primary_key=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    granted_by_user_id: Mapped[UUID | None] = mapped_column(Uuid)
    grant_actor_type: Mapped[str] = mapped_column(String(10), default="SYSTEM")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["active_organization_id", "user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("octet_length(session_token_hash) = 32", name="ck_session_hash"),
        CheckConstraint("octet_length(csrf_secret_hash) = 32", name="ck_csrf_hash"),
        CheckConstraint("auth_epoch >= 0", name="ck_session_auth_epoch"),
        CheckConstraint(
            "created_at <= last_seen_at AND last_seen_at <= absolute_expires_at "
            "AND idle_expires_at <= absolute_expires_at",
            name="ck_session_times",
        ),
        Index("ix_sessions_user_revoked", "user_id", "revoked_at"),
        Index("ix_sessions_absolute_expiry", "absolute_expires_at"),
        Index("ix_sessions_org_user", "active_organization_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"))
    active_organization_id: Mapped[UUID | None] = mapped_column(Uuid)
    csrf_secret_hash: Mapped[bytes] = mapped_column(LargeBinary)
    auth_epoch: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OIDCLoginAttempt(Base):
    __tablename__ = "oidc_login_attempts"
    __table_args__ = (
        CheckConstraint("octet_length(state_hash) = 32", name="ck_login_state_hash"),
        CheckConstraint("octet_length(nonce_hash) = 32", name="ck_login_nonce_hash"),
        CheckConstraint("octet_length(browser_binding_hash) = 32", name="ck_login_browser_hash"),
        CheckConstraint("expires_at > created_at", name="ck_login_expiry"),
        Index("ix_login_attempt_expiry", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    state_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    nonce_hash: Mapped[bytes] = mapped_column(LargeBinary)
    browser_binding_hash: Mapped[bytes] = mapped_column(LargeBinary)
    pkce_verifier_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    encryption_key_id: Mapped[str] = mapped_column(String(80))
    return_path: Mapped[str] = mapped_column(String(512), default="/")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthEvent(Base):
    __tablename__ = "auth_events"
    __table_args__ = (
        CheckConstraint("outcome IN ('SUCCESS','DENIED','ERROR')", name="ck_auth_event_outcome"),
        Index("ix_auth_events_time_id", "occurred_at", "id"),
        Index("ix_auth_events_user_time", "user_id", "occurred_at"),
        Index("ix_auth_events_org", "organization_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    event_type: Mapped[str] = mapped_column(String(80))
    outcome: Mapped[str] = mapped_column(String(12))
    user_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"))
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    session_id: Mapped[UUID | None] = mapped_column(Uuid)
    request_id: Mapped[UUID] = mapped_column(Uuid)
    reason_code: Mapped[str | None] = mapped_column(String(80))
    event_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
