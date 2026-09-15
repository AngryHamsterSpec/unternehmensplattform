"""Deterministischer Manager: Regeln, Kosten, Ranking und prüfbare Erklärungen."""

import hashlib
import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, cast

from platform_app.decisions.catalog import RULE_VERSION, load_catalog
from platform_app.decisions.schemas import (
    AssessmentOptions,
    AssessmentResult,
    CandidateResult,
    ComponentAssignment,
    Constraint,
    CostLine,
    CostResult,
    Evidence,
    ScenarioInput,
    SensitivityResult,
    SensitivityVariation,
    VerificationResult,
    WeightGroup,
    WorkloadAssignment,
)

D = Decimal
GROUPS = ("cost", "performance", "resilience", "operations", "governance")
PRESETS = {
    "ECONOMIC": dict(zip(GROUPS, map(D, ("35", "15", "20", "20", "10")), strict=True)),
    "PERFORMANCE": dict(zip(GROUPS, map(D, ("15", "35", "25", "10", "15")), strict=True)),
}


def rounded(value: Decimal) -> Decimal:
    return value.quantize(D(".01"), rounding=ROUND_HALF_UP)


def fingerprint(value: Any) -> str:
    data = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(data.encode("utf8")).hexdigest()


def weights_for(options: AssessmentOptions) -> dict[WeightGroup, Decimal]:
    values = (
        options.custom_weights
        if options.weight_profile == "CUSTOM"
        else PRESETS[options.weight_profile]
    )
    assert values is not None
    total = sum(values.values(), D(0))
    return {cast(WeightGroup, key): value / total for key, value in values.items()}


def price_value(value: Any) -> Decimal | None:
    """Eine fehlende/ungültige Preisquelle ergibt unbekannte Kosten, niemals null."""
    if value is None:
        return None
    try:
        number = D(str(value))
    except (ValueError, ArithmeticError):
        return None
    return number if number.is_finite() and D(0) <= number <= D("1000000000000") else None


def constraint_results(
    scenario: ScenarioInput,
    plan: dict[str, Any],
    costs: CostResult,
    catalog: dict[str, Any],
    valuation_date: date,
) -> list[Constraint]:
    result: list[Constraint] = []

    def check(key: str, known: bool, passed: bool, explanation: str) -> None:
        result.append(
            Constraint(
                key=key,
                status="UNKNOWN" if not known else "PASS" if passed else "FAIL",
                explanation=explanation,
                evidence_ids=[
                    "input:scenario",
                    "input:options",
                    "catalog:" + plan["key"],
                    "rules:scoring",
                ],
            )
        )

    valid_prices = (
        date.fromisoformat(catalog["price_date"])
        <= valuation_date
        <= date.fromisoformat(catalog["valid_until"])
    )
    check(
        "price_validity",
        valid_prices,
        valid_prices,
        f"Synthetischer Preisstand gültig von {catalog['price_date']} bis {catalog['valid_until']}; Bewertungsdatum {valuation_date}.",
    )
    check(
        "region",
        True,
        scenario.requirements.region == "EU",
        "Der Demokatalog modelliert nur die EU.",
    )
    staff = scenario.company_profile.it_staff_fte
    check(
        "staff",
        staff is not None,
        staff is not None and staff >= D(plan["staff"]),
        f"Mindestens {plan['staff']} IT-Vollzeitstellen für den gesamten Modellplan erforderlich.",
    )
    for workload in scenario.workloads:
        key = workload.workload_key
        check(
            key + ":function",
            True,
            workload.workload_type in plan["supported"],
            "Der Katalog muss den angegebenen Arbeitslasttyp ausdrücklich unterstützen.",
        )
        for field in ("user_count", "vcpu_count", "memory_gib", "storage_gib"):
            required = getattr(workload, field)
            capacity = price_value(plan.get("capacities", {}).get(field))
            check(
                key + ":capacity:" + field,
                required is not None and capacity is not None,
                required is not None and capacity is not None and required <= capacity,
                f"Kapazität je Arbeitslast für {field}: {capacity if capacity is not None else 'unbekannt'}; Bedarf {required if required is not None else 'unbekannt'}.",
            )
        for field, actual, operator in [
            ("max_latency_ms", D(plan["latency"]), "max"),
            ("availability_percent", D(plan["availability"]), "min"),
            ("rto_seconds", D(plan["rto"]), "max"),
            ("rpo_seconds", D(plan["rpo"]), "max"),
        ]:
            target = getattr(workload, field)
            passed = target is not None and (
                actual <= target if operator == "max" else actual >= target
            )
            check(
                key + ":" + field,
                target is not None,
                passed,
                f"Modellwert {actual}; Anforderung {target if target is not None else 'unbekannt'}.",
            )
        check(
            key + ":internet",
            workload.internet_dependency_allowed is not None,
            workload.internet_dependency_allowed is True,
            "Alle vier Demopläne benötigen eine Cloudverbindung, beim Hybridplan für die zugesagte Sicherung und Wiederherstellung.",
        )
        check(
            key + ":sensitivity",
            workload.sensitivity is not None,
            workload.sensitivity != "RESTRICTED",
            "Für streng vertrauliche Daten fehlt im Demokatalog ein ausreichender Nachweis.",
        )
    if scenario.requirements.hard_budget:
        profile = scenario.company_profile
        known = (
            costs.complete
            and profile.initial_budget is not None
            and profile.monthly_budget is not None
        )
        passed = bool(
            known
            and costs.startup_total is not None
            and costs.monthly_total is not None
            and profile.initial_budget is not None
            and profile.monthly_budget is not None
            and costs.startup_total <= profile.initial_budget
            and costs.monthly_total <= profile.monthly_budget
        )
        check(
            "budget",
            known,
            passed,
            "Einmaliges und monatliches Budget als getrennte harte Grenzen.",
        )
    return result


