"""Persistenz: begrenzte Blobs, Datensätze, Aufträge und unveränderliche Versionen."""

from datetime import datetime
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

from platform_app.intake.models import now
from platform_app.shared.db import Base


class DataBlob(Base):
    __tablename__ = "data_blobs"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        CheckConstraint("octet_length(content) BETWEEN 1 AND 524288"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    content_hash: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes | None] = mapped_column(LargeBinary)
    object_id: Mapped[UUID | None] = mapped_column(Uuid)
    storage_meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        ForeignKeyConstraint(
            ["organization_id", "original_blob_id"], ["data_blobs.organization_id", "data_blobs.id"]
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
        ),
        CheckConstraint("current_version >= 0"),
        Index("ix_datasets_org_created", "organization_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid)
    name: Mapped[str] = mapped_column(String(160))
    filename: Mapped[str] = mapped_column(String(160))
    delimiter: Mapped[str] = mapped_column(String(4))
    original_blob_id: Mapped[UUID] = mapped_column(Uuid)
    original_hash: Mapped[str] = mapped_column(String(64))
    original_bytes: Mapped[int] = mapped_column(Integer)
    current_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DataJob(Base):
    __tablename__ = "data_jobs"
    __table_args__ = (
        UniqueConstraint("organization_id", "dataset_id", "id"),
        ForeignKeyConstraint(
            ["organization_id", "dataset_id"], ["datasets.organization_id", "datasets.id"]
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
        ),
        ForeignKeyConstraint(
            ["organization_id", "result_blob_id"], ["data_blobs.organization_id", "data_blobs.id"]
        ),
        CheckConstraint("kind IN ('IMPORT', 'PREVIEW')"),
        CheckConstraint("status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')"),
        CheckConstraint(
            "(kind = 'IMPORT' AND source_version IS NULL) OR (kind = 'PREVIEW' AND source_version > 0)"
        ),
        CheckConstraint(
            "(status IN ('QUEUED', 'RUNNING') AND finished_at IS NULL AND result_blob_id IS NULL AND profile IS NULL AND error IS NULL) OR (status = 'SUCCEEDED' AND finished_at IS NOT NULL AND result_blob_id IS NOT NULL AND profile IS NOT NULL AND error IS NULL) OR (status IN ('FAILED', 'CANCELLED') AND finished_at IS NOT NULL AND result_blob_id IS NULL AND profile IS NULL AND error IS NOT NULL)"
        ),
        Index("ix_jobs_queue", "organization_id", "status", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    dataset_id: Mapped[UUID] = mapped_column(Uuid)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid)
    kind: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(12), default="QUEUED")
    source_version: Mapped[int | None] = mapped_column(Integer)
    processing_mode: Mapped[str] = mapped_column(String, default="LEGACY")
    lease_token: Mapped[UUID | None] = mapped_column(Uuid)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[str] = mapped_column(String(160), default="")
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    import_options: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    result_blob_id: Mapped[UUID | None] = mapped_column(Uuid)
    result_hash: Mapped[str | None] = mapped_column(String(64))
    profile: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DataVersion(Base):
    __tablename__ = "data_versions"
    __table_args__ = (
        UniqueConstraint("organization_id", "dataset_id", "version_no"),
        UniqueConstraint("organization_id", "job_id"),
        ForeignKeyConstraint(
            ["organization_id", "dataset_id"], ["datasets.organization_id", "datasets.id"]
        ),
        ForeignKeyConstraint(
            ["organization_id", "dataset_id", "job_id"],
            ["data_jobs.organization_id", "data_jobs.dataset_id", "data_jobs.id"],
        ),
        ForeignKeyConstraint(
            ["organization_id", "blob_id"], ["data_blobs.organization_id", "data_blobs.id"]
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
        ),
        CheckConstraint("version_no > 0"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    dataset_id: Mapped[UUID] = mapped_column(Uuid)
    job_id: Mapped[UUID] = mapped_column(Uuid)
    blob_id: Mapped[UUID] = mapped_column(Uuid)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid)
    version_no: Mapped[int] = mapped_column(Integer)
    source_version: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
