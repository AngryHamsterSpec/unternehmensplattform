# M2 – Abschlussprüfung

Stand: **14.09.2026**. **M2 ist auf ausdrückliche Nutzerentscheidung erledigt; der vereinbarte lokale Funktionsumfang ist IMPLEMENTIERT, integriert und geprüft.** Der aktuelle Restore-Nachweis bleibt nach Timeout offen; dies ist keine vollständige technische Betriebsabnahme. Branch `master`, Images `0.1.0`, Schema `0005`. Das Repository besitzt noch keinen Commit; deshalb keine erfundene Commit-ID. Manuelle Änderungen einschließlich `dataset_limit_per_organization=1000` bleiben erhalten. **Stopp nach M2; M3 wurde nicht begonnen.**

## Abgeschlossener Umfang

- CSV, JSON/JSONL, XLSX, Parquet, SQLite-Snapshots und registrierte PostgreSQL-Quellen führen über dieselbe Original-/Import-/Versionspipeline. Upload bis 1 GiB mit zusätzlichen dokumentierten Format- und Ressourcengrenzen.
- Persistente Vollanalysen: Fehlwerte/Duplikate, Dezimalstatistik, R7-Quantile, Histogramme, IQR-Hinweise, Pearson, UTC-Kalenderaggregation und nachvollziehbarer Qualitätsscore.
- Unveränderliche wiederverwendbare Qualitätsregelsätze, HTML-/JSON-Berichte, Quellen-, Ergebnis-, Urheber- und Zeitmetadaten.
- Manuelle und assistierte Bereinigungspläne mit typisierten Schritten, Verifier, Vorschau und ausdrücklicher menschlicher Versionsfreigabe. Regelbasierte Planung funktioniert ohne KI-Schlüssel; der optionale OpenAI-Adapter ist separat abgesichert.
- Gemeinsames Enterprise-Design mit Auftragshistorie, Abbruch/Wiederholung, interaktiven/statischen Diagrammen und SVG-Export. Migration 0005, separater Quellen-/Analyseworker, Verträge und Restore integriert.

[Verbindlicher Umfang](../prompts/M2_COMPLETION_SCOPE.md), [ADR 0014](../adr/0014-datenanalyse-quellen-und-gepruefte-plaene.md), [Bedienung und Grenzen](../../apps/api/src/platform_app/data/README.md).

## Tatsächlich ausgeführte Nachweise

Windows-Host, Linux/AMD64-Container, echtes lokales PostgreSQL und Keycloak. Ausschließlich synthetische Testquellen; kein externer Modellaufruf. Der Nutzer hat die finalen API-/Worker-Images gebaut und gestartet. Die abschließend korrigierte Webansicht wurde zusätzlich gebaut und lokal gestartet.

