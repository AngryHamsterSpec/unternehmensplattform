"""Explizite Eventsemantik und versionierte Prozess-/Simulationsverträge."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Name = Annotated[str, Field(min_length=1, max_length=100)]
Seconds = Annotated[Decimal, Field(ge=0, le=3155760000, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventMapping(Contract):
    case: Name
    activity: Name
    timestamp: Name
    start: Name | None = None
    duration: Name | None = None
    actor: Name | None = None
    status: Name | None = None
    cost: Name | None = None
    department: Name | None = None
    priority: Name | None = None
    automated: Name | None = None
    event_id: Name | None = None

    @model_validator(mode="after")
    def distinct(self) -> Self:
        values = [v for v in self.model_dump().values() if v]
        if len(values) != len(set(values)):
            raise ValueError("Jede zugeordnete Spalte darf nur eine Bedeutung besitzen.")
        if self.start and self.duration:
            raise ValueError(
                "Startzeit oder Dauer auswählen; widersprüchliche Zeitquellen vermeiden."
            )
        return self


class ProcessInput(Contract):
    name: str = Field(min_length=1, max_length=160)
    dataset_id: UUID
    version_no: int = Field(ge=1)
    mapping: EventMapping
    naive_timestamps_as_utc: bool = False
    duplicate_policy: Literal["keep", "exclude_exact"] = "keep"
    end_activities: list[Name] = Field(default_factory=list, max_length=30)
    error_statuses: list[Name] = Field(
        default_factory=lambda: ["error", "failed", "fehler"], max_length=30
    )
    sla_seconds: Seconds | None = None
    wait_target_seconds: Seconds | None = None
    capacity_hours_per_actor: Decimal | None = Field(
        default=None, gt=0, le=1000000, allow_inf_nan=False
    )
    currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def semantics(self) -> Self:
        if self.sla_seconds is not None and not self.end_activities:
            raise ValueError(
                "SLA benötigt explizite Endaktivitäten zur Erkennung abgeschlossener Fälle."
            )
        if self.capacity_hours_per_actor is not None and not (
            self.mapping.actor and (self.mapping.start or self.mapping.duration)
        ):
            raise ValueError("Kapazitätsauswertung benötigt Actor und Startzeit oder Dauer.")
        return self


class ProcessKpis(Contract):
    events: int
    cases: int
    completed_cases: int | None
    observed_start: str
    observed_end: str
    cycle_mean_seconds: str
    cycle_median_seconds: str
    cycle_p90_seconds: str
    throughput_per_day: str | None
    wait_mean_seconds: str | None
    wait_covered_cases: int
    sequential_cases: int
    rework_case_percent: str
    error_event_percent: str | None
    automation_percent: str | None
    sla_percent: str | None
    sla_cases: int
    total_cost: str | None
    cost_events: int
    known_status_events: int
    known_automation_events: int
    quality_percent: str


class ProcessActivity(Contract):
    id: str
    name: str
    events: int
    cases: int
    errors: int
    repeats: int
    service_seconds: str
    service_events: int
    mean_position: float


class ProcessEdge(Contract):
    id: str
    source: str
    target: str
    events: int
    cases: int
    gap_seconds: str
    wait_seconds: str
    wait_observations: int
    mean_wait_seconds: str | None
    cycle_share_percent: str | None
    target_excess_seconds: str | None
    examples: list[str]


class ProcessVariant(Contract):
    id: str
    path: list[str]
    cases: int
    share_percent: str
    mean_cycle_seconds: str
    repeats: int
    errors: int
    examples: list[str]


class ProcessQuality(Contract):
    input_rows: int
    rejected_rows: int
    duplicate_rows: int
    excluded_duplicates: int
    tied_events: int
    reordered_cases: int
    overlapping_cases: int
    partial_cases: int
    missing_intervals: int
    invalid_optional_values: int
    examples: list[dict[str, Any]]


class Improvement(Contract):
    id: str
    target_kind: Literal["wait", "service"]
    target_id: str
    title: str
    evidence: str
    hypothesis: str
    risk: str
    validation: str
    affected_cases: int


class ProcessResult(Contract):
    kind: Literal["DISCOVERY"] = "DISCOVERY"
    method_version: str
    kpis: ProcessKpis
    quality: ProcessQuality
    activities: list[ProcessActivity]
    edges: list[ProcessEdge]
    variants: list[ProcessVariant]
    variants_total: int
    variants_covered_cases: int
    daily: list[dict[str, Any]]
    dimensions: dict[str, list[dict[str, Any]]]
    resources: list[dict[str, Any]]
    improvements: list[Improvement]
    cases_hash: str
    source_hash: str
    original_hash: str
    notes: list[str]


class SimulationInput(Contract):
    name: str = Field(min_length=1, max_length=160)
    target_kind: Literal["wait", "service"]
    target_id: str = Field(min_length=1, max_length=64)
    reduction_percent: Decimal = Field(gt=0, le=80, allow_inf_nan=False)
    hypothesis: str = Field(min_length=10, max_length=2000)
    risk: str = Field(min_length=10, max_length=2000)
    validation: str = Field(min_length=10, max_length=2000)
    estimated_cost: Decimal | None = Field(default=None, ge=0, le=1000000000, allow_inf_nan=False)


class SimulationResult(Contract):
    kind: Literal["SIMULATION"] = "SIMULATION"
    method_version: str
    parent_result_hash: str
    total_cases: int
    eligible_cases: int
    affected_cases: int
    baseline_mean_seconds: str
    projected_mean_seconds: str
    saved_seconds: str
    improvement_percent: str
    baseline_sla_percent: str | None
    projected_sla_percent: str | None
    sla_cases: int
    examples: list[dict[str, Any]]
    assumptions: list[str]
    source_hash: str


class ProcessSummary(Contract):
    id: UUID
    name: str
    dataset_id: UUID
    version_no: int
    parent_id: UUID | None
    kind: Literal["DISCOVERY", "SIMULATION"]
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"]
    progress: int
    message: str
    error: str | None
    result_hash: str | None
    created_by_user_id: UUID
    created_at: datetime
    finished_at: datetime | None


class ProcessView(ProcessSummary):
    config: dict[str, Any]
    result: ProcessResult | SimulationResult | None


class ProcessCaseSummary(Contract):
    case_key: str
    case_id: str
    variant_id: str
    events: int
    cycle_seconds: str
    wait_seconds: str | None
    repeats: int
    errors: int
    complete: bool | None
    sla_met: bool | None
    sequential: bool
    partial: bool
    first_at: str
    last_at: str


class ApprovalInput(Contract):
    result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["APPROVED", "REJECTED"]
    comment: str = Field(min_length=10, max_length=2000)


class ProcessApprovalView(ApprovalInput):
    id: UUID
    run_id: UUID
    created_by_user_id: UUID
    created_at: datetime
