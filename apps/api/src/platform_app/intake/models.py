"""Fachspalten und unveränderliche typisierte Profilstände."""

from datetime import UTC, datetime
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

# Register the identity tables referenced by the FK strings below in the shared metadata.
from platform_app.identity import models as identity_models  # noqa: F401
from platform_app.shared.db import Base


def now() -> datetime:
    return datetime.now(UTC)


class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
        ),
        CheckConstraint("revision > 0"),
        Index("ix_profiles_org_created", "organization_id", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid)
    name: Mapped[str] = mapped_column(String(160))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProfileVersion(Base):
    __tablename__ = "company_profile_versions"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "company_profile_id", "version_no"),
        ForeignKeyConstraint(
            ["organization_id", "company_profile_id"],
            ["company_profiles.organization_id", "company_profiles.id"],
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
        ),
        CheckConstraint("version_no > 0"),
        CheckConstraint("monthly_budget IS NULL OR monthly_budget >= 0"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    company_profile_id: Mapped[UUID] = mapped_column(Uuid)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid)
    version_no: Mapped[int] = mapped_column(Integer)
    industry: Mapped[str] = mapped_column(String(120))
    employee_count: Mapped[int | None] = mapped_column(Integer)
    monthly_budget: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    content_hash: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WorkloadRecord(Base):
    __tablename__ = "workloads"
    __table_args__ = (
        UniqueConstraint("organization_id", "profile_version_id", "workload_key"),
        ForeignKeyConstraint(
            ["organization_id", "profile_version_id"],
            ["company_profile_versions.organization_id", "company_profile_versions.id"],
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    profile_version_id: Mapped[UUID] = mapped_column(Uuid)
    workload_key: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(160))
    workload_type: Mapped[str] = mapped_column(String(30))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)


class AssetRecord(Base):
    __tablename__ = "infrastructure_assets"
    __table_args__ = (
        UniqueConstraint("organization_id", "profile_version_id", "asset_key"),
        ForeignKeyConstraint(
            ["organization_id", "profile_version_id"],
            ["company_profile_versions.organization_id", "company_profile_versions.id"],
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    profile_version_id: Mapped[UUID] = mapped_column(Uuid)
    asset_key: Mapped[str] = mapped_column(String(64))
    asset_type: Mapped[str] = mapped_column(String(30))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
