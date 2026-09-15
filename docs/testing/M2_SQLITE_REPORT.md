# M2 — SQLite-Snapshots: lokaler Nachweis

Stand: 13.09.2026. SQLite-Snapshot-Workflow IMPLEMENTIERT; M2 insgesamt weiterhin TEILWEISE IMPLEMENTIERT.

## Ergebnis

`.sqlite`, `.sqlite3` und `.db` durchlaufen Abschnittsupload, Tabellenwahl, Profilierung, Bereinigungsvorschau, bestätigte Version und CSV-Export. Eine fehlende oder falsche Tabellenwahl lässt sich am gespeicherten Original korrigieren. Originalbytes bleiben unverändert; die gewählte Tabelle bleibt in Folgeversionen sichtbar. Bestehende Daten-/Agenten-/Freigabegrenzen gelten unverändert.

Die manuelle zentrale Dataset-Quote mit Default **1000** und `check_dataset_quota(db)` wurde erhalten. Der aktualisierte lokale API-Container meldet tatsächlich **1000**. Der frühere 100er-Hinweis wurde in Status und Plan korrigiert; keine Originale oder manuellen Sicherungsdateien wurden entfernt.

## Tatsächlich ausgeführte Prüfungen

| Prüfung | Ergebnis |
| --- | --- |
| SQLite-Unitfälle unter Windows | 22 bestanden, 3,47 s |
| Linux: SQLite-Unitfälle, echter PostgreSQL-Workflow, CSV-Leseoptionen und Streaming | 48 bestanden, keine übersprungen, 26,16 s |
| Strenge mypy-Prüfung | 51 Quelldateien ohne Fehler |
| Ruff Format/Lint, geänderte Python-Dateien | 7 Dateien erfolgreich |
| TypeScript und Vite-Produktionsbuild | bestanden |
| Frontendformat, ESLint und Komponententests | 16 Tests bestanden, 15,14 s |
| OIDC-Browser: SQLite-Upload → Tabellenkorrektur → Vorschau → Version 2 → Export/Originalvergleich | bestanden, Fall 10,0 s, Gesamtlauf 12,3 s |
| Quell-/Konfigurationsscan, Trivy 0.74.0 | Scannerfixture erkannt, keine gemeldeten Geheimnisse/Schwachstellen, Gate bestanden |
| Lokaler Betriebszustand | API, PostgreSQL und Web gesund; Worker und IdP laufen |

Der erste Windows-Aufruf konnte das bereits vorhandene temporäre pytest-Verzeichnis nicht öffnen; der erfolgreiche Lauf nutzte ein neues Testverzeichnis innerhalb des Workspace. Der erste Browserlauf scheiterte vor dem Import an einem zu engen Testselektor: Das native Feldlabel enthält auch den Hilfetext. Der Selektor wurde anhand des tatsächlichen DOM korrigiert; anschließend derselbe einzelne Workflow vollständig erfolgreich. Die letzte Änderung betrifft ausschließlich diesen Testselektor; Format separat bestätigt. Kein erneuter vollständiger Frontend-/Backendlauf dafür.

Die Datenbankprüfung deckt Mandantenisolation, Lesekonto ohne Retry-Schreibrecht, Wiederaufnahme, gespeicherte fehlgeschlagene Jobs, Tabellenherkunft, Versionsbestätigung und Originalgleichheit ab. Der normale Worker war während dieser Prüfung pausiert und wurde danach mit dem neuen Image gestartet. Browserdaten sind ausschließlich synthetisch im vorhandenen Testmandanten B.

## Reproduzierbarer Umfang

Gezielter Backendaufruf nach Testimage-Build und bei pausiertem regulärem Worker:

```text
docker compose --profile test run --rm --no-deps tests python -m pytest -q -p no:cacheprovider --tb=short /app/tests/test_sqlite_format.py /app/tests/test_sqlite_integration.py /app/tests/test_csv_import_options.py /app/tests/test_stream_engine.py
```

Frontend-Teststage: `docker build -f infra/proxy/Dockerfile --target test -t unternehmensplattform-web-tests .` Browser: `pnpm test:e2e --grep SQLite-Snapshot` mit lokalem Demo-Passwort aus der Umgebung. Keine Zugangsdaten im Repository oder im Bericht.

Aktivierte Images: API/Worker `sha256:8e04a5ba53a74cd377381b8068e801d3355314ff8397b27587eac46b08a84525`; Web `sha256:907db3c0d420d10e63d59acf2c5307db19772e16827ab50449606a36e328697e`.

## Grenzen

SQLite wird ausschließlich als vollständiger unverschlüsselter Snapshot im DELETE-Journalmodus unterstützt. Die UI und [ADR 0013](../adr/0013-sqlite-datenbanksnapshots.md) erklären Tabellen-, Werte-, Schema- und Ressourcenbegrenzungen. Kein pauschaler Lastnachweis für jede 1-GiB-Datenbank. Kein neuer Benchmark, Restore-Lauf, vollständiger Imagescan, externer Datenbankzugang oder Live-KI-Test. Bestehende Hinweise zur ECharts-Bundlegröße und zum Starlette/AnyIO-Deprecation-Warning bleiben bestehen; beide blockierten die Prüfungen nicht.

Direkte Netzwerk-Datenbankquellen, allgemeine Qualitätsregeln/tiefere Statistik und beaufsichtigte Agentenvorschläge bleiben weitere M2-Arbeit. Die SQLite-Erweiterung ersetzt keinen dieser noch offenen Umfänge.
