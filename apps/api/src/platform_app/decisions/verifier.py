"""Unabhängige Nachrechnung ohne Aufruf des Managers oder seiner Rechenhelfer.

Nur DTOs und der versionierte Rohkatalog werden geteilt. Kosten, Constraints,
Kriterien, Gewichte, Zuordnungen und Sensitivität werden separat abgeleitet.
"""

import hashlib
import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from platform_app.decisions.catalog import RULE_VERSION, load_catalog
from platform_app.decisions.schemas import (
    AssessmentOptions,
    AssessmentResult,
    ScenarioInput,
    VerificationResult,
)

D = Decimal
GROUPS = ("cost", "performance", "resilience", "operations", "governance")
CHECKS = [
    "Eingabe-/Options-/Versionsbindung",
    "Evidenzinhalte und Referenzen",
    "Kosten aus Mengen und synthetischem Rohkatalog",
    "Kapazitäten und Muss-Bedingungen",
    "Unabhängige Kriterien- und Scoreberechnung",
    "Vollständige Architekturzuordnung",
    "Ergebnisstatus und Rangfolge",
    "Zehn nachgerechnete Sensitivitätsvarianten",
]


def cents(number: Decimal) -> Decimal:
    return number.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf8")
    return hashlib.sha256(encoded).hexdigest()


def valid_price(raw: Any) -> Decimal | None:
    try:
        number = D(str(raw))
        return number if number.is_finite() and 0 <= number <= D("1000000000000") else None
    except (ValueError, ArithmeticError):
        return None


def verify(
    scenario: ScenarioInput, options: AssessmentOptions, result: AssessmentResult
) -> VerificationResult:
    """Auch nachträglich beschädigte DTO-Instanzen führen zu einer Ablehnung."""
    try:
        AssessmentResult.model_validate(result.model_dump())
        return _verify(scenario, options, result)
    except (ArithmeticError, ValueError, TypeError, KeyError, AttributeError):
        return VerificationResult(
            valid=False,
            errors=["Das Ergebnis verletzt den Prüfvertrag und wurde abgelehnt."],
            checks=CHECKS,
        )


