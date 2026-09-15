"""Eigenständige, datenarme Metadaten plus lesbarer, escapeter Analyseexport."""

import html
import json
from typing import Any


def analytical_html(
    result: dict[str, Any], task_id: str, result_hash: str, metadata: dict[str, str] | None = None
) -> str:
    def escape(value: Any) -> str:
        return html.escape(str(value if value is not None else "—"))

    def table(headers: list[str], rows: list[list[Any]]) -> str:
        return (
            "<table><thead><tr>"
            + "".join("<th>" + escape(h) + "</th>" for h in headers)
            + "</tr></thead><tbody>"
            + "".join(
                "<tr>" + "".join("<td>" + escape(v) + "</td>" for v in row) + "</tr>"
                for row in rows
            )
            + "</tbody></table>"
        )

    profile = result["profile"]
    content = "<h1>Datenanalyse</h1><p>IT-Kompass · " + escape(result["engine_version"]) + "</p>"
    content += table(
        ["Nachweis", "Wert"],
        [
            ["Datensatz", result["dataset_id"]],
            ["Version", result["version_no"]],
            ["Quellhash", result["content_hash"]],
            ["Originalhash", result["original_hash"]],
            ["Auftrag", task_id],
            ["Ergebnishash", result_hash],
            ["Beauftragt von", (metadata or {}).get("created_by_user_id")],
            ["Beauftragt am", (metadata or {}).get("created_at")],
            ["Abgeschlossen am", (metadata or {}).get("finished_at")],
        ],
    )
    content += (
        "<h2>Analyseauftrag und Regelstand</h2><pre style='white-space:pre-wrap;overflow-wrap:anywhere'>"
        + escape(
            json.dumps(
                {
                    "options": result.get("options"),
                    "ruleset": result.get("ruleset"),
                    "database_source": profile.get("database_source"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        + "</pre>"
    )
    content += "<h2>Datenqualität</h2>" + table(
        ["Zeilen", "Spalten", "Fehlende Zellen", "Doppelte Zeilen", "Qualitätsscore / 100"],
        [
            [
                profile["rows"],
                len(profile["columns"]),
                profile["missing_cells"],
                profile["duplicate_rows"],
                result["score"],
            ]
        ],
    )
    content += "<p>" + escape(result["score_method"]) + "</p><h2>Schema und Kategorien</h2>"
    content += table(
        ["Spalte", "Typ", "Fehlend", "Verschiedene Werte", "Häufigste Werte (Anzahl)"],
        [
            [
                c["name"],
                c["inferred_type"],
                c["missing"],
                c["distinct"],
                "; ".join(str(v["value"]) + " (" + str(v["count"]) + ")" for v in c["top_values"]),
            ]
            for c in profile["columns"]
        ],
    )
    content += "<h2>Statistik</h2>" + table(
        [
            "Spalte",
            "Gültig",
            "Ungültig",
            "Minimum",
            "Q1",
            "Median",
            "Q3",
            "Maximum",
            "Mittelwert",
            "Stichproben-Standardabweichung",
            "IQR-Ausreißer",
        ],
        [
            [
                n[k]
                for k in (
                    "column",
                    "count",
                    "invalid",
                    "minimum",
                    "q1",
                    "median",
                    "q3",
                    "maximum",
                    "mean",
                    "sample_stddev",
                    "outliers",
                )
            ]
            for n in result["numeric"]
        ],
    )
    content += "<h2>Korrelationen</h2>" + table(
        ["X", "Y", "Gültige Paare", "Pearson"],
        [[p["x"], p["y"], p["pairs"], p["pearson"]] for p in result["correlations"]],
    )
    content += "<h2>Histogramme</h2>" + table(
        ["Spalte", "Klassenhäufigkeiten (1–10)"],
        [[n["column"], ", ".join(map(str, n["histogram"]))] for n in result["numeric"]],
    )
    content += "<h2>Qualitätsregeln</h2>" + table(
        ["Spalte", "Regel", "Geprüft", "Fehler", "Beispielzeilen"],
        [
            [
                r["rule"]["column"],
                r["rule"]["operation"],
                r["checked"],
                r["failed"],
                ", ".join(map(str, r["example_rows"])),
            ]
            for r in result["rules"]
        ],
    )
    times = result["time_series"]
    content += (
        "<h2>Zeitreihe</h2><p>"
        + escape(times["column"])
        + " · "
        + escape(times["grain"])
        + " · Perioden insgesamt: "
        + escape(times["total_periods"])
        + "</p>"
    )
    content += table(
        ["Periode", "Zeilen", "Gültige Messwerte", "Summe", "Mittelwert"],
        [
            [p[k] for k in ("period", "rows", "valid_values", "sum", "mean")]
            for p in times["periods"]
        ],
    )
    content += (
        "<h2>Methodik und Grenzen</h2><ul>"
        + "".join("<li>" + escape(note) + "</li>" for note in result["notes"])
        + "</ul>"
    )
    return (
        '<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>IT-Kompass · Datenanalyse</title><style>body{font:14px system-ui;color:#202e2b;background:#f4f3ef;margin:3rem;line-height:1.5}h1,h2{color:#246655}table{border-collapse:collapse;width:100%;background:white;margin:1rem 0;font-variant-numeric:tabular-nums}td,th{border:1px solid #dce0d9;text-align:left;padding:.5rem;overflow-wrap:anywhere}th{background:#eaf2ed}td{max-width:32rem}li{margin:.5rem 0}@media print{body{margin:0;background:white}thead{display:table-header-group}tr{break-inside:avoid}}</style><main>'
        + content
        + "</main></html>"
    )
