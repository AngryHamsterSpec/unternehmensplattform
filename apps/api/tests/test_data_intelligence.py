"""Fachliche Referenzwerte und Grenzen der M2-Analyse / unabhängigen Planung."""

import json
from decimal import Decimal
from uuid import UUID

import pytest
from platform_app.data.analytics import analyze, calendar_date, number
from platform_app.data.engine import DataError
from platform_app.data.intelligence_schemas import AnalysisInput, PlanSelection, QualityRule
from platform_app.data.plan_advisor import candidates, minimized_payload, verify_plan
from platform_app.data.postgres_source import source_for, sources
from platform_app.data.reports import analytical_html
from platform_app.data.stream_engine import build
from pydantic import ValidationError


def analysis(tmp_path, content, **options):
    raw = tmp_path / "input.csv"
    raw.write_bytes(content)
    normalized, _, profile, _ = build(raw, tmp_path, ";", False, [], lambda *_: None)
    result = analyze(
        normalized, tmp_path, profile, AnalysisInput(version_no=1, **options), lambda *_: None
    )
    return result, profile


def test_quartiles_distribution_outlier_correlations_and_exact_large_values(tmp_path):
    result, _ = analysis(tmp_path, b"X;Y;K\n1;2;3\n2;4;3\n3;6;3\n4;8;3\n100;200;3\n")
    n = result["numeric"][0]
    assert [Decimal(n[k]) for k in ("minimum", "q1", "median", "q3", "maximum", "mean")] == [
        1,
        2,
        3,
        4,
        100,
        22,
    ]
    assert n["outliers"] == 1 and sum(n["histogram"]) == 5
    assert result["correlations"][0]["pearson"] == "1"
    assert result["correlations"][1]["pearson"] is None
    assert result["numeric"][2]["histogram"] == [5] + [0] * 9
    assert Decimal(result["score"]) == 100
    folder = tmp_path / "large"
    folder.mkdir()
    a = 10**98
    result, _ = analysis(folder, f"X\n{a}\n{a + 2}\n".encode(), numeric_columns=["X"])
    assert Decimal(result["numeric"][0]["median"]) == a + 1
    assert Decimal(result["numeric"][0]["sample_stddev"]) > 1


def test_rules_dates_missing_invalid_and_pairwise_exclusion(tmp_path):
    rules = [
        QualityRule(column="X", operation="required"),
        QualityRule(column="X", operation="range", minimum="0", maximum="4"),
        QualityRule(column="Team", operation="unique"),
        QualityRule(column="Team", operation="allowed_values", values=["A"]),
    ]
    result, _ = analysis(
        tmp_path,
        b"X;Y;Datum;Team\n1;2;2026-01-31T23:30:00-02:00;A\n;4;2026-02-01;A\nfalsch;8;2026-02-31;B\n9;; ;C\n",
        numeric_columns=["X", "Y"],
        date_column="Datum",
        time_metric="X",
        rules=rules,
    )
    assert [r["failed"] for r in result["rules"]] == [1, 2, 2, 2]
    assert result["numeric"][0]["invalid"] == 1
    assert result["correlations"][0]["pairs"] == 1 and result["correlations"][0]["pearson"] is None
    time = result["time_series"]
    assert time["invalid_dates"] == time["missing_dates"] == time["invalid_or_missing_metrics"] == 1
    assert time["periods"] == [
        {"period": "2026-02", "rows": 2, "valid_values": 1, "sum": "1", "mean": "1"}
    ]
    assert result["rules"][1]["example_rows"] == [3, 4]


def test_empty_profile_and_schema_integrity(tmp_path):
    result, profile = analysis(tmp_path, b"A;B\n")
    assert result["score"] is None and result["numeric"] == []
    source = tmp_path / "bad"
    source.write_text('["A","C"]\n', encoding="utf8")
    target = tmp_path / "other"
    target.mkdir()
    with pytest.raises(DataError, match="Schema"):
        analyze(source, target, profile, AnalysisInput(version_no=1), lambda *_: None)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1e101", "1e-101", "1,2", " ", "9" * 101])
