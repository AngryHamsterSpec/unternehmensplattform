"""Deterministische Vollanalysen; begrenzter RAM, exakte Dezimalsortierung auf Platte."""

import re
import sqlite3
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from itertools import combinations
from pathlib import Path
from typing import Any

from platform_app.data.engine import DataError
from platform_app.data.intelligence_schemas import AnalysisInput, QualityRule
from platform_app.data.schemas import DataProfile
from platform_app.data.stream_engine import encode_row, source_rows

DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,3})?\Z")


def number(value: str) -> Decimal | None:
    value = value.strip()
    if len(value) > 100 or not DECIMAL.fullmatch(value):
        return None
    try:
        result = Decimal(value)
        return result if result.is_finite() and abs(result.adjusted()) <= 100 else None
    except InvalidOperation:
        return None


def calendar_date(value: str) -> date | None:
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return instant.astimezone(UTC).date() if instant.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def rule_valid(rule: QualityRule, value: str) -> bool:
    if rule.operation == "required":
        return bool(value.strip())
    if not value.strip():
        return True  # Pflichtwert separat prüfen; leere Werte zählen nicht als geprüft.
    if rule.operation == "decimal":
        return number(value) is not None
    if rule.operation == "date":
        return calendar_date(value) is not None
    if rule.operation == "boolean":
        return value.casefold() in {"true", "false"}
    if rule.operation == "allowed_values":
        return value in rule.values
    if rule.operation == "range":
        n = number(value)
        return (
            n is not None
            and (rule.minimum is None or n >= Decimal(rule.minimum))
            and (rule.maximum is None or n <= Decimal(rule.maximum))
        )
    return True


