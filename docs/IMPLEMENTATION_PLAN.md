# Umsetzungsplan

Stand: **14.09.2026**. M0 dokumentiert; M1 und der vereinbarte M2-Funktionsumfang lokal implementiert und geprüft. **M2 ist gemäß Nutzerentscheidung erledigt; der aktuelle Restore-Nachweis bleibt nach 180-Sekunden-Timeout beim anfänglichen Prüfsummenvergleich offen.** [Abschlussbericht](testing/M2_COMPLETION_REPORT.md), [Status](STATUS.md). Die manuelle zentrale Dataset-Quote mit Default **1000** bleibt erhalten. **Stopp nach M2; M3 wurde nicht begonnen.** Nachfolgende ältere Fortschrittsabschnitte dokumentieren historische Teilschritte.

## Arbeitsweise

Jeder Meilenstein liefert einen benutzbaren vertikalen Ablauf mit Fachlogik, Daten, Berechtigungen, Oberfläche und Nachweisen. Entscheidungen werden vor umfangreicher Implementierung getroffen; Entwürfe werden bei neuen Erkenntnissen korrigiert. Nach Abschluss aktualisiert STATUS.md den tatsächlichen Stand.

## M0 — Architektur und gemeinsame Durchsicht

Liefergegenstände: Projektverfassung, Architektur/ADR, Domänen- und Datenmodell, Agentenhierarchie, Docker-Entwurf, Technologiealternativen, Threat Model, API-Verträge, Teststrategie, Anforderungsmatrix und konkreter M1-Auftrag. Prüfung auf Widersprüche, vollständige Mandatsabdeckung und lesbare Links. Kein Anwendungscode.

## M1 — Szenario bis geprüftem Architekturvergleich

Die Reihenfolge reduziert technische Risiken, ohne in ungenutzten Schichten stecken zu bleiben:

| Schritt | Konkret herzustellendes Ergebnis | Abschlussbeleg |
| --- | --- | --- |
| M1.1 | Gepinnte Laufzeiten, Compose, Migration, OIDC roundtrip über Browser/Container, erste Tenant-Policy | Build, echter Login, zwei Mandanten, migrationsfähige DB |
| M1.2 | Formular → valide Profilversion → PostgreSQL → Wiederaufruf | API-/Browser-Test, Fehlereingaben und Versionskonflikt |
| M1.3 | Vier Kandidatenarten, Ruleset, synthetischer Preiskatalog, Gewichtung und TCO | nachgerechnete Golden-Fälle und Invarianten |
| M1.4 | Ergebnis mit Einzelbeiträgen, Evidenz, Verifier und Audit atomar persistieren | Manipulations-/Rollback-/Idempotenztests |
| M1.5 | Deutsche Ergebnis-/Vergleichsansicht und rollenabhängige Verwaltung | Viewer-/Tenant-Negativtests, Tastaturbedienung |
| M1.6 | Regelbasierte Erklärung, optionaler gekapselter OpenAI-Adapter | Provider-Vertrag, Datenminimierung, Timeout, Kennzeichnung |
| M1.7 | Demo, Neustart/Restore, CI, Dokumentation, Messprofil | vollständiger E2E-Ablauf und nachvollziehbarer Prüfbericht |

M1.1 ist der entscheidende Machbarkeitstest für OIDC/Proxy/Compose. Falls kompatible stabile Versionen nicht gemeinsam laufen, zuerst belegte Alternative wählen und ADR/Matrix ändern. Nicht über einen stillen Sicherheits-Bypass umgehen.

## M2 — Datenintelligenz

CSV als erster kompletter Import → Profiling → manuelle Transformation → Vorschau → bestätigte neue Version → Visualisierung → Export. Hier entstehen Worker, PostgreSQL-Jobzustände, Ressourcenlimits und Objektspeicher-Port. Danach JSON, XLSX, Parquet und Datenbankquellen mit eigenen Validierungs- und Sicherheitsnachweisen.

KI schlägt strukturierte Transformationen vor; dieselbe deterministische Pipeline führt sie nach Bestätigung aus. Rohdatei, Pipeline, Profil, Resultat, Urheber und Hashes bleiben verknüpft. Mehrere Scanner-/Analysewerkzeuge werden nicht vor einem belegten Workflow angeschlossen.

## M3 — Prozessintelligenz

Typisierter EventLog-Vertrag aus M2 → validierte Zeitdaten → KPI-Berechnung → belegter Engpass → aktuelle und vorgeschlagene Prozessdarstellung. Wartezeit benötigt belastbare Start-/Enddaten; fehlende Ereignisse ergeben keine erfundene Dauer. Auslastung benötigt Kapazität und Arbeitszeitmodell. Verbesserung ist eine messbare Hypothese, keine garantierte Einsparung. Process-Mining-Bibliothek erst nach Nutzen-/Lizenz-/Datenprüfung.

## M4 — Cloud, FinOps und Resilienz

Szenario → lesendes Inventar bzw. ausdrücklich importierter Snapshot → versionierter Preis-/Kostenbezug → Rechte-/Backup-/DR-Plan → nachvollziehbarer Report. Zuerst ein Provider mit minimalem Scope, zweiter über denselben Vertrag. Ein Live-Provider ohne Zugang bleibt korrekt als nicht live getestet markiert.

Terraform-Ausgabe ist ein Planartefakt. Kein Apply in diesem Meilenstein. Ein späterer Schreibpfad benötigt eigenen Freigabe-, Drift-, Fehler- und Wiederanlaufnachweis.

## M5 — Defensives Security Lab

