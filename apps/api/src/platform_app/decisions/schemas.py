"""Strenge, JSON-fähige Eingabe- und Ergebnisverträge; Geld wird Decimal."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonnegativeDecimal = Annotated[
    Decimal, Field(ge=0, le=Decimal("1000000000000"), allow_inf_nan=False, decimal_places=6)
]
PositiveDecimal = Annotated[
    Decimal, Field(gt=0, le=Decimal("1000000000"), allow_inf_nan=False, decimal_places=6)
]
Percent = Annotated[Decimal, Field(ge=0, le=100, allow_inf_nan=False)]
MoneyTotal = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]
WeightGroup = Literal["cost", "performance", "resilience", "operations", "governance"]
PlanKey = Literal["SAAS", "PAAS", "IAAS", "HYBRID"]
WorkloadType = Literal["BUSINESS_APP", "WEB_APP", "DATABASE", "FILE_STORAGE", "ANALYTICS", "OTHER"]
Sensitivity = Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"]


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class CompanyProfile(DTO):
    industry: str = Field(min_length=1, max_length=120)
    employee_count: int | None = Field(default=None, ge=1, le=1000000)
    it_staff_fte: NonnegativeDecimal | None = None
    monthly_budget: NonnegativeDecimal | None = None
    initial_budget: NonnegativeDecimal | None = None
    currency: Literal["EUR"] = "EUR"


class Workload(DTO):
    workload_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=160)
    workload_type: WorkloadType
    user_count: int | None = Field(default=None, ge=1, le=1000000)
    vcpu_count: PositiveDecimal | None = None
    memory_gib: PositiveDecimal | None = None
    storage_gib: NonnegativeDecimal | None = None
    max_latency_ms: PositiveDecimal | None = None
    availability_percent: Percent | None = None
    rto_seconds: int | None = Field(default=None, ge=0, le=31536000)
    rpo_seconds: int | None = Field(default=None, ge=0, le=31536000)
    sensitivity: Sensitivity | None = None
    internet_dependency_allowed: bool | None = None


class InfrastructureAsset(DTO):
    asset_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=160)
    asset_type: Literal["SERVER", "STORAGE", "NETWORK", "LICENSE", "OTHER"]
    quantity: int = Field(default=1, ge=1, le=1000000)
    notes: str = Field(default="", max_length=2000)


class Requirements(DTO):
    region: str = Field(default="EU", min_length=2, max_length=64)
    hard_budget: bool = False


class ScenarioInput(DTO):
    name: str = Field(min_length=1, max_length=160)
    company_profile: CompanyProfile
    workloads: list[Workload] = Field(min_length=1, max_length=10)
    infrastructure_assets: list[InfrastructureAsset] = Field(default_factory=list, max_length=100)
    requirements: Requirements = Field(default_factory=Requirements)

    @model_validator(mode="after")
    def unique_keys(self) -> Self:
        for entries in (self.workloads, self.infrastructure_assets):
            keys = [
                entry.workload_key if isinstance(entry, Workload) else entry.asset_key
                for entry in entries
            ]
            if len(keys) != len(set(keys)):
                raise ValueError("Schlüssel innerhalb einer Liste müssen eindeutig sein.")
        return self


class AssessmentOptions(DTO):
    weight_profile: Literal["ECONOMIC", "PERFORMANCE", "CUSTOM"] = "ECONOMIC"
    custom_weights: dict[WeightGroup, NonnegativeDecimal] | None = None
    horizon_months: int = Field(default=36, ge=1, le=120)
    valuation_date: date = Field(default_factory=date.today)

    @model_validator(mode="after")
    def complete_weights(self) -> Self:
        expected = {"cost", "performance", "resilience", "operations", "governance"}
        if self.weight_profile == "CUSTOM":
            if self.custom_weights is None or set(self.custom_weights) != expected:
                raise ValueError("Eigene Gewichte benötigen genau alle fünf Bewertungsgruppen.")
            if sum(self.custom_weights.values(), Decimal(0)) <= 0:
                raise ValueError("Die Summe der Gewichte muss größer als null sein.")
        elif self.custom_weights is not None:
            raise ValueError("Eigene Gewichte sind nur im Profil CUSTOM zulässig.")
        return self


class Evidence(DTO):
    id: str
    kind: Literal["INPUT", "CATALOG", "RULE", "CALCULATION"]
    label: str
    source: str
    version: str
    value: Any = None


class Constraint(DTO):
    key: str
    status: Literal["PASS", "FAIL", "UNKNOWN"]
    explanation: str
    evidence_ids: list[str]


class CostLine(DTO):
    id: str
    label: str
    category: Literal["CAPEX", "OPEX"]
    recurrence: Literal["ONCE", "MONTHLY"]
    quantity: NonnegativeDecimal | None
    unit_price: NonnegativeDecimal | None
    total: MoneyTotal | None
    price_id: str
    evidence_ids: list[str]


class CostResult(DTO):
    currency: Literal["EUR"] = "EUR"
    complete: bool
    capex_total: MoneyTotal | None
    opex_total: MoneyTotal | None
    tco_total: MoneyTotal | None
    startup_total: MoneyTotal | None
    monthly_total: MoneyTotal | None
    lines: list[CostLine]


class ComponentAssignment(DTO):
    role: str
    service_model: Literal["SAAS", "PAAS", "IAAS", "SELF_MANAGED"]
    deployment_model: Literal["PUBLIC_CLOUD", "PRIVATE_CLOUD", "TRADITIONAL"]
    hosting_location: Literal["PROVIDER", "ON_PREMISES", "COLOCATION"]


class WorkloadAssignment(DTO):
    workload_key: str
    service_model: Literal["SAAS", "PAAS", "IAAS", "SELF_MANAGED"]
    deployment_model: Literal["PUBLIC_CLOUD", "PRIVATE_CLOUD", "TRADITIONAL"]
    hosting_location: Literal["PROVIDER", "ON_PREMISES", "COLOCATION"]
    components: list[ComponentAssignment]
    explanation: str
    evidence_ids: list[str]


class CandidateResult(DTO):
    key: PlanKey
    label: str
    status: Literal["ELIGIBLE", "INDETERMINATE", "EXCLUDED"]
    score: Percent | None
    rank: int | None = Field(default=None, ge=1, le=20)
    assignments: list[WorkloadAssignment]
    criterion_scores: dict[WeightGroup, Percent | None]
    constraints: list[Constraint]
    costs: CostResult
    evidence_ids: list[str]
    assumptions: list[str]
    uncertainties: list[str]
    explanation: str


class VerificationResult(DTO):
    valid: bool
    errors: list[str]
    checks: list[str]


class SensitivityVariation(DTO):
    group: WeightGroup
    factor: NonnegativeDecimal
    winner_key: PlanKey | None
    changed: bool


class SensitivityResult(DTO):
    tested_variations: int = Field(ge=0)
    winner_changes: int = Field(ge=0)
    score_gap: Percent | None
    variations: list[SensitivityVariation]
    explanation: str


class AssessmentResult(DTO):
    status: Literal["VERIFIED", "INCOMPLETE", "NO_FEASIBLE_OPTION", "VERIFICATION_FAILED"]
    candidates: list[CandidateResult]
    recommended_candidate_key: PlanKey | None
    weights: dict[WeightGroup, MoneyTotal]
    horizon_months: int = Field(ge=1, le=120)
    verification: VerificationResult
    sensitivity: SensitivityResult
    rule_set_version: str
    candidate_catalog_version: str
    cost_catalog_version: str
    evidence: list[Evidence]
    assumptions: list[str]
    uncertainties: list[str]
    explanation: str


def as_json(model: DTO) -> dict[str, Any]:
    """Persistenz/API-Adapter: Dezimalwerte als Strings, keine float-Konvertierung."""
    return model.model_dump(mode="json")