def display(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(+value)


def analyze(
    source: Path,
    directory: Path,
    profile: DataProfile,
    options: AnalysisInput,
    heartbeat: Callable[[int, str], None],
) -> dict[str, Any]:
    columns = [c.name for c in profile.columns]
    chosen = (
        options.numeric_columns
        or [c.name for c in profile.columns if c.inferred_type == "decimal"][:8]
    )
    names = (
        chosen
        + [r.column for r in options.rules]
        + [n for n in (options.date_column, options.time_metric) if n]
    )
    if any(n not in columns for n in names):
        raise DataError("Eine ausgewählte Spalte fehlt in dieser Datenversion.")
    indices = [columns.index(n) for n in chosen]
    rule_indices = [columns.index(r.column) for r in options.rules]
    date_index = columns.index(options.date_column) if options.date_column else None
    metric_index = columns.index(options.time_metric) if options.time_metric else None
    db = sqlite3.connect(directory / "statistics.sqlite")
    cancelled: Exception | None = None

    def progress() -> int:
        nonlocal cancelled
        try:
            heartbeat(0, "Analyse wird berechnet")
            return 0
        except Exception as error:
            cancelled = error
            return 1

    try:
        db.execute("PRAGMA cache_size=-8192")
        db.execute("PRAGMA temp_store=FILE")
        db.execute("PRAGMA journal_mode=OFF")
        db.execute("PRAGMA max_page_count=2097152")  # 8 GiB bei 4-KiB-Seiten.
        db.create_collation(
            "DECIMAL", lambda a, b: (Decimal(a) > Decimal(b)) - (Decimal(a) < Decimal(b))
        )
        db.set_progress_handler(progress, 10000)
        db.execute("CREATE TABLE numeric_values(col INTEGER, value TEXT COLLATE DECIMAL)")
        db.execute("CREATE TABLE unique_values(rule INTEGER, value TEXT)")
        db.execute("CREATE TABLE timeline(bucket TEXT, value TEXT)")
        moments: list[list[Any]] = [[0, Decimal(0), Decimal(0), 0, 0] for _ in chosen]
        pairs: dict[tuple[int, int], list[Any]] = {
            pair: [0, Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
            for pair in combinations(range(len(chosen)), 2)
        }
        rules: list[dict[str, Any]] = [
            {"rule": r.model_dump(), "checked": 0, "failed": 0, "example_rows": []}
            for r in options.rules
        ]
        time_invalid = time_missing = metric_invalid = total = 0
        reader = source_rows(source, ";", True)
        if next(reader, []) != columns:
            reader.close()
            raise DataError("Analysequelle und gespeichertes Schema widersprechen sich.")
        with localcontext() as context:
            context.prec = (
                450  # Zulässige Exponenten ±100, Kovarianz und starke Größenunterschiede.
            )
            try:
                for total, row in enumerate(reader, 1):
                    if len(row) != len(columns):
                        raise DataError(
                            "Die gespeicherte Datenversion hat eine ungültige Zeilenstruktur."
                        )
                    encode_row(row)
                    values = [number(row[i]) for i in indices]
                    for i, numeric in enumerate(values):
                        m = moments[i]
                        if not row[indices[i]].strip():
                            m[3] += 1
                        elif numeric is None:
                            m[4] += 1
                        else:
                            m[0] += 1
                            delta = numeric - m[1]
                            m[1] += delta / m[0]
                            m[2] += delta * (numeric - m[1])
                            db.execute("INSERT INTO numeric_values VALUES (?,?)", (i, str(numeric)))
                    for (i, j), m in pairs.items():
                        x, y = values[i], values[j]
                        if x is not None and y is not None:
                            m[0] += 1
                            dx, dy = x - m[1], y - m[2]
                            m[1] += dx / m[0]
                            m[2] += dy / m[0]
                            m[3] += dx * (x - m[1])
                            m[4] += dy * (y - m[2])
                            m[5] += dx * (y - m[2])
                    for i, rule in enumerate(options.rules):
                        value = row[rule_indices[i]]
                        if rule.operation != "required" and not value.strip():
                            continue
                        rules[i]["checked"] += 1
                        if rule.operation == "unique":
                            db.execute("INSERT INTO unique_values VALUES (?,?)", (i, value))
                        elif not rule_valid(rule, value):
                            rules[i]["failed"] += 1
                            if len(rules[i]["example_rows"]) < 10:
                                rules[i]["example_rows"].append(total)
                    if date_index is not None:
                        value = row[date_index]
                        stamp = calendar_date(value)
                        if not value.strip():
                            time_missing += 1
                        elif stamp is None:
                            time_invalid += 1
                        else:
                            metric = number(row[metric_index]) if metric_index is not None else None
                            if metric_index is not None and metric is None:
                                metric_invalid += 1
                            bucket = (
                                stamp.isoformat()[:7]
                                if options.time_grain == "month"
                                else stamp.isoformat()
                            )
                            db.execute(
                                "INSERT INTO timeline VALUES (?,?)",
                                (bucket, str(metric) if metric is not None else None),
                            )
                    if total % 1000 == 0:
                        db.commit()
                        heartbeat(
                            15 + int(40 * total / max(1, profile.rows)),
                            "Zeilen und Qualitätsregeln werden geprüft",
                        )
                        if (directory / "statistics.sqlite").stat().st_size > 8 * 1024**3:
                            raise DataError(
                                "Die Analyse überschreitet 8 GiB temporäre Statistikdaten. Weniger Spalten oder Regeln wählen."
                            )
            finally:
                reader.close()
            if total != profile.rows:
                raise DataError(
                    "Die gespeicherte Zeilenanzahl stimmt nicht mit der Analysequelle überein."
                )
            db.commit()
            heartbeat(60, "Quantile und Verteilungen werden berechnet")
            db.execute("CREATE INDEX numeric_order ON numeric_values(col,value COLLATE DECIMAL)")
            statistics = []
            for i, name in enumerate(chosen):
                n, mean, m2, missing, invalid = moments[i]
                n = int(n)

                def quantile(p: Decimal, n: int = n, i: int = i) -> Decimal | None:
                    if not n:
                        return None
                    pos = Decimal(n - 1) * p
                    low = int(pos)
                    rows = db.execute(
                        "SELECT value FROM numeric_values WHERE col=? ORDER BY value COLLATE DECIMAL LIMIT 2 OFFSET ?",
                        (i, low),
                    ).fetchall()
                    a = Decimal(rows[0][0])
                    return a + (Decimal(rows[-1][0]) - a) * (pos - low)

                minimum, q1, median, q3, maximum = [
                    quantile(Decimal(p)) for p in ("0", ".25", ".5", ".75", "1")
                ]
                outliers = 0
                bins = [0] * 10
                if (
                    minimum is not None
                    and maximum is not None
                    and q1 is not None
                    and q3 is not None
                ):
                    low, high = q1 - Decimal("1.5") * (q3 - q1), q3 + Decimal("1.5") * (q3 - q1)
                    for k, (raw,) in enumerate(
                        db.execute("SELECT value FROM numeric_values WHERE col=?", (i,)), 1
                    ):
                        v = Decimal(raw)
                        outliers += int(v < low or v > high)
                        if maximum > minimum:
                            bins[min(9, int((v - minimum) * 10 / (maximum - minimum)))] += 1
                        if k % 1000 == 0:
                            heartbeat(70, "Ausreißer und Histogramme werden geprüft")
                    if maximum == minimum:
                        bins[0] = n
                statistics.append(
                    {
                        "column": name,
                        "count": n,
                        "missing": int(missing),
                        "invalid": int(invalid),
                        "mean": display(mean) if n else None,
                        "minimum": display(minimum),
                        "q1": display(q1),
                        "median": display(median),
                        "q3": display(q3),
                        "maximum": display(maximum),
                        "sample_stddev": display((max(Decimal(0), m2) / (n - 1)).sqrt())
                        if n > 1
                        else None,
                        "outliers": outliers,
                        "histogram": bins,
                    }
                )
            correlations = []
            for (i, j), (n, _mx, _my, xx, yy, xy) in pairs.items():
                correlation = (
                    max(Decimal(-1), min(Decimal(1), xy / (xx * yy).sqrt()))
                    if n >= 2 and xx > 0 and yy > 0
                    else None
                )
                correlations.append(
                    {
                        "x": chosen[i],
                        "y": chosen[j],
                        "pairs": int(n),
                        "pearson": display(correlation),
                    }
                )
            for i, rule in enumerate(options.rules):
                if rule.operation == "unique":
                    rules[i]["failed"] = db.execute(
                        "SELECT coalesce(sum(n),0) FROM (SELECT count(*) n FROM unique_values WHERE rule=? GROUP BY value HAVING count(*)>1)",
                        (i,),
                    ).fetchone()[0]
            heartbeat(85, "Zeitreihe und Analysebericht werden erstellt")
            periods: list[dict[str, Any]] = []
            total_periods = 0
            last_bucket = None
            current_count = valid_count = 0
            total_value = Decimal(0)

            def finish_bucket() -> None:
                nonlocal total_periods
                if last_bucket is not None:
                    total_periods += 1
                    if len(periods) < 1000:
                        periods.append(
                            {
                                "period": last_bucket,
                                "rows": current_count,
                                "valid_values": valid_count,
                                "sum": display(total_value) if valid_count else None,
                                "mean": display(total_value / valid_count) if valid_count else None,
                            }
                        )

            for k, (bucket, raw) in enumerate(
                db.execute("SELECT bucket,value FROM timeline ORDER BY bucket"), 1
            ):
                if bucket != last_bucket:
                    finish_bucket()
                    last_bucket, current_count, valid_count, total_value = bucket, 0, 0, Decimal(0)
                current_count += 1
                if raw is not None:
                    valid_count += 1
                    total_value += Decimal(raw)
                if k % 1000 == 0:
                    heartbeat(85, "Zeitperioden werden aggregiert")
            finish_bucket()
            checked = sum(r["checked"] for r in rules)
            failed = sum(r["failed"] for r in rules)
            components = (
                [
                    Decimal(100)
                    * (total * len(columns) - profile.missing_cells)
                    / (total * len(columns)),
                    Decimal(100) * (total - profile.duplicate_rows) / total,
                ]
                if total
                else []
            )
            if checked:
                components.append(Decimal(100) * (checked - failed) / checked)
            return {
                "engine_version": "data-analysis-1",
                "profile": profile.model_dump(mode="json"),
                "options": options.model_dump(mode="json"),
                "numeric": statistics,
                "correlations": correlations,
                "rules": rules,
                "score": display(sum(components, Decimal(0)) / len(components))
                if components
                else None,
                "score_method": "Gleichgewichtetes Mittel aus Vollständigkeit, Eindeutigkeit ganzer Zeilen und (falls geprüft) Regelkonformität. Leere Daten erhalten keinen Score.",
                "time_series": {
                    "column": options.date_column,
                    "metric": options.time_metric,
                    "grain": options.time_grain,
                    "invalid_dates": time_invalid,
                    "missing_dates": time_missing,
                    "invalid_or_missing_metrics": metric_invalid,
                    "total_periods": total_periods,
                    "periods": periods,
                },
                "notes": [
                    "Alle Zeilen geprüft. Vertiefte Statistik für höchstens acht gewählte numerische Spalten; ohne Auswahl die ersten acht als numerisch erkannten Spalten.",
                    "Quantile: lineare Interpolation (R7); Ausreißer: 1,5 × IQR, nur Hinweise. Histogramm: zehn gleich breite Klassen, rechte Grenze nur in letzter Klasse eingeschlossen; konstante Werte in erster Klasse.",
                    "Pearson verwendet paarweise gültige Dezimalwerte; fehlende/ungültige Paare werden ausgeschlossen. Keine Kausalitätsaussage; konstante Spalten liefern keinen Koeffizienten.",
                    "Zeitstempel benötigen einen expliziten Offset und werden auf UTC-Tage abgebildet; reine ISO-Daten bleiben Kalendertage. Keine Interpolation fehlender Perioden; maximal erste 1.000 Perioden im Bericht.",
                    "Typ-/Bereichsregeln überspringen Leerwerte; Pflichtwertregeln prüfen sie ausdrücklich. Eindeutigkeit zählt alle Zeilen mit mehrfach vorkommendem nichtleerem Originalwert.",
                ],
            }
    except sqlite3.Error:
        if cancelled:
            raise cancelled from None
        raise DataError(
            "Die Statistik konnte innerhalb der verfügbaren Ressourcen nicht berechnet werden."
        ) from None
    finally:
        db.close()
