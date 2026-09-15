"""Strikte Verträge für M2-Analysen, Regeln, Quellen und beaufsichtigte Pläne."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from platform_app.data.schemas import DataProfile, Step, StrictModel


class QualityRule(StrictModel):
    column: str = Field(min_length=1, max_length=100)
    operation: Literal[
        "required", "unique", "decimal", "date", "boolean", "range", "allowed_values"
    ]
    minimum: str | None = Field(default=None, max_length=100)
    maximum: str | None = Field(default=None, max_length=100)
    values: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def arguments(self) -> "QualityRule":
        if self.operation == "range":
            if self.minimum is None and self.maximum is None:
                raise ValueError("Mindestens eine Bereichsgrenze ist erforderlich.")
            try:
                bounds = [Decimal(v) for v in (self.minimum, self.maximum) if v is not None]
                if any(not v.is_finite() or abs(v.adjusted()) > 100 for v in bounds):
                    raise ValueError()
                if len(bounds) == 2 and bounds[0] > bounds[1]:
                    raise ValueError()
            except (ValueError, InvalidOperation):
                raise ValueError("Ungültige oder vertauschte Dezimalgrenzen.") from None
        elif self.minimum is not None or self.maximum is not None:
            raise ValueError("Grenzen sind nur für Bereichsregeln zulässig.")
        if (self.operation == "allowed_values") != bool(self.values):
            raise ValueError("Werteliste nur für erlaubte Werte angeben.")
        if any(
            len(v) > 512 or "\x00" in v or any(0xD800 <= ord(c) <= 0xDFFF for c in v)
            for v in self.values
        ):
            raise ValueError("Ungültiger oder zu langer erlaubter Wert.")
        return self


class RuleSetInput(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    rules: list[QualityRule] = Field(min_length=1, max_length=50)
    replaces_id: UUID | None = None


class RuleSetView(RuleSetInput):
    id: UUID
    created_at: datetime
    created_by_user_id: UUID


class AnalysisInput(StrictModel):
    version_no: int = Field(ge=1)
    numeric_columns: list[str] = Field(default_factory=list, max_length=8)
    date_column: str | None = Field(default=None, max_length=100)
    time_metric: str | None = Field(default=None, max_length=100)
    time_grain: Literal["day", "month"] = "month"
    ruleset_id: UUID | None = None
    rules: list[QualityRule] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def selection(self) -> "AnalysisInput":
        if len(set(self.numeric_columns)) != len(self.numeric_columns):
            raise ValueError("Numerische Spalten dürfen nicht doppelt gewählt werden.")
        if self.time_metric and not self.date_column:
            raise ValueError("Eine Zeitspalte ist erforderlich.")
        if self.ruleset_id and self.rules:
            raise ValueError("Gespeicherten Regelsatz oder einzelne Regeln wählen.")
        return self


class SourceImportInput(StrictModel):
    source_id: str = Field(min_length=1, max_length=80)
    table: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=160)


class PlanInput(StrictModel):
    version_no: int = Field(ge=1)
    mode: Literal["rules", "openai"] = "rules"
    approve_external_processing: bool = False


class PlanSelection(StrictModel):
    candidate_ids: list[str] = Field(max_length=10)


class NumericStatistics(StrictModel):
    column: str
    count: int
    missing: int
    invalid: int
    mean: str | None
    minimum: str | None
    q1: str | None
    median: str | None
    q3: str | None
    maximum: str | None
    sample_stddev: str | None
    outliers: int
    histogram: list[int]


class Correlation(StrictModel):
    x: str
    y: str
    pairs: int
    pearson: str | None


class RuleResult(StrictModel):
    rule: QualityRule
    checked: int
    failed: int
    example_rows: list[int]


class TimePeriod(StrictModel):
    period: str
    rows: int
    valid_values: int
    sum: str | None
    mean: str | None


class TimeSeries(StrictModel):
    column: str | None
    metric: str | None
    grain: Literal["day", "month"]
    invalid_dates: int
    missing_dates: int
    invalid_or_missing_metrics: int
    total_periods: int
    periods: list[TimePeriod]


class RuleSetReference(StrictModel):
    id: str
    name: str
    created_at: str


class AnalysisResult(StrictModel):
    engine_version: str
    profile: DataProfile
    options: AnalysisInput
    numeric: list[NumericStatistics]
    correlations: list[Correlation]
    rules: list[RuleResult]
    score: str | None
    score_method: str
    time_series: TimeSeries
    notes: list[str]
    ruleset: RuleSetReference | None
    dataset_id: str
    version_no: int
    content_hash: str
    original_hash: str


class PlanCandidate(StrictModel):
    id: str
    step: Step
    reason: str
    evidence: str
    risk: Literal["MEDIUM"]


class PlanTrace(StrictModel):
    role: str
    decision: str


class PlanResult(StrictModel):
    mode: Literal["rules", "openai"]
    prompt_version: str
    source_hash: str
    steps: list[Step]
    candidates: list[PlanCandidate]
    facts: dict[str, int]
    uncertainty: str
    required_decision: str
    trace: list[PlanTrace]
    reserved_usd: str
    model: str | None
    price_version: str | None
    input_hash: str


class SourceResult(StrictModel):
    dataset_id: str
    job_id: str
    original_hash: str
    source: dict[str, Any]


class TaskSummary(StrictModel):
    id: UUID
    created_by_user_id: UUID
    dataset_id: UUID | None
    version_no: int | None
    kind: Literal["ANALYSIS", "SOURCE", "PLAN"]
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"]
    progress: int
    message: str
    error: str | None
    result_hash: str | None
    created_at: datetime
    finished_at: datetime | None


class TaskView(TaskSummary):
    result: AnalysisResult | PlanResult | SourceResult | None
    request: dict[str, Any]


class SourceView(StrictModel):
    id: str
    name: str
    tables: list[str]
    provider: Literal["postgresql"]


class SourceCatalog(StrictModel):
    items: list[SourceView]
    live_ai_available: bool