Autorisierter Scope → kontrollierter nichtdestruktiver Scan → unveränderte Scannerbelege → Findings → menschliche Prüfung → Behebungshinweis → erneute Messung. Separater Compose-Stack und interner Laborbereich. Ein vollständiger Scanneradapter zuerst, weitere SAST-/Abhängigkeits-/SBOM-/Container-/Baseline-Werkzeuge danach. Keine Ausführung frei generierter Kommandos.

## M6 — Kundensupport mit Quellen

Freigegebene Dokumente importieren → tenant-/rollenisoliert suchen → belegte Antwort → bei Unsicherheit eskalieren → Feedback. Retrieval-Qualität wird gemessen, bevor pgvector verpflichtend wird. Dokumentwiderruf entzieht auch Index-/Cachezugriffe. Ausgehende Nachrichten bleiben Entwurf bzw. benötigen explizite Freigabe.

## M7 — Agent Factory und In-App-Hilfe

Spezifikation → Validator → Risiko-/Toolprüfung → Evaluation → menschliche Freigabe → aktivierte Version. Feedback wird in geprüfte Vorschläge überführt. Die In-App-Hilfe erklärt Seitenzustand, Rollen, Fachbegriffe, manuelle Schritte und sichere nächste Aktionen anhand autorisierten Kontexts.

## M8 — Gesamtabnahme und Betriebsreife

Alle sieben Zielworkflows aus dem Master Prompt erneut zusammen prüfen. Performance auf dokumentierter Referenzhardware messen; Ausfälle und Restore üben; Sicherheitsfunde schließen oder befristet verantwortet behandeln; Produktivkonfiguration, Monitoring, Geheimnisrotation und Datenlebenszyklus überprüfen. Offene Live-Verbindungen ausdrücklich ausweisen.

## Review nach jedem Meilenstein

Architektur: Grenzen und Abhängigkeiten; Sicherheit: Rechte/Trust Boundaries; Daten: Verträge/Lineage; QA: Rand- und Ausfallfälle; Betrieb: Diagnose/Restore; Wartbarkeit: verständliche Änderungspfade. Festgestellte Fehler werden korrigiert und erneut gezielt geprüft. Reviews sind keine bloßen Textabschnitte ohne Konsequenz.

## M2-Fortschritt vom 12.09.2026

Reale CSV-Reparatur mit erfolgreicher Wiederaufnahme aller fünf beanstandeten Dateien abgeschlossen. JSON/JSONL als nächster flacher Tabellenadapter implementiert; aktuelle Nachweise im [JSON-Bericht](testing/M2_JSON_REPORT.md). XLSX wurde anschließend ergänzt; offen bleiben Parquet und Datenbankquellen sowie die weiteren Modul-C-Analysen und beaufsichtigten typisierten KI-Transformationsvorschläge. Die bestehende deterministische Freigabegrenze gilt auch für spätere Agenten.

## Gemeinsames Produktdesign und XLSX

IT-Kompass besitzt eine gemeinsame visuelle Grundlage für M1–M8; bestehende Komponenten und ECharts bleiben erhalten. XLSX ergänzt M2 um den kontrollierten Arbeitsblattimport. [Designsystem](DESIGN_SYSTEM.md), [ADR 0011](adr/0011-xlsx-tabellenadapter.md), [Nachweis](testing/M2_PRODUCT_XLSX_REPORT.md). Parquet ist implementiert; als Nächstes Datenbankquellen und weitere Modul-C-Analysen samt beaufsichtigten Transformationsvorschlägen. Die geplante Agentenhierarchie und die deterministische Freigabegrenze bleiben maßgeblich.

## Parquet am 13.09.2026

Der Parquet-Adapter ist bis zur bestätigten Bereinigung und zum Export implementiert und lokal geprüft. [Prüfbericht](testing/M2_PARQUET_REPORT.md). Offen bleiben Datenbankquellen, zusätzliche Qualitätsregeln/Statistik und beaufsichtigte KI-Transformationsvorschläge. Keine Erweiterung der Agentenrechte oder Umgehung der bestehenden Freigabegrenzen.

## Frontendabschluss und nächster M2-Schritt

Vertieftes Enterprise-Design lokal implementiert; [Prüfbericht](testing/M2_ENTERPRISE_DESIGN_REPORT.md). Die manuell eingeführte zentrale Dataset-Quote mit Default 1000 und `check_dataset_quota(db)` bleibt erhalten. Jetzt Datenbankquellen, Qualitätsregeln/Statistik und beaufsichtigte Transformationsvorschläge unter der bestehenden Agenten- und Freigabearchitektur fortführen. Originaldaten bleiben unverändert; eine langfristig isolierte Testumgebung bleibt ein Betriebsaspekt.

## Erster Datenbankadapter abgeschlossen

SQLite-Snapshots sind am 13.09.2026 einschließlich Tabellenwahl, Fehlerkorrektur, Profil, Vorschau, bestätigter Version und Export lokal implementiert und geprüft. [Nachweis](testing/M2_SQLITE_REPORT.md), [ADR 0013](adr/0013-sqlite-datenbanksnapshots.md). Die zentrale Nutzerquote mit Default 1000 bleibt aktiv. Für direkte Netzwerk-Datenbankquellen als Nächstes einen expliziten Secret-/Verbindungs-/Snapshotvertrag mit minimalen Leserechten umsetzen; keine freien SQL- oder Agentenrechte. Danach zusätzliche Qualitätsregeln/Statistik und typisierte beaufsichtigte Transformationsvorschläge.