def test_invalid_decimal_is_explicit(value):
    assert number(value) is None


@pytest.mark.parametrize("value", ["2026-02-30", "2026-01-01T12:00:00", "morgen"])
def test_dates_require_valid_calendar_and_explicit_timezone(value):
    assert calendar_date(value) is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"operation": "range", "minimum": "NaN"},
        {"operation": "range", "minimum": "9", "maximum": "1"},
        {"operation": "required", "minimum": "1"},
        {"operation": "allowed_values", "values": []},
    ],
)
def test_rule_schema_rejects_ambiguous_arguments(kwargs):
    with pytest.raises(ValidationError):
        QualityRule(column="X", **kwargs)


def test_plan_evidence_minimization_verifier_and_report_escaping(tmp_path):
    result, profile = analysis(tmp_path, b'"<script>alert(1)</script>";X\n secret ;1\n secret ;1\n')
    choices = candidates(profile)
    payload = json.dumps(minimized_payload(profile, choices))
    assert "secret" not in payload and "script" not in payload
    assert {c["id"] for c in choices} == {"trim-0", "duplicates"}
    plan = verify_plan(profile, choices, PlanSelection(candidate_ids=["trim-0"]), "a" * 64, "rules")
    assert len(plan["steps"]) == 1 and len(plan["trace"]) == 7
    for ids in (["shell"], ["trim-0", "trim-0"]):
        with pytest.raises(DataError, match="Verifier"):
            verify_plan(profile, choices, PlanSelection(candidate_ids=ids), "a" * 64, "openai")
    result.update(dataset_id="demo", version_no=1, content_hash="a" * 64, original_hash="b" * 64)
    html = analytical_html(result, "demo", "c" * 64)
    assert "<script>" not in html and "&lt;script&gt;" in html and "Content-Security-Policy" in html


def test_registry_tenant_allowlist_tls_platform_deny_and_safe_errors(tmp_path, monkeypatch):
    org = UUID("10000000-0000-4000-8000-000000000001")
    config = {
        "id": "sales",
        "name": "Vertrieb",
        "organizations": [str(org)],
        "host": "db.example.test",
        "database": "source",
        "user": "reader",
        "password": "SYNTHETIC-DO-NOT-LOG",
        "tables": ["public.sales"],
    }
    registry = tmp_path / "registry.json"
    monkeypatch.setenv("DATA_SOURCES_FILE", str(registry))
    registry.write_text(json.dumps([config]), encoding="utf8")
    assert (
        sources(UUID(int=9)) == []
        and source_for(org, "sales", "public.sales").sslmode == "verify-full"
    )
    with pytest.raises(DataError):
        source_for(org, "sales", "public.secret")
    for changed in (
        {"sslmode": "disable"},
        {"database": "platform"},
        {"tables": ["public.sales; DROP"]},
    ):
        # Ein Semikolon innerhalb eines Namensteils ist ein erlaubter, gequoteter Bezeichner.
        if "tables" in changed:
            changed = {"tables": ["too.many.parts"]}
        registry.write_text(json.dumps([{**config, **changed}]), encoding="utf8")
        with pytest.raises(DataError) as failure:
            sources(org)
        assert "SYNTHETIC-DO-NOT-LOG" not in str(failure.value)


def test_source_lease_monitor_cancels_blocked_query():
    from threading import Event

    from platform_app.data.postgres_source import keep_lease

    cancelled = Event()

    class ConnectionDouble:
        def cancel_safe(self, *, timeout):
            assert timeout == 5
            cancelled.set()

    def revoked(*_):
        raise DataError("Synthetisch widerrufen")

    with pytest.raises(DataError, match="widerrufen"), keep_lease(ConnectionDouble(), revoked):
        assert cancelled.wait(5), "Blockierte Quellenabfrage wurde nicht abgebrochen"
