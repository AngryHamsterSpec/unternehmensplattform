from copy import deepcopy
from decimal import Decimal

import pytest
from platform_app.decisions.demo import demo_scenario
from platform_app.decisions.engine import evaluate
from platform_app.decisions.schemas import AssessmentOptions, ScenarioInput
from platform_app.decisions.verifier import verify
from pydantic import ValidationError


def test_complete_and_repeatable():
    s = ScenarioInput.model_validate(demo_scenario())
    a = evaluate(s, AssessmentOptions())
    assert a.status == "VERIFIED" and a.verification.valid
    assert a.model_dump() == evaluate(s, AssessmentOptions()).model_dump()
    assert len(a.candidates) == 4
    assert (
        next(c for c in a.candidates if c.key == "HYBRID")
        .assignments[0]
        .components[1]
        .hosting_location
        == "PROVIDER"
    )


def test_unknown_does_not_become_zero():
    d = demo_scenario()
    d["workloads"][0]["storage_gib"] = None
    a = evaluate(ScenarioInput.model_validate(d), AssessmentOptions())
    assert a.status == "INCOMPLETE"
    assert all(c.costs.tco_total is None for c in a.candidates)
    assert a.recommended_candidate_key is None


def test_hard_constraint_precedes_score():
    d = demo_scenario()
    d["workloads"][0]["internet_dependency_allowed"] = False
    a = evaluate(ScenarioInput.model_validate(d), AssessmentOptions())
    assert a.status == "NO_FEASIBLE_OPTION"
    assert all(c.rank is None for c in a.candidates)


def test_verifier_detects_manipulated_cost_and_rank():
    s = ScenarioInput.model_validate(demo_scenario())
    o = AssessmentOptions()
    a = evaluate(s, o)
    bad = deepcopy(a)
    bad.candidates[0].costs.tco_total += Decimal("1")
    assert not verify(s, o, bad).valid
    bad = deepcopy(a)
    bad.candidates[0].score = Decimal("99.99")
    assert not verify(s, o, bad).valid


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1"])
def test_invalid_numeric_input(value):
    d = demo_scenario()
    d["company_profile"]["monthly_budget"] = value
    with pytest.raises(ValidationError):
        ScenarioInput.model_validate(d)