| Prüfung | Beobachtetes Ergebnis |
| --- | --- |
| Neue Fach-/PostgreSQL-Prüfungen | 26 Fälle bestanden: beide Speicherformate, RLS, Regeln/Ergebnisse unveränderlich, Berichte, Idempotenz, Pläne, Vorschau/Freigabe, veraltete Version, Lease/Wiederanlauf, Rechteentzug, echte Quelle und KI-Test-Double. |
| Ergänzende Referenz-/Abbruchprüfung | Zwei gezielte Fälle bestanden: große Dezimalwerte und sichere Unterbrechung blockierter Quellenabfragen. Keine Addition wiederholter Fälle zu einer erfundenen Gesamtsumme. |
| Abschließender API-Vertrag | Beide Speicherformatfälle erneut bestanden (20,34 s): Listen ohne schwere Resultate/Requests, vollständiger Detailabruf, Berichts-Urheber/Zeitpunkt/Hash, nosniff, RLS und Unveränderlichkeit. |
| Frontend | 17 Tests, TypeScript, ESLint und Vite-Build bestanden; verzögerte Importannahme und nachgelagerter Detailabruf im Regressionstest enthalten. |
| Reale Browserstrecke | Ein kompletter M2-Fall bestanden (21,9 s; gesamter Runner 25,1 s): OIDC → PostgreSQL-Snapshot → Regelversion → Vollanalyse → Korrelations-/Zeitdiagramm → statischer SVG-/HTML-Export → Reload → Plan → Vorschau → bestätigte Version 2 → bytegleiches Original → 390-Pixel-Ansicht. Keine Seitenfehler. |
| Betriebsprüfung | Nicht privilegierte Container, Loopback-Ports, Ressourcen-/Netz-/Dateisystemgrenzen beider Worker geprüft. DB-Ausfall: Readiness 503, Liveness 200; automatischer Wiederanlauf erfolgreich. |
| Sicherheit | Quellscan mit erkannter Scannerfixture: null Geheimnisse, keine gemeldeten Paket-Schwachstellen. Keine neue große Imagescanserie; bestehende Imagegrenzen bleiben dokumentiert. |
| Wiederherstellung | **NICHT ABGESCHLOSSEN.** Der initiale Prüfsummenvergleich von `data_chunks` überschritt 180 Sekunden. Backup, frisches Restore-Volume und erweiterter Restore-Browserfall wurden nicht erreicht. Beide Originalworker wurden automatisch wieder gestartet; API, Web und PostgreSQL anschließend gesund. Keine verbliebene aktive Prüfsummenabfrage gefunden. Kein neuer Restore-Erfolg behauptet. |
| Statische/Skriptprüfungen | Strenge mypy-Prüfung über 60 Quelldateien, Ruff und Formatprüfung bestanden; vier Restore-Cleanup-Fälle bestanden. Dokumentation und Modulpflichtdateien geprüft. |

## Reproduzierbare Aufrufe

Die Linux-DB-Prüfungen verwendeten das vorhandene Testimage mit aktuellen Quell-/Testdateien als schreibgeschützte Mounts; beide Worker waren für die DB-Fälle pausiert und wurden anschließend freigegeben. So wurden weder veraltete Tests noch der unter Windows blockierte PostgreSQL-Treiber als Nachweis verwendet.

```text
pytest -q tests/test_intelligence_integration.py tests/test_data_intelligence.py
pytest -q tests/test_intelligence_integration.py::test_analysis_rules_report_idempotence_tenants_and_immutable_results
pnpm run typecheck && pnpm run lint && pnpm test && pnpm build
pnpm test:e2e --grep "M2 Vollablauf"
python scripts/check_security.py --sources-only
python scripts/check_runtime.py
python scripts/check_restore.py --full-stack --isolated-browser
python -m unittest discover -s scripts -p test_restore_cleanup.py
```

Für den Windows-Browsernachweis galt `E2E_BROWSER_CHANNEL=chrome`: Das gebündelte Chromium ließ sich nicht starten; vorhandener Chrome lief in einem isolierten Testprofil. Zugangsdaten kamen aus der geschützten lokalen Umgebung und wurden nicht protokolliert. Frontendabhängigkeiten lagen außerhalb des synchronisierten OneDrive-Verzeichnisses. Im isolierten Build fehlten kopierte Schriftdateien; das tatsächliche Web-Image enthält sie. Die bekannte Warnung zum separat geladenen ECharts-Bundle bleibt bestehen.

## Gefundene und behobene Fehler

Die Abnahme korrigierte die veraltete Readiness-Schemaerwartung auf 0005 sowie fehlerhafte Testvorbereitung für Rechteentzug, zusätzliche Frontendabrufe und asynchrone Organisationsauswahl. Der Browser fand einen echten Quellenfehler: Während einer verzögerten neuen Importannahme ließ sich noch das alte Resultat öffnen. Der alte Verweis wird jetzt sofort ausgeblendet; nach Annahme zählt ausschließlich der neue Auftrag. Regression und vollständiger Browserworkflow sind erfolgreich.

Die frühere automatische Werkzeugfreigabe war kapazitätsbedingt gescheitert. Nach dem manuellen Build durch den Nutzer konnten die verbleibenden Prüfungen ausgeführt werden; diese Blockade besteht für den dokumentierten Abschluss nicht mehr.

## Sechs Reviewperspektiven