def calculate_costs(
    scenario: ScenarioInput,
    plan: dict[str, Any],
    horizon: int,
    catalog: dict[str, Any] | None = None,
) -> CostResult:
    catalog = load_catalog() if catalog is None else catalog
    lines: list[CostLine] = []

    def add(
        identifier: str,
        label: str,
        category: str,
        recurrence: str,
        quantity: Decimal | None,
        price: Any,
        price_id: str,
        evidence: str,
    ) -> None:
        unit_price = price_value(price)
        amount = None if quantity is None or unit_price is None else rounded(quantity * unit_price)
        lines.append(
            CostLine(
                id=identifier,
                label=label,
                category=category,
                recurrence=recurrence,
                quantity=quantity,
                unit_price=unit_price,
                total=None
                if amount is None
                else amount * (horizon if recurrence == "MONTHLY" else 1),
                price_id=price_id,
                evidence_ids=["input:scenario", "input:options", evidence],
            )
        )

    for workload in scenario.workloads:
        quantity = (
            (D(workload.user_count) if workload.user_count is not None else None)
            if plan["unit"] == "user"
            else workload.vcpu_count
        )
        add(
            workload.workload_key + ":runtime",
            workload.name + ": Betriebsleistung",
            "OPEX",
            "MONTHLY",
            quantity,
            plan.get("monthly_unit"),
            plan["key"] + ":runtime",
            "catalog:" + plan["key"],
        )
        add(
            workload.workload_key + ":storage",
            workload.name + ": Speicher und Sicherung",
            "OPEX",
            "MONTHLY",
            workload.storage_gib,
            catalog.get("storage_monthly_unit"),
            "storage-giB-month",
            "catalog:storage",
        )
        add(
            workload.workload_key + ":memory",
            workload.name + ": Arbeitsspeicher",
            "OPEX",
            "MONTHLY",
            workload.memory_gib,
            catalog.get("memory_monthly_unit"),
            "memory-giB-month",
            "catalog:memory",
        )
    add(
        "setup",
        "Einrichtung / Hardware (Demowert)",
        "CAPEX" if plan["key"] == "HYBRID" else "OPEX",
        "ONCE",
        D(1),
        plan.get("setup"),
        plan["key"] + ":setup",
        "catalog:" + plan["key"],
    )
    add(
        "operations",
        "Interner Betrieb (Demoverrechnung)",
        "OPEX",
        "MONTHLY",
        D(plan["staff"]),
        catalog.get("staff_monthly_unit"),
        "staff-fte-month",
        "catalog:staff",
    )

    def total_for(field: str, match: str) -> Decimal | None:
        selected = [line.total for line in lines if getattr(line, field) == match]
        return (
            None
            if any(value is None for value in selected)
            else sum((value for value in selected if value is not None), D(0))
        )

    capex = total_for("category", "CAPEX")
    opex = total_for("category", "OPEX")
    monthly = total_for("recurrence", "MONTHLY")
    complete = all(line.total is not None for line in lines)
    return CostResult(
        complete=complete,
        capex_total=capex,
        opex_total=opex,
        tco_total=capex + opex if capex is not None and opex is not None else None,
        startup_total=total_for("recurrence", "ONCE"),
        monthly_total=monthly / horizon if monthly is not None else None,
        lines=lines,
    )


