from hypothesis import given
from hypothesis import strategies as st
from platform_app.decisions.demo import demo_scenario
from platform_app.decisions.engine import evaluate
from platform_app.decisions.schemas import AssessmentOptions, ScenarioInput


@given(st.integers(min_value=1, max_value=120))
def test_cost_monotonicity(horizon):
    s = ScenarioInput.model_validate(demo_scenario())
    a = evaluate(s, AssessmentOptions(horizon_months=horizon))
    b = evaluate(s, AssessmentOptions(horizon_months=min(120, horizon + 1)))
    assert all(
        y.costs.tco_total >= x.costs.tco_total
        for x, y in zip(a.candidates, b.candidates, strict=True)
    )
