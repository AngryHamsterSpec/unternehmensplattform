"""Mandantengebundene Bewertungsaggregate mit relationalen Kostenzeilen."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from platform_app.intake.models import now
from platform_app.shared.db import Base


class CostCatalog(Base):
    __tablename__ = "cost_catalog_versions"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "version"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    version: Mapped[str] = mapped_column(String(100))
    content_hash: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "created_by_user_id", "idempotency_key"),
        ForeignKeyConstraint(
            ["organization_id", "profile_version_id"],
            ["company_profile_versions.organization_id", "company_profile_versions.id"],
        ),
        ForeignKeyConstraint(
            ["organization_id", "catalog_version_id"],
            ["cost_catalog_versions.organization_id", "cost_catalog_versions.id"],
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
        ),
        CheckConstraint(
            "status IN ('VERIFIED','INCOMPLETE','NO_FEASIBLE_OPTION','VERIFICATION_FAILED')"
        ),
        Index("ix_assessment_org_created", "organization_id", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid)
    profile_version_id: Mapped[UUID] = mapped_column(Uuid)
    catalog_version_id: Mapped[UUID] = mapped_column(Uuid)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid)
    request_hash: Mapped[str] = mapped_column(String(64))
    result_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40))
    options: Mapped[dict[str, Any]] = mapped_column(JSONB)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CandidateRecord(Base):
    __tablename__ = "architecture_candidates"
    __table_args__ = (
        UniqueConstraint("organization_id", "assessment_id", "id"),
        UniqueConstraint("organization_id", "assessment_id", "candidate_key"),
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"], ["assessments.organization_id", "assessments.id"]
        ),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)"),
        CheckConstraint("status IN ('ELIGIBLE','INDETERMINATE','EXCLUDED')"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    assessment_id: Mapped[UUID] = mapped_column(Uuid)
    candidate_key: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30))
    score: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    rank: Mapped[int | None] = mapped_column(Integer)
    tco_total: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))


class CostLineRecord(Base):
    __tablename__ = "cost_estimate_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "assessment_id", "candidate_id"],
            [
                "architecture_candidates.organization_id",
                "architecture_candidates.assessment_id",
                "architecture_candidates.id",
            ],
        ),
        CheckConstraint("total IS NULL OR total >= 0"),
        Index("ix_lines_candidate", "organization_id", "assessment_id", "candidate_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    assessment_id: Mapped[UUID] = mapped_column(Uuid)
    candidate_id: Mapped[UUID] = mapped_column(Uuid)
    label: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(10))
    total: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"], ["assessments.organization_id", "assessments.id"]
        ),
        Index("ix_runs_assessment", "organization_id", "assessment_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    assessment_id: Mapped[UUID] = mapped_column(Uuid)
    agent_key: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "actor_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
        ),
        Index("ix_audit_org_time", "organization_id", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    actor_user_id: Mapped[UUID] = mapped_column(Uuid)
    event_type: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[UUID | None] = mapped_column(Uuid)
    request_id: Mapped[UUID] = mapped_column(Uuid)
    event_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
