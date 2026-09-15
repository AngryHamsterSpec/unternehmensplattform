# Prüfungen des CSV-Ablaufs

Die vorhandenen test_data_engine.py und test_data_integration.py sichern alte Versionen, CSV-Randfälle, Formelschutz, Freigaben, RLS, Rollback und Idempotenz.

test_stream_engine.py prüft größere Zeilen-/Spalten-/Zellenzahlen, exakte Dezimalaggregate, Reihenfolge mehrerer Transformationen, eingebettete Zeilenumbrüche, BOM, JSONL-Roundtrip sowie Parsergrenzen. test_large_data_integration.py nutzt echte PostgreSQL-Rollen: Mehrabschnitt-Upload mit 400.000 Zeilen, Wiederholung, Originaldownload, Vorschau, Bestätigung, Export, späte Seitennavigation, fremder Mandant, CSRF, Größenüberschreitung, Abbruch und abgelaufene Worker-Lease.

Die Browserprüfung meldet sich wirklich an Keycloak an. Sie umfasst den bestehenden kleinen Versionsablauf und einen Dateiimport über der im Nutzerbild gezeigten Größe von 2.088.432 Bytes.

## Ausführen

```sh
docker compose stop data-worker
docker compose --profile test run --build --rm tests
docker compose up -d --no-deps data-worker
docker compose --profile test run --rm tests python -m mypy --config-file /app/pyproject.toml --cache-dir /tmp/mypy /app/src/platform_app
docker build -f infra/proxy/Dockerfile --target test -t unternehmensplattform-web-tests:0.1.0 .
python scripts/run_e2e.py --isolated
python scripts/benchmark_large_csv.py
python scripts/check_runtime.py
python scripts/check_restore.py --full-stack --isolated-browser
python scripts/check_security.py
```

Der 1-GiB-Test erzeugt die Datei mit begrenztem Speicher, überträgt exakt 1.073.741.824 Bytes durch Nginx und HTTP, wartet auf den echten Worker und prüft Zeilenzahl, Mittelwert, letzte Datenansicht sowie vollständige Original- und Exportdownloads gegen SHA-256. Seine reguläre DB-Session ist eine synthetische Testfixture; der echte OIDC-Login wird separat im Browser nachgewiesen.

Während DB-Tests bleibt der reguläre Worker angehalten, damit er absichtlich unterbrochene Testaufträge nicht übernimmt. Bei Fehlern ebenfalls wieder starten. Windows-Unitprüfungen verwenden ein neues projektlokales temporäres Verzeichnis; der Linux-Testcontainer ist die verbindliche DB-/Typprüfumgebung.

Tatsächliche Ergebnisse: [1-GiB-Prüfbericht](../../../../../docs/testing/M2_LARGE_CSV_REPORT.md). Der [erste CSV-Bericht](../../../../../docs/testing/M2_CSV_REPORT.md) bleibt als historischer Nachweis erhalten.


## Gezielte Visualisierungsprüfung

test_visualization_integration.py prüft begrenzte Auswahl, Hash/Originalpositionen, alte Inline- und neue Abschnittsversionen, Spaltenvalidierung, Viewer, Fremdmandant, Textkürzung und einen konkurrierenden Veröffentlichungsversuch während des Detailabrufs.

Frontend: chartModel.test.ts prüft Histogramme, fehlende Zahlen, sichere Darstellungsgrenzen, Ringanteile und Filter. Der bestehende CSV-Browserablauf prüft zusätzlich alle Diagrammtypen, PNG-Signatur, SVG-Inhalt, Moduswechsel, Filter, mobile Breite und bestehende Versionierung/Exporte. Gezielt ausführbar mit scripts/run_e2e.py --isolated --grep CSV-Import.

Ergebnisse werden im Visualisierungsbericht dokumentiert; nicht ausgeführte Prüfungen gelten nicht als bestanden.

## CSV-Reparatur

test_csv_import_options.py prüft Formate, Kodierungen und lange Zellen; test_import_retry_integration.py prüft Wiederaufnahme bis bestätigter Transformation und Export sowie Rollen, CSRF und RLS. [Aktueller Nachweis](../../../../../docs/testing/M2_CSV_RECOVERY_REPORT.md).

## JSON-Nachweis

test_json_format.py prüft den begrenzten Reader und die gemeinsame Transformation. test_json_integration.py prüft JSON und JSONL bis zur bestätigten Version in PostgreSQL. Der gezielte Browserfall CSV-Formaterkennung enthält zusätzlich einen JSON-Import mit Vorschau und Bestätigung. [Ergebnisse und Grenzen](../../../../../docs/testing/M2_JSON_REPORT.md).

## XLSX-Nachweis

