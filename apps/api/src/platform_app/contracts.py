"""Explizite Antwortmodelle für OpenAPI und die gespeicherten Fachverträge."""

from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel

from platform_app.decisions.schemas import AssessmentOptions, AssessmentResult, ScenarioInput

T = TypeVar("T")


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None


class VersionView(BaseModel):
    id: UUID
    version_no: int
    data: ScenarioInput


class VersionSummary(BaseModel):
    id: UUID
    version_no: int
    created_at: datetime


class ScenarioView(BaseModel):
    id: UUID
    name: str
    current_version: int
    created_at: datetime
    version: VersionView
    versions: list[VersionSummary]


class AssessmentView(AssessmentResult):
    id: UUID
    scenario_version_id: UUID
    created_at: datetime
    result_hash: str
    options: AssessmentOptions


class AuditView(BaseModel):
    id: UUID
    created_at: datetime
    actor_user_id: UUID
    event_type: str
    entity_type: str
    entity_id: UUID | None
    metadata: dict[str, Any]
