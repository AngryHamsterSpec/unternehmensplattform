from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest
from platform_app.decisions import demo_scenario, evaluate
from platform_app.decisions.schemas import AssessmentOptions, ScenarioInput
from platform_app.decisions.verifier import verify


@pytest.mark.parametrize("field", ["user_count", "vcpu_count", "memory_gib", "storage_gib"])
def test_each_capacity_is_a_hard_constraint(field):
    raw = demo_scenario()
    raw["workloads"][0][field] = 100000
    result = evaluate(ScenarioInput.model_validate(raw), AssessmentOptions())
    assert result.status == "NO_FEASIBLE_OPTION"
    assert result.recommended_candidate_key is None
    assert result.verification.valid


@pytest.mark.parametrize(
    "part", ["catalog", "components", "status", "sensitivity", "weights", "rank"]
)
def test_verifier_rejects_forged_provenance_and_results(part):
    scenario = ScenarioInput.model_validate(demo_scenario())
    options = AssessmentOptions()
    result = deepcopy(evaluate(scenario, options))
    if part == "catalog":
        evidence = next(e for e in result.evidence if e.id == "catalog:SAAS")
        evidence.value["setup"] = "0"
    elif part == "components":
        next(c for c in result.candidates if c.key == "HYBRID").assignments[0].components.clear()
    elif part == "status":
        result.status = "INCOMPLETE"
    elif part == "sensitivity":
        result.sensitivity.winner_changes += 1
    elif part == "weights":
        result.weights["cost"] += Decimal("0.1")
    else:
        result.candidates[0].rank = 19
    assert not verify(scenario, options, result).valid


def test_expired_price_catalog_cannot_produce_recommendation():
    result = evaluate(
        ScenarioInput.model_validate(demo_scenario()),
        AssessmentOptions(valuation_date=date(2028, 1, 1)),
    )
    assert result.recommended_candidate_key is None
    assert result.status != "VERIFIED"
    assert result.verification.valid


def test_missing_memory_is_unknown_not_free():
    raw = demo_scenario()
    raw["workloads"][0]["memory_gib"] = None
    result = evaluate(ScenarioInput.model_validate(raw), AssessmentOptions())
    assert result.status == "INCOMPLETE"
    assert result.recommended_candidate_key is None
    assert all(c.costs.tco_total is None for c in result.candidates)


@pytest.mark.parametrize("field", ["monthly_unit", "setup"])
def test_missing_plan_price_blocks_complete_comparison(field, monkeypatch):
    from platform_app.decisions import engine, verifier
    from platform_app.decisions.catalog import load_catalog

    catalog = load_catalog()
    catalog["plans"][0][field] = None
    monkeypatch.setattr(engine, "load_catalog", lambda: deepcopy(catalog))
    monkeypatch.setattr(verifier, "load_catalog", lambda: deepcopy(catalog))
    result = evaluate(
        ScenarioInput.model_validate(demo_scenario()),
        AssessmentOptions(valuation_date=date(2026, 9, 10)),
    )
    assert result.status == "INCOMPLETE"
    assert result.recommended_candidate_key is None
    assert result.verification.valid
    assert result.candidates[0].costs.tco_total is None
    assert any(candidate.status == "ELIGIBLE" for candidate in result.candidates[1:])
    assert result.sensitivity.tested_variations == 0


@pytest.mark.parametrize("value", [None, "NaN", "Infinity", "-0.1", "nicht vorhanden"])
def test_invalid_shared_price_is_unknown(value, monkeypatch):
    from platform_app.decisions import engine, verifier
    from platform_app.decisions.catalog import load_catalog

    catalog = load_catalog()
    catalog["storage_monthly_unit"] = value
    monkeypatch.setattr(engine, "load_catalog", lambda: deepcopy(catalog))
    monkeypatch.setattr(verifier, "load_catalog", lambda: deepcopy(catalog))
    result = evaluate(
        ScenarioInput.model_validate(demo_scenario()),
        AssessmentOptions(valuation_date=date(2026, 9, 10)),
    )
    assert result.verification.valid
    assert result.status == "INCOMPLETE"
    assert all(candidate.costs.tco_total is None for candidate in result.candidates)


def test_golden_demo_tco():
    result = evaluate(
        ScenarioInput.model_validate(demo_scenario()),
        AssessmentOptions(valuation_date=date(2026, 9, 10)),
    )
    expected = {"SAAS": "44708", "PAAS": "89568", "IAAS": "158448", "HYBRID": "235848"}
    for candidate in result.candidates:
        assert candidate.costs.tco_total == Decimal(expected[candidate.key])
        assert candidate.costs.tco_total == candidate.costs.capex_total + candidate.costs.opex_total
        assert (
            candidate.costs.tco_total
            == candidate.costs.startup_total + 36 * candidate.costs.monthly_total
        )


