# M2 — Parquet-Nachweis

Stand: 13.09.2026. Parquet-Adapter lokal IMPLEMENTIERT; M2 insgesamt weiterhin TEILWEISE IMPLEMENTIERT.

## Benutzbarer Ablauf

Parquet-Datei auswählen → abschnittsweise hochladen → Schema/Profil prüfen → Bereinigungsschritte hinzufügen → Vorschau berechnen → Version ausdrücklich bestätigen → CSV exportieren. Das ursprüngliche Parquet bleibt bytegleich herunterladbar. source_format=parquet bleibt in den Ableitungen erhalten. Keine zusätzlichen Agentenrechte oder Live-KI.

Polars 1.44.2 und Apache Thrift 0.24.0 passen zum bestehenden Alpine-System. [ADR 0012](../adr/0012-parquet-tabellenadapter.md) begründet Metadatenprüfung, synchrone Zeilengruppen und Grenzen. Die vorhandene deutsche Oberfläche und das gemeinsame Designsystem werden verwendet.

## Erfolgreich ausgeführte Prüfungen

| Prüfung | Tatsächliches Ergebnis |
| --- | --- |
| Parquet, CSV-Leseoptionen, JSON und XLSX | **62 Unitfälle bestanden**, 4,29 s; davon 22 Parquet-/Readerfälle |
| Echter PostgreSQL-Parquet-Ablauf | **1 bestanden**, 16,96 s; RLS, Originalgleichheit, Profil, Vorschau, Bestätigung, CSV-Export |
| mypy im Linux-Testimage | **50 Quelldateien**, keine Fehler |
| Ruff / Python-Formatierung, TypeScript/Vite, Prettier und ESLint | bestanden |
| Bestehende Frontend-Unitprüfungen | **14 bestanden**, 16,15 s |
| Eigener Chromium/OIDC-Parquet-Ablauf | **1 bestanden**, 8,0 s einschließlich Start |
| Quellscan Trivy 0.74.0 | Scannerfixture erkannt, keine Geheimnisse oder Paketbefunde im Quellscan |
| pip-audit der gesperrten Python-Laufzeitabhängigkeiten | keine bekannten Schwachstellen gemeldet |

Formatfälle: unkomprimiert, Snappy, Gzip, Zstd und LZ4; große Ganzzahlen und präzise Dezimalwerte; boolesche und Datum-/Zeitwerte; Nullzellen, leere Tabellen, mehrere Gruppen und geordnete Ausgabe. Negative Fälle: verschachtelte/binäre Daten, NaN/Infinity, Dateimarker, Footer, externe Referenzen, Verschlüsselung und inkonsistente Metadaten. Bei nachgelagertem Normalisierungsfehler wird der Quellgenerator ausdrücklich geschlossen.

## Begrenzter Ressourcennachweis

Ein separater Container ohne Netzwerk, mit schreibgeschütztem Root-Dateisystem, 256 MiB und einer CPU verarbeitete eine synthetische Zstd-Parquet-Datei:

- **100.003 Zeilen × 8 Spalten**, 922.641 Originalbytes.
- Erstellung, vollständiger Import, Profil und Export: **8,273 s**.
- Prozess-Spitzen-RSS: **101,32 MiB**; Containerlimit eingehalten.
- Zeilen-/Spaltenzahl und vollständiges Minimum/Maximum geprüft.

Skript: [check_parquet_resources.py](../../scripts/check_parquet_resources.py). Gemessen mit dem aktuellen Quellstand als schreibgeschütztem Bind-Mount im Laufzeitimage; temporäre Daten in einem 96-MiB-tmpfs. Dieser konkrete Nachweis ist keine allgemeine Speicher- oder Laufzeitzusage für beliebige Parquet-Dateien.

## Reproduktion und Grenzen

Unit: python -m pytest apps/api/tests/test_parquet_format.py apps/api/tests/test_json_format.py apps/api/tests/test_csv_import_options.py apps/api/tests/test_xlsx_format.py -q

DB: docker compose --profile test run --rm --no-deps tests python -m pytest -q -p no:cacheprovider /app/tests/test_parquet_integration.py. Regulären Worker währenddessen pausieren, danach wieder starten.

Web: docker build -f infra/proxy/Dockerfile --target test -t unternehmensplattform-web-tests . Browserfall: pnpm test:e2e --grep "Parquet-Import"; synthetische Fixture unter apps/web/e2e/fixtures.

Die gesamte reguläre Browser-Suite umfasst jetzt sieben Fälle, mit dem zusätzlichen Restorefall acht. Die erwartete Anzahl im Restorewerkzeug wurde aktualisiert; **kein neuer vollständiger Restorelauf** wurde durchgeführt. Ebenso keine Wiederholung des 1-GiB-CSV-Lasttests oder aller alten Browserfälle.

Parquet-Grenzen: einzelne lokale PAR1-Datei, flaches Schema, höchstens 256 Spalten, 8 MiB Footer, 4.096 Gruppen, 64 MiB deklarierte entpackte Daten je Gruppe, 8 GiB insgesamt. Keine verschlüsselten Dateien, externen Spalten, Verzeichnis-/Cloudimporte oder Parquet-Ausgabe abgeleiteter Versionen. Native Decode-Ressourcen bleiben zusätzlich durch den Worker begrenzt. Ein synchroner Gruppenaufruf wird nicht mitten in der Dekodierung unterbrochen.

Nächster M2-Schritt: kontrollierte Datenbankquellen, danach weitere Qualitäts-/Statistikfunktionen und beaufsichtigte typisierte Transformationsvorschläge. Kein neuer produktiver Betrieb, Remote-CI-Lauf oder allgemeiner 1-GiB-Parquet-Nachweis.
