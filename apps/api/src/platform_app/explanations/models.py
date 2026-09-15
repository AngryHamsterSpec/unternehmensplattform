from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from platform_app.intake.models import now
from platform_app.shared.db import Base


class ExplanationRequest(Base):
    __tablename__ = "explanation_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"], ["assessments.organization_id", "assessments.id"]
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
        ),
        UniqueConstraint("organization_id", "created_by_user_id", "idempotency_key"),
        CheckConstraint("status IN ('RESERVED','SUCCEEDED','FAILED')"),
        CheckConstraint("reserved_usd >= 0"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    assessment_id: Mapped[UUID] = mapped_column(Uuid)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(20), default="RESERVED")
    request_hash: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(160))
    price_version: Mapped[str] = mapped_column(String(160))
    reserved_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    input_hash: Mapped[str] = mapped_column(String(64))
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    failure_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProviderBudgetDay(Base):
    __tablename__ = "provider_budget_days"
    __table_args__ = (CheckConstraint("reserved_usd >= 0"),)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    budget_date: Mapped[date] = mapped_column(Date, primary_key=True)
    reserved_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal(0))