| Perspektive | Ergebnis |
| --- | --- |
| Fachlichkeit | Referenzwerte, Fehlwerte und Unsicherheit getrennt; Bereinigung erst nach Vorschau/Bestätigung, Original unverändert. |
| Architektur | Bestehende Datenpipeline und Legacy-Versionen erhalten; typisierte Jobs/Regeln/Ergebnisse, getrennter Quellenworker und Erweiterungsverträge. |
| Sicherheit | Reale Tenant-/Quellen-RLS, Rollen/Widerruf, Unveränderlichkeit, Audit, minimierte KI-Daten und Budget-/Freigabegates geprüft. |
| Bedienbarkeit | Vollständiger deutscher Browserworkflow, persistente Berichte, Exporte und mobile Ansicht bestanden; Screenshots angesehen. Bei sehr breiten Statistiktabellen können Bezeichnungen/Zahlen in engen Zellen stark umbrechen; visueller Feinschliff bleibt als bekannte Darstellungsgrenze dokumentiert. |
| Leistung/Betrieb | Begrenzter Hintergrundworker, bedarfsgerechte Berichtsladung und Ausfall/Wiederanlauf nachgewiesen. Der initiale Großdaten-Prüfsummenvergleich ist für den aktuellen Restore-Nachweis zu langsam; Gate offen. Auf Nutzeranweisung keine Wiederholung und kein neuer 1-GiB-Benchmark. |
| Wartbarkeit/Dokumentation | ADR, Modul-README/EXPLAIN/TESTING, API, Agentenhierarchie, Threat Model, Anforderungsmatrix und Abschlussstatus gepflegt. |

[Analysescreenshot](../screenshots/m2-vollanalyse.png), [mobile Ansicht](../screenshots/m2-vollanalyse-mobil.png), [sanitisierte maschinenlesbare Nachweise](m2-completion-evidence.json).

## Verbleibende Grenzen

**Aktueller Restore-Nachweis offen:** Der zugelassene letzte Lauf scheiterte bereits vor dem Backup an `snapshot(SOURCE)` für `data_chunks` (180-Sekunden-Limit). Es gibt keinen neuen erfolgreichen `result.json`-Restorebericht. Historische Restore-Ergebnisse bleiben unverändert gültig für ihren damaligen Umfang, belegen aber nicht die aktuelle vollständige M2-Wiederherstellung. Eine künftige Betriebsfreigabe benötigt einen skalierbaren Dateiprüfsummenvergleich und einen erfolgreichen vollständigen Lauf. Wegen der jüngsten ausdrücklichen Stoppanweisung wurde keine weitere Reparatur- oder Testserie begonnen.

Externe OpenAI-Verarbeitung: **NICHT LIVE GETESTET / BENÖTIGT EXTERNE ZUGANGSDATEN**. Der tatsächliche Adapter wurde mit gekennzeichnetem Test-Double einschließlich Zustimmung, Budget, Timeout und Verifier geprüft. Deterministische Agentenrollen werden nicht als sieben autonome LLM-Aufrufe dargestellt.

ARM64, produktive TLS-/SSO-/Backupumgebung, Remote-CI, weitere Datenbankanbieter und verteilte Verarbeitung besitzen keinen neuen Nachweis. Quellenregistrierung und externe Quelldatenbanken benötigen eigene Betreiberbackups; erfasste Snapshots gehören zum nachgewiesenen Plattformbackup. Der historische 1-GiB-CSV-Nachweis gilt weiter; er ist keine Zusage für jede komprimierte Datei oder beliebige Vollanalysen. Bestehende Keycloak-Imagebefunde und befristete Einordnungen bleiben im [Projektstatus](../STATUS.md) sichtbar.

Der Quellscan erfolgte vor der abschließenden kleinen UI-Rennkorrektur; Abhängigkeiten blieben unverändert. Runtime-Grenzen wurden vor dem letzten Web-Neubau bei identischer Containerkonfiguration geprüft. Auf ausdrücklichen Nutzerwunsch nach dem laufenden Restore keine weitere Testserie oder Frontenderweiterung; **M2 erledigt, M3 nicht begonnen**.