def _verify(
    scenario: ScenarioInput, options: AssessmentOptions, result: AssessmentResult
) -> VerificationResult:
    errors: list[str] = []
    catalog = load_catalog()
    plans = {plan["key"]: plan for plan in catalog["plans"]}
    raw_weights = (
        options.custom_weights
        if options.weight_profile == "CUSTOM"
        else dict(
            zip(
                GROUPS,
                map(
                    D,
                    ("35", "15", "20", "20", "10")
                    if options.weight_profile == "ECONOMIC"
                    else ("15", "35", "25", "10", "15"),
                ),
                strict=True,
            )
        )
    )
    assert raw_weights is not None
    weight_total = sum(raw_weights.values(), D(0))
    weights = {key: value / weight_total for key, value in raw_weights.items()}
    if result.weights != weights or result.horizon_months != options.horizon_months:
        errors.append("Gewichte oder Betrachtungszeitraum wurden verändert.")
    if (result.rule_set_version, result.candidate_catalog_version, result.cost_catalog_version) != (
        RULE_VERSION,
        catalog["version"],
        catalog["version"],
    ):
        errors.append("Versionsbindung stimmt nicht überein.")

    # Eine bloß existierende Kennung beweist keinen richtigen Evidenzinhalt.
    expected_evidence: dict[str, tuple[str, str, str, Any]] = {
        "input:scenario": (
            "INPUT",
            "Nutzereingabe",
            "scenario-v1",
            digest(scenario.model_dump(mode="json")),
        ),
        "input:options": (
            "INPUT",
            "Nutzereingabe",
            "assessment-options-v1",
            digest(options.model_dump(mode="json")),
        ),
        "rules:scoring": ("RULE", "decisions/EXPLAIN.md", RULE_VERSION, RULE_VERSION),
    }
    for suffix, field in (
        ("storage", "storage_monthly_unit"),
        ("memory", "memory_monthly_unit"),
        ("staff", "staff_monthly_unit"),
    ):
        expected_evidence["catalog:" + suffix] = (
            "CATALOG",
            catalog["source"],
            catalog["version"],
            catalog.get(field),
        )
    for key, plan in plans.items():
        expected_evidence["catalog:" + key] = (
            "CATALOG",
            catalog["source"],
            catalog["version"],
            plan,
        )
    evidence = {entry.id: entry for entry in result.evidence}
    if len(evidence) != len(result.evidence) or set(evidence) != set(expected_evidence):
        errors.append("Evidenzmenge fehlt, enthält Duplikate oder fremde Einträge.")
    for identifier, expected in expected_evidence.items():
        entry = evidence.get(identifier)
        if entry is None or (entry.kind, entry.source, entry.version, entry.value) != expected:
            errors.append(identifier + ": Evidenzinhalt stimmt nicht mit der Quelle überein.")
    if set(candidate.key for candidate in result.candidates) != set(plans) or len(
        result.candidates
    ) != len(plans):
        errors.append("Kandidatenmenge wurde verändert.")
    expected_states: dict[str, str] = {}
    expected_scores: dict[str, Decimal | None] = {}
    expected_criteria: dict[str, dict[str, Decimal | None]] = {}

    for candidate in result.candidates:
        key = candidate.key
        if key not in plans:
            continue
        plan = plans[key]
        expected_lines: list[tuple[str, str, str, Decimal | None, Decimal | None, str, str]] = []
        for workload in scenario.workloads:
            runtime_quantity = (
                (D(workload.user_count) if workload.user_count is not None else None)
                if plan["unit"] == "user"
                else workload.vcpu_count
            )
            expected_lines.extend(
                [
                    (
                        workload.workload_key + ":runtime",
                        "OPEX",
                        "MONTHLY",
                        runtime_quantity,
                        valid_price(plan.get("monthly_unit")),
                        key + ":runtime",
                        "catalog:" + key,
                    ),
                    (
                        workload.workload_key + ":storage",
                        "OPEX",
                        "MONTHLY",
                        workload.storage_gib,
                        valid_price(catalog.get("storage_monthly_unit")),
                        "storage-giB-month",
                        "catalog:storage",
                    ),
                    (
                        workload.workload_key + ":memory",
                        "OPEX",
                        "MONTHLY",
                        workload.memory_gib,
                        valid_price(catalog.get("memory_monthly_unit")),
                        "memory-giB-month",
                        "catalog:memory",
                    ),
                ]
            )
        expected_lines.extend(
            [
                (
                    "setup",
                    "CAPEX" if key == "HYBRID" else "OPEX",
                    "ONCE",
                    D(1),
                    valid_price(plan.get("setup")),
                    key + ":setup",
                    "catalog:" + key,
                ),
                (
                    "operations",
                    "OPEX",
                    "MONTHLY",
                    D(plan["staff"]),
                    valid_price(catalog.get("staff_monthly_unit")),
                    "staff-fte-month",
                    "catalog:staff",
                ),
            ]
        )
        lines = {line.id: line for line in candidate.costs.lines}
        if len(lines) != len(candidate.costs.lines) or set(lines) != {
            line[0] for line in expected_lines
        }:
            errors.append(key + ": Kostenzeilen fehlen oder sind doppelt/fremd.")
        classified: dict[str, list[Decimal | None]] = {
            "CAPEX": [],
            "OPEX": [],
            "ONCE": [],
            "MONTHLY": [],
        }
        for (
            identifier,
            category,
            recurrence,
            quantity,
            price,
            price_id,
            price_evidence,
        ) in expected_lines:
            expected_total = (
                None
                if quantity is None or price is None
                else cents(quantity * price)
                * (options.horizon_months if recurrence == "MONTHLY" else 1)
            )
            classified[category].append(expected_total)
            classified[recurrence].append(expected_total)
            line = lines.get(identifier)
            if line is None or (
                line.category,
                line.recurrence,
                line.quantity,
                line.unit_price,
                line.total,
                line.price_id,
                line.evidence_ids,
            ) != (
                category,
                recurrence,
                quantity,
                price,
                expected_total,
                price_id,
                ["input:scenario", "input:options", price_evidence],
            ):
                errors.append(
                    key
                    + ": Kostenzeile "
                    + identifier
                    + " widerspricht Mengen, Katalog oder Abrechnungsperiode."
                )
        totals = {
            category: None
            if any(number is None for number in amounts)
            else sum((number for number in amounts if number is not None), D(0))
            for category, amounts in classified.items()
        }
        complete = totals["CAPEX"] is not None and totals["OPEX"] is not None
        capex, opex = totals["CAPEX"], totals["OPEX"]
        tco = capex + opex if capex is not None and opex is not None else None
        monthly = (
            totals["MONTHLY"] / options.horizon_months if totals["MONTHLY"] is not None else None
        )
        if (
            candidate.costs.complete,
            candidate.costs.capex_total,
            candidate.costs.opex_total,
            candidate.costs.tco_total,
            candidate.costs.startup_total,
            candidate.costs.monthly_total,
            candidate.costs.currency,
        ) != (complete, capex, opex, tco, totals["ONCE"], monthly, "EUR"):
            errors.append(key + ": Kostensummen oder Vollständigkeit stimmen nicht überein.")

        states: dict[str, str] = {}

        def record(identifier: str, passed: bool | None, target: dict[str, str] = states) -> None:
            target[identifier] = "UNKNOWN" if passed is None else "PASS" if passed else "FAIL"

        valid_date = (
            date.fromisoformat(catalog["price_date"])
            <= options.valuation_date
            <= date.fromisoformat(catalog["valid_until"])
        )
        record("price_validity", True if valid_date else None)
        record("region", scenario.requirements.region == "EU")
        staff = scenario.company_profile.it_staff_fte
        record("staff", None if staff is None else staff >= D(plan["staff"]))
        for workload in scenario.workloads:
            prefix = workload.workload_key + ":"
            record(prefix + "function", workload.workload_type in plan["supported"])
            for field in ("user_count", "vcpu_count", "memory_gib", "storage_gib"):
                demand = getattr(workload, field)
                capacity = valid_price(plan.get("capacities", {}).get(field))
                record(
                    prefix + "capacity:" + field,
                    None if demand is None or capacity is None else demand <= capacity,
                )
            for field, capability, minimum in (
                ("max_latency_ms", "latency", False),
                ("availability_percent", "availability", True),
                ("rto_seconds", "rto", False),
                ("rpo_seconds", "rpo", False),
            ):
                target = getattr(workload, field)
                actual = D(plan[capability])
                record(
                    prefix + field,
                    None if target is None else actual >= target if minimum else actual <= target,
                )
            record(prefix + "internet", workload.internet_dependency_allowed)
            record(
                prefix + "sensitivity",
                None if workload.sensitivity is None else workload.sensitivity != "RESTRICTED",
            )
        profile = scenario.company_profile
        if scenario.requirements.hard_budget:
            record(
                "budget",
                None
                if not complete
                or profile.initial_budget is None
                or profile.monthly_budget is None
                or totals["ONCE"] is None
                or monthly is None
                else totals["ONCE"] <= profile.initial_budget and monthly <= profile.monthly_budget,
            )
        actual_states = {constraint.key: constraint.status for constraint in candidate.constraints}
        if actual_states != states or len(actual_states) != len(candidate.constraints):
            errors.append(key + ": Muss-Bedingungen fehlen oder wurden verändert.")
        if any(
            constraint.evidence_ids
            != ["input:scenario", "input:options", "catalog:" + key, "rules:scoring"]
            for constraint in candidate.constraints
        ):
            errors.append(key + ": Muss-Bedingungen besitzen falsche Evidenzreferenzen.")

        budget = (
            None
            if profile.initial_budget is None or profile.monthly_budget is None
            else profile.initial_budget + profile.monthly_budget * options.horizon_months
        )
        cost_score = (
            None
            if budget is None or tco is None
            else D(100)
            if budget == 0 and tco == 0
            else D(0)
            if budget == 0
            else max(D(0), D(100) - tco * D(50) / budget)
        )
        latency_values = [workload.max_latency_ms for workload in scenario.workloads]
        performance = (
            None
            if None in latency_values
            else sum(
                (
                    max(D(0), D(100) - D(plan["latency"]) * D(50) / value)
                    for value in latency_values
                    if value is not None
                ),
                D(0),
            )
            / len(latency_values)
        )
        recovery_values = [workload.rto_seconds for workload in scenario.workloads]
        resilience = (
            None
            if None in recovery_values
            else sum(
                (
                    max(D(0), D(100) - D(plan["rto"]) * D(50) / max(D(1), D(value)))
                    for value in recovery_values
                    if value is not None
                ),
                D(0),
            )
            / len(recovery_values)
        )
        operations = (
            None if staff is None else max(D(0), D(100) * (D(1) - D(plan["staff"]) / (staff + 1)))
        )
        criteria = dict(
            zip(
                GROUPS,
                (cost_score, performance, resilience, operations, D(plan["governance"])),
                strict=True,
            )
        )
        criteria = {
            group: None if value is None else cents(min(D(100), value))
            for group, value in criteria.items()
        }
        expected_criteria[key] = criteria
        if candidate.criterion_scores != criteria:
            errors.append(key + ": Kriterienwerte weichen von den Bewertungsankern ab.")
        status = (
            "EXCLUDED"
            if "FAIL" in states.values()
            else "INDETERMINATE"
            if not complete
            or "UNKNOWN" in states.values()
            or any(criteria[group] is None and weights[group] > 0 for group in weights)
            else "ELIGIBLE"
        )
        score = (
            cents(sum((weights[group] * (criteria[group] or D(0)) for group in weights), D(0)))
            if status == "ELIGIBLE"
            else None
        )
        expected_states[key], expected_scores[key] = status, score
        if (
            candidate.status != status
            or candidate.score != score
            or candidate.label != plan["label"]
        ):
            errors.append(key + ": Kandidatenstatus, Score oder Bezeichnung wurde verändert.")
        if candidate.evidence_ids != [
            "input:scenario",
            "input:options",
            "catalog:" + key,
            "rules:scoring",
        ]:
            errors.append(key + ": Kandidatenreferenzen widersprechen der Herkunft.")
        if {assignment.workload_key for assignment in candidate.assignments} != {
            workload.workload_key for workload in scenario.workloads
        } or len(candidate.assignments) != len(scenario.workloads):
            errors.append(key + ": Arbeitslastzuordnung unvollständig oder doppelt.")
        expected_components = [
            ("Primärbetrieb", plan["service"], plan["deployment"], plan["location"])
        ]
        if key == "HYBRID":
            expected_components.append(
                ("Asynchrone Cloud-Sicherung", "PAAS", "PUBLIC_CLOUD", "PROVIDER")
            )
        for assignment in candidate.assignments:
            if (
                (assignment.service_model, assignment.deployment_model, assignment.hosting_location)
                != (plan["service"], plan["deployment"], plan["location"])
                or [
                    (
                        component.role,
                        component.service_model,
                        component.deployment_model,
                        component.hosting_location,
                    )
                    for component in assignment.components
                ]
                != expected_components
                or assignment.evidence_ids != ["input:scenario", "catalog:" + key]
            ):
                errors.append(key + ": Architekturkomponenten oder ihre Herkunft wurden verändert.")

    ordered = sorted(
        (key for key in expected_states if expected_states[key] == "ELIGIBLE"),
        key=lambda key: (-(expected_scores[key] or D(0)), key),
    )
    valid_scores = {key: score for key, score in expected_scores.items() if score is not None}
    ranks = sorted(set(valid_scores.values()), reverse=True)
    for candidate in result.candidates:
        expected_rank = (
            ranks.index(valid_scores[candidate.key]) + 1 if candidate.key in ordered else None
        )
        if candidate.rank != expected_rank:
            errors.append(candidate.key + ": Rangfolge inkonsistent.")
    incomplete = "INDETERMINATE" in expected_states.values()
    winner = ordered[0] if ordered and not incomplete else None
    if result.recommended_candidate_key != winner:
        errors.append("Empfehlung stimmt nicht mit dem vollständigen Vergleich überein.")
    expected_status = (
        "INCOMPLETE" if incomplete else "VERIFIED" if ordered else "NO_FEASIBLE_OPTION"
    )
    if result.status != expected_status:
        errors.append("Gesamtstatus stimmt nicht mit der unabhängigen Prüfung überein.")
    expected_variations = []
    if ordered and not incomplete:
        for group in weights:
            for factor in (D("0.8"), D("1.2")):
                varied = {
                    key: weight * (factor if key == group else 1) for key, weight in weights.items()
                }
                denominator = sum(varied.values(), D(0))
                varied_order = sorted(
                    ordered,
                    key=lambda key: (
                        -cents(
                            sum(
                                (
                                    varied[dimension]
                                    * (expected_criteria[key][dimension] or D(0))
                                    / denominator
                                    for dimension in weights
                                ),
                                D(0),
                            )
                        ),
                        key,
                    ),
                )
                varied_winner = varied_order[0]
                expected_variations.append((group, factor, varied_winner, varied_winner != winner))
    actual_variations = [
        (variation.group, variation.factor, variation.winner_key, variation.changed)
        for variation in result.sensitivity.variations
    ]
    if (
        actual_variations != expected_variations
        or result.sensitivity.tested_variations != len(expected_variations)
        or result.sensitivity.winner_changes != sum(row[3] for row in expected_variations)
    ):
        errors.append("Sensitivitätsvarianten oder Wechselanzahl sind falsch.")
    gap = (
        cents(valid_scores[ordered[0]] - valid_scores[ordered[1]])
        if len(ordered) > 1 and not incomplete
        else None
    )
    if result.sensitivity.score_gap != gap:
        errors.append("Scoreabstand ist falsch.")
    return VerificationResult(valid=not errors, errors=errors, checks=CHECKS)