def criterion_values(
    scenario: ScenarioInput, plan: dict[str, Any], costs: CostResult, horizon: int
) -> dict[WeightGroup, Decimal | None]:
    profile = scenario.company_profile
    budget = (
        None
        if profile.initial_budget is None or profile.monthly_budget is None
        else profile.initial_budget + profile.monthly_budget * horizon
    )
    cost = (
        None
        if costs.tco_total is None or budget is None
        else D(100)
        if budget == 0 and costs.tco_total == 0
        else D(0)
        if budget == 0
        else max(D(0), D(100) - D(50) * costs.tco_total / budget)
    )
    latencies = [workload.max_latency_ms for workload in scenario.workloads]
    performance = (
        None
        if any(value is None for value in latencies)
        else sum(
            (
                max(D(0), D(100) - D(50) * D(plan["latency"]) / value)
                for value in latencies
                if value is not None
            ),
            D(0),
        )
        / len(latencies)
    )
    rtos = [workload.rto_seconds for workload in scenario.workloads]
    resilience = (
        None
        if any(value is None for value in rtos)
        else sum(
            (
                max(D(0), D(100) - D(50) * D(plan["rto"]) / max(D(1), D(value)))
                for value in rtos
                if value is not None
            ),
            D(0),
        )
        / len(rtos)
    )
    operations = (
        None
        if profile.it_staff_fte is None
        else max(D(0), D(100) * (D(1) - D(plan["staff"]) / (profile.it_staff_fte + 1)))
    )
    values = {
        "cost": cost,
        "performance": performance,
        "resilience": resilience,
        "operations": operations,
        "governance": D(plan["governance"]),
    }
    return {
        cast(WeightGroup, key): None if value is None else rounded(min(D(100), value))
        for key, value in values.items()
    }