@pytest.mark.parametrize("horizon", [1, 7, 36, 120])
def test_fractional_quantity_rounds_each_billing_period(horizon):
    raw = demo_scenario()
    raw["workloads"][0]["storage_gib"] = "1.333333"
    result = evaluate(
        ScenarioInput.model_validate(raw),
        AssessmentOptions(horizon_months=horizon, valuation_date=date(2026, 9, 10)),
    )
    assert result.verification.valid
    for candidate in result.candidates:
        storage = next(line for line in candidate.costs.lines if line.id.endswith(":storage"))
        assert storage.total == Decimal("0.27") * horizon
        assert (
            candidate.costs.tco_total
            == candidate.costs.startup_total + horizon * candidate.costs.monthly_total
        )


@pytest.mark.parametrize(
    "values",
    [
        {"cost": "1", "performance": "1", "resilience": "1", "operations": "0", "governance": "0"},
        {"cost": "0", "performance": "1", "resilience": "0", "operations": "0", "governance": "0"},
        {
            "cost": "7",
            "performance": "11",
            "resilience": "13",
            "operations": "17",
            "governance": "19",
        },
    ],
)
def test_custom_weight_normalization_preserves_decimal_precision(values):
    from platform_app.decisions.schemas import AssessmentResult

    result = evaluate(
        ScenarioInput.model_validate(demo_scenario()),
        AssessmentOptions(
            weight_profile="CUSTOM", custom_weights=values, valuation_date=date(2026, 9, 10)
        ),
    )
    assert result.status == "VERIFIED", result.verification.errors
    assert AssessmentResult.model_validate_json(result.model_dump_json()) == result
    assert result.sensitivity.tested_variations == 10
    assert all(
        Decimal(0) <= candidate.score <= Decimal(100)
        for candidate in result.candidates
        if candidate.score is not None
    )


def test_zero_budget_is_known_while_missing_budget_is_unknown():
    raw = demo_scenario()
    raw["company_profile"].update(initial_budget="0", monthly_budget="0")
    options = AssessmentOptions(valuation_date=date(2026, 9, 10))
    result = evaluate(ScenarioInput.model_validate(raw), options)
    assert result.status == "VERIFIED"
    assert all(candidate.criterion_scores["cost"] == 0 for candidate in result.candidates)
    raw["company_profile"]["initial_budget"] = None
    assert evaluate(ScenarioInput.model_validate(raw), options).status == "INCOMPLETE"


def test_verifier_is_independent_of_cost_and_score_implementation(monkeypatch):
    from platform_app.decisions import engine

    original = engine.criterion_values

    def wrong_scores(*args, **kwargs):
        scores = original(*args, **kwargs)
        scores["governance"] = Decimal("100")
        return scores

    monkeypatch.setattr(engine, "criterion_values", wrong_scores)
    result = evaluate(
        ScenarioInput.model_validate(demo_scenario()),
        AssessmentOptions(valuation_date=date(2026, 9, 10)),
    )
    assert result.status == "VERIFICATION_FAILED"
    assert not result.verification.valid
    assert result.recommended_candidate_key is None


def test_scenario_and_options_are_unchanged_by_evaluation():
    scenario = ScenarioInput.model_validate(demo_scenario())
    options = AssessmentOptions(valuation_date=date(2026, 9, 10))
    original = (scenario.model_dump_json(), options.model_dump_json())
    first = evaluate(scenario, options)
    assert original == (scenario.model_dump_json(), options.model_dump_json())
    assert first == evaluate(scenario, options)


@pytest.mark.parametrize(
    "part",
    [
        "duplicate_evidence",
        "assignment_reference",
        "price_reference",
        "missing_constraint",
        "score_gap",
        "variant_winner",
    ],
)
def test_additional_verifier_integrity_boundaries(part):
    scenario = ScenarioInput.model_validate(demo_scenario())
    options = AssessmentOptions(valuation_date=date(2026, 9, 10))
    result = evaluate(scenario, options)
    if part == "duplicate_evidence":
        result.evidence.append(deepcopy(result.evidence[0]))
    elif part == "assignment_reference":
        result.candidates[0].assignments[0].evidence_ids = ["catalog:IAAS"]
    elif part == "price_reference":
        result.candidates[0].costs.lines[0].price_id = "erfundener-preis"
    elif part == "missing_constraint":
        result.candidates[0].constraints.pop()
    elif part == "score_gap":
        result.sensitivity.score_gap = Decimal("99.99")
    else:
        result.sensitivity.variations[0].winner_key = None
    assert not verify(scenario, options, result).valid
