"""Unveränderliche Regelsätze und begrenzte M2-Hintergrundaufträge."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from platform_app.intake.models import now
from platform_app.shared.db import Base


class QualityRuleSet(Base):
    __tablename__ = "data_rule_sets"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
        ),
        ForeignKeyConstraint(
            ["organization_id", "replaces_id"],
            ["data_rule_sets.organization_id", "data_rule_sets.id"],
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid)
    name: Mapped[str] = mapped_column(String(160))
    rules: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    replaces_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DataTask(Base):
    __tablename__ = "data_tasks"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "created_by_user_id", "idempotency_key"),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
        ),
        ForeignKeyConstraint(
            ["organization_id", "dataset_id", "version_no"],
            [
                "data_versions.organization_id",
                "data_versions.dataset_id",
                "data_versions.version_no",
            ],
        ),
        CheckConstraint("kind IN ('ANALYSIS','SOURCE','PLAN')"),
        CheckConstraint("status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED')"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid)
    dataset_id: Mapped[UUID | None] = mapped_column(Uuid)
    version_no: Mapped[int | None] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(12))
    request_hash: Mapped[str] = mapped_column(String(64))
    request: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(12), default="QUEUED")
    lease_token: Mapped[UUID | None] = mapped_column(Uuid)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String(160), default="Auftrag vorgemerkt")
    error: Mapped[str | None] = mapped_column(String(300))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    result_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
