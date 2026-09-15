"""Misst ausschließlich die deterministische Domäne; keine API-/DB-Latenzbehauptung."""

import json
import math
import platform
import statistics
from datetime import UTC, date, datetime
from pathlib import Path
from time import perf_counter

from platform_app.decisions import demo_scenario, evaluate
from platform_app.decisions.schemas import AssessmentOptions, ScenarioInput


def main():
    source = demo_scenario()
    source["workloads"] = [
        {**source["workloads"][0], "workload_key": f"workload-{i}", "name": f"Demo {i}"}
        for i in range(10)
    ]
    source["company_profile"]["it_staff_fte"] = "20"
    source["company_profile"]["monthly_budget"] = "150000"
    source["company_profile"]["initial_budget"] = "200000"
    scenario = ScenarioInput.model_validate(source)
    options = AssessmentOptions(valuation_date=date(2026, 9, 10))
    samples = []
    for index in range(105):
        start = perf_counter()
        result = evaluate(scenario, options)
        duration = (perf_counter() - start) * 1000
        assert result.verification.valid
        if index >= 5:
            samples.append(duration)
    samples.sort()
    report = {
        "measured_at": datetime.now(UTC).isoformat(),
        "scope": "Domäne inkl. unabhängigem Verifier; keine DB, HTTP oder parallelen Nutzer",
        "python": platform.python_version(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "workloads": 10,
        "candidates": 4,
        "samples": len(samples),
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(samples[math.ceil(len(samples) * 0.95) - 1], 3),
        "max_ms": round(max(samples), 3),
    }
    target = Path(__file__).resolve().parents[1] / ".local/decision-benchmark.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