def evaluate(scenario: ScenarioInput, options: AssessmentOptions) -> AssessmentResult:
    from platform_app.decisions.verifier import verify

    catalog = load_catalog()
    weights = weights_for(options)
    evidence = [
        Evidence(
            id="input:scenario",
            kind="INPUT",
            label="Bewertete Eingabefassung",
            source="Nutzereingabe",
            version="scenario-v1",
            value=fingerprint(scenario.model_dump(mode="json")),
        ),
        Evidence(
            id="input:options",
            kind="INPUT",
            label="Bewertungsoptionen mit festem Bewertungsdatum",
            source="Nutzereingabe",
            version="assessment-options-v1",
            value=fingerprint(options.model_dump(mode="json")),
        ),
        Evidence(
            id="rules:scoring",
            kind="RULE",
            label="Versionierte Rechenregeln und Bewertungsanker",
            source="decisions/EXPLAIN.md",
            version=RULE_VERSION,
            value=RULE_VERSION,
        ),
    ]
    for suffix, field, label in [
        ("storage", "storage_monthly_unit", "Speicherpreis je GiB/Monat"),
        ("memory", "memory_monthly_unit", "RAM-Preis je GiB/Monat"),
        ("staff", "staff_monthly_unit", "Verrechnung je Vollzeitstelle/Monat"),
    ]:
        evidence.append(
            Evidence(
                id="catalog:" + suffix,
                kind="CATALOG",
                label=label,
                source=catalog["source"],
                version=catalog["version"],
                value=catalog.get(field),
            )
        )
    candidates: list[CandidateResult] = []
    for plan in catalog["plans"]:
        key = plan["key"]
        evidence.append(
            Evidence(
                id="catalog:" + key,
                kind="CATALOG",
                label=plan["label"],
                source=catalog["source"],
                version=catalog["version"],
                value=plan,
            )
        )
        costs = calculate_costs(scenario, plan, options.horizon_months, catalog)
        constraints = constraint_results(scenario, plan, costs, catalog, options.valuation_date)
        values = criterion_values(scenario, plan, costs, options.horizon_months)
        excluded = any(constraint.status == "FAIL" for constraint in constraints)
        unknown = (
            any(constraint.status == "UNKNOWN" for constraint in constraints)
            or not costs.complete
            or any(values[group] is None and weights[group] > 0 for group in weights)
        )
        status = "EXCLUDED" if excluded else "INDETERMINATE" if unknown else "ELIGIBLE"
        score = (
            rounded(sum((weights[group] * (values[group] or D(0)) for group in weights), D(0)))
            if status == "ELIGIBLE"
            else None
        )
        components = [
            ComponentAssignment(
                role="Primärbetrieb",
                service_model=plan["service"],
                deployment_model=plan["deployment"],
                hosting_location=plan["location"],
            )
        ]
        if key == "HYBRID":
            components.append(
                ComponentAssignment(
                    role="Asynchrone Cloud-Sicherung",
                    service_model="PAAS",
                    deployment_model="PUBLIC_CLOUD",
                    hosting_location="PROVIDER",
                )
            )
        assignments = [
            WorkloadAssignment(
                workload_key=workload.workload_key,
                service_model=plan["service"],
                deployment_model=plan["deployment"],
                hosting_location=plan["location"],
                components=components,
                explanation="Verbundene lokale Anwendung und Cloud-Sicherung."
                if key == "HYBRID"
                else plan["label"],
                evidence_ids=["input:scenario", "catalog:" + key],
            )
            for workload in scenario.workloads
        ]
        uncertainties = [
            constraint.explanation for constraint in constraints if constraint.status == "UNKNOWN"
        ]
        if not costs.complete:
            uncertainties.append("Relevante Kostenmengen oder gültige Einzelpreise fehlen.")
        uncertainties.extend(
            "Das gewichtete Kriterium " + group + " ist unbekannt."
            for group in weights
            if values[group] is None and weights[group] > 0
        )
        candidates.append(
            CandidateResult(
                key=key,
                label=plan["label"],
                status=status,
                score=score,
                assignments=assignments,
                criterion_scores=values,
                constraints=constraints,
                costs=costs,
                evidence_ids=["input:scenario", "input:options", "catalog:" + key, "rules:scoring"],
                assumptions=[
                    "Synthetische Kapazitäts-, SLA-, Personal- und Kostenannahmen; kein Anbieterangebot.",
                    catalog["coverage"],
                ],
                uncertainties=uncertainties,
                explanation="Muss-Anforderung verletzt."
                if excluded
                else "Erforderliche Angaben oder Belege fehlen."
                if unknown
                else "Alle im Modell prüfbaren Muss-Anforderungen erfüllt.",
            )
        )
    eligible = sorted(
        (candidate for candidate in candidates if candidate.status == "ELIGIBLE"),
        key=lambda candidate: (-(candidate.score or D(0)), candidate.key),
    )
    rank_scores = sorted(
        {candidate.score for candidate in eligible if candidate.score is not None}, reverse=True
    )
    for candidate in eligible:
        assert candidate.score is not None
        candidate.rank = rank_scores.index(candidate.score) + 1
    incomplete = any(candidate.status == "INDETERMINATE" for candidate in candidates)
    winner = eligible[0].key if eligible and not incomplete else None
    variations: list[SensitivityVariation] = []
    if eligible and not incomplete:
        for group in weights:
            for factor in (D(".8"), D("1.2")):
                changed_weights = {
                    key: value * (factor if key == group else 1) for key, value in weights.items()
                }
                total = sum(changed_weights.values(), D(0))
                ordered = sorted(
                    eligible,
                    key=lambda candidate: (
                        -rounded(
                            sum(
                                (
                                    changed_weights[key]
                                    * (candidate.criterion_scores[key] or D(0))
                                    / total
                                    for key in weights
                                ),
                                D(0),
                            )
                        ),
                        candidate.key,
                    ),
                )
                chosen = ordered[0].key
                variations.append(
                    SensitivityVariation(
                        group=group, factor=factor, winner_key=chosen, changed=chosen != winner
                    )
                )
    status = "INCOMPLETE" if incomplete else "VERIFIED" if eligible else "NO_FEASIBLE_OPTION"
    gap = (
        eligible[0].score - eligible[1].score
        if len(eligible) > 1 and eligible[0].score is not None and eligible[1].score is not None
        else None
    )
    result = AssessmentResult(
        status=status,
        candidates=candidates,
        recommended_candidate_key=winner,
        weights=weights,
        horizon_months=options.horizon_months,
        verification=VerificationResult(valid=False, errors=[], checks=[]),
        sensitivity=SensitivityResult(
            tested_variations=len(variations),
            winner_changes=sum(variation.changed for variation in variations),
            score_gap=rounded(gap) if gap is not None and not incomplete else None,
            variations=variations,
            explanation="Einzelgewichte um ±20 % verändert; keine statistische Erfolgswahrscheinlichkeit."
            if variations
            else "Ohne vollständig belegten Vergleich wird keine Rangstabilität behauptet.",
        ),
        rule_set_version=RULE_VERSION,
        candidate_catalog_version=catalog["version"],
        cost_catalog_version=catalog["version"],
        evidence=evidence,
        assumptions=[
            catalog["source"],
            catalog["coverage"],
            "Governance-Werte sind dokumentierte Demo-Ratings, keine Sicherheitsmessung.",
        ],
        uncertainties=[
            "Nur vier unterstützte Modellpläne; keine globale Optimierung.",
            "Bestehende Assets sind Inventarangaben. Wiederverwendung oder Restwert werden nicht ohne Eignungsnachweis gutgeschrieben.",
        ],
        explanation=f"Unter den angegebenen Annahmen führt {eligible[0].label}."
        if winner
        else "Keine belegbar geeignete Alternative. Fehlende Angaben oder Ausschlussgründe prüfen.",
    )
    result.verification = verify(scenario, options, result)
    if not result.verification.valid:
        result.status = "VERIFICATION_FAILED"
        result.recommended_candidate_key = None
        result.explanation = (
            "Die unabhängige Prüfung meldet Widersprüche. Es wird keine Empfehlung freigegeben."
        )
    return result