test_xlsx_format.py prüft synthetische Arbeitsmappen mit Blattwahl, Datums-/Boolwerten, Fehlzellen, falschen Dimensionen, Formeln, Excel-Fehlern, Vorschauen und Archiv-/XML-Angriffsmustern. test_xlsx_integration.py prüft echten Upload, Profil, Mandantenisolation, Originalbytes, Vorschau, bestätigte Version und Export. Der bestehende Browserfall zur Formatwiederaufnahme enthält zusätzlich JSON und XLSX mit Blatt 2.

Aktuelle Ergebnisse: [Produktdesign und XLSX](../../../../../docs/testing/M2_PRODUCT_XLSX_REPORT.md). Der historische 1-GiB-CSV-Nachweis ist keine Zusage, beliebige 1-GiB-XLSX-Arbeitsmappen innerhalb der separaten XML-/Metadatenlimits verarbeiten zu können.

## Parquet-Nachweis

test_parquet_format.py deckt fünf Kompressionsarten, präzise Dezimal-/Ganzzahlwerte, Schema-/Typfehler, geordnete Gruppen, leere Tabellen, Metadatenfehler, Abbruch und ausdrückliche Quellfreigabe ab. test_parquet_integration.py prüft Originalgleichheit, Mandantenisolation und den vollständigen Versionsworkflow gegen PostgreSQL. Ein eigener OIDC-Browserfall prüft dieselbe Nutzerstrecke.

scripts/check_parquet_resources.py ist ein begrenzter synthetischer Linux-Nachweis: 100.003 Zeilen, acht Spalten, 256-MiB-/1-CPU-Container. Kein allgemeiner Lasttest und keine Verallgemeinerung auf beliebige komprimierte Dateien. [Aktuelle Ergebnisse](../../../../../docs/testing/M2_PARQUET_REPORT.md).

## SQLite-Nachweis

test_sqlite_format.py prüft Wertepräzision, Tabellenwahl, zitierte Namen, Reihenfolge, leere Tabellen, Originalschutz, Formula-Injection im Export, berechnete/virtuelle Spalten, Views, Binär-/unendliche Werte, übergroße Datensätze, beschädigte/WAL-Dateien und Abbruch mit geschlossenem Reader. test_sqlite_integration.py führt den vollständigen Workflow einschließlich Fehlerkorrektur, RLS und Lesekonto gegen PostgreSQL aus. Der OIDC-Browserfall „SQLite-Snapshot“ verwendet ausschließlich die synthetische Fixture. [Tatsächliche Ergebnisse](../../../../../docs/testing/M2_SQLITE_REPORT.md).

## M2-Erweiterung vom 14.09.2026

`test_data_intelligence.py` prüft fachliche Referenzwerte, konstante/fehlende/ungültige Zahlen, große Dezimalwerte, Kalender-/Offsetsemantik, Regeln, Planminimierung, Verifier, HTML-Escaping, Quellenkonfiguration und Abbruch blockierter Abfragen. `test_intelligence_integration.py` verwendet echtes PostgreSQL für beide Speicherformate, Regelversionen, idempotente Aufgaben, RLS, unveränderliche Ergebnisse, Export, Vorschau/Freigabe, veraltete Pläne, Abbruch, Lease-Wiederanlauf, Rechteentzug und die echte synthetische Datenquelle. OpenAI wird ausschließlich als gekennzeichnetes Test-Double verwendet; Zustimmung, Budget, Datenminimierung, Ablehnung und Timeout werden geprüft.

Für gezielte Läufe zuerst `python scripts/setup_data_source_demo.py` ausführen und **beide** Worker stoppen: `docker compose stop data-worker intelligence-worker`. Danach `docker compose --profile test run --rm tests python -m pytest -q tests/test_data_intelligence.py tests/test_intelligence_integration.py` ausführen und beide Worker wieder starten. Aktuelle Images/Tests vor der Abnahme bauen; keine erfolgreichen Prüfungen gegen veraltete Images behaupten. Für normale Änderungen keine 1-GiB-Benchmarks wiederholen, sofern die Änderung keinen zusätzlichen Erkenntniswert erwarten lässt.

`e2e/m2-intelligence.spec.ts` beschreibt den durchgängigen OIDC-/PostgreSQL-/Regel-/Berichts-/Diagramm-/Plan-/Versionsablauf. `check_restore.py` erfasst auch `data_tasks` und `data_rule_sets`, pausiert beide Worker und prüft bei `--full-stack` gezielt die historische Wiederherstellung. Ausgeführte Ergebnisse und verbleibende Plattform-/Live-Grenzen: [M2-Abschlussbericht](../../../../../docs/testing/M2_COMPLETION_REPORT.md).
