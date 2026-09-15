# Nachverfolgung der Anforderungen

Stand: 09.09.2026. Diese Zuordnung bestätigt die Berücksichtigung im Entwurf, nicht die Implementierung. Quelle ist der [vollständige Master Prompt](requirements/MASTER_PROMPT_ORIGINAL.md). Die deutsche [Projektverfassung](PROJECT_CHARTER.md) legt Sprache und Arbeitsweise fest.

## Die zwölf Phase-0-Liefergegenstände

| Nr. | Gefordert | Geliefertes Dokument |
| --- | --- | --- |
| 1 | Architektur | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 2 | Implementierungsplan | [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) |
| 3 | Roadmap | [ROADMAP.md](ROADMAP.md) |
| 4 | Erstes ADR | [ADR 0001](adr/0001-system-architecture.md) |
| 5 | Threat Model | [THREAT_MODEL.md](security/THREAT_MODEL.md) |
| 6 | Vorgeschlagene Repositorystruktur | [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) |
| 7 | Datenbank-/Domänenmodell | [DATA_MODEL.md](DATA_MODEL.md), [DOMAIN_MAP.md](modules/DOMAIN_MAP.md) |
| 8 | Agentenhierarchie | [AGENT_HIERARCHY.md](AGENT_HIERARCHY.md) |
| 9 | Docker-Architektur | [DOCKER_ARCHITECTURE.md](DOCKER_ARCHITECTURE.md) |
| 10 | Teststrategie | [TEST_STRATEGY.md](testing/TEST_STRATEGY.md) |
| 11 | Abnahmekriterien | [MILESTONE_ACCEPTANCE.md](testing/MILESTONE_ACCEPTANCE.md) |
| 12 | Technologiematrix | [TECHNOLOGY_MATRIX.md](TECHNOLOGY_MATRIX.md) |

Zusätzlich: API-Verträge, spezifizierte Entscheidungslogik, Review, Status, IHK-Abgrenzung, Lernpfad und nächster deutscher Umsetzungsauftrag.

## Alle Abschnitte des Master-Mandats

| Abschnitt | Inhalt | Entwurfsnachweis / geplanter Umsetzungszeitpunkt |
| --- | --- | --- |
| 0 | Autonomie, Engineering, Statuspflege | Projektverfassung, AGENTS.md, Implementierungsplan; jede Phase |
| 1 | Produktvision | Projektverfassung und Domänenkarte; M1–M8 |
| 2 | Architekturprinzipien | Architektur, ADR 0001; M1 und laufend |
| 3 | Technologie | Technologiematrix mit Quellen; tatsächliche Pins vor Implementierung |
| 4 | Fachmodule A–J | Zuordnung unten; M1–M7 |
| 5 | Kontrollierte Verbesserung | Agentenhierarchie, Factory-Vertrag; M7 |
| 6 | Sicherheitsarchitektur | Threat Model, Trust Boundaries, Data Classification, Incident Response; Schutz ab M1 |
| 7 | Datenbankmodell | Datenmodell mit FKs, Indizes, RLS, Versionen; M1 und Erweiterungen |
| 8 | API | API-Verträge und OpenAPI-Ziel; M1 |
| 9 | Jobs | Architektur und Docker-Entwurf; echte Queue/Worker ab M2 |
| 10 | Frontend | API-/UI-Verträge, P1-Spezifikation; Designsystem/zugängliche Arbeitskonsole M1 |
| 11 | Erklärbarkeit und Moduldokumentation | Lernpfad, Modul-README/EXPLAIN/TESTING je implementiertem Modul |
| 12 | IHK/berufliche Dokumentation | IHK-Abgrenzung jetzt; echte Projektnachweise bei tatsächlichem Ausschnitt |
| 13 | Tests und Evaluation | Teststrategie/Abnahme; M1–M8 |
| 14 | Security-Testumgebung | Docker-/Threat-Entwurf; isoliertes Labor M5 |
| 15 | Fehler- und Chaostests | Teststrategie; relevante Ausfälle ab jeweiligem Modul |
| 16 | Performance | Architektur/Messprofil; Baseline M1, Erweiterungen M2–M8 |
| 17 | Observability | Architektur/Agenten-/Datenmodell; strukturierte Logs, IDs, Health ab M1 |
| 18 | Portabilität | Docker-Architektur; Linux/Windows-Docker und CPU-Nachweise ab M1 |
| 19 | Umgebungsprofile | Docker-Architektur; development/test/demo P1, Lab M5, production-template schrittweise |
| 20 | CI/CD | Teststrategie; reale GitHub Actions ab M1, optionale manuelle Live-Evaluation |
| 21 | Repositoryqualität | README, CONTRIBUTING, SECURITY, CHANGELOG, Editor/Git-Konventionen; CODEOWNERS erst mit echtem Verantwortlichen |
| 22 | Lokale Demo | P1-Spezifikation, synthetische Org/Rollen/Szenarien; Daten/Prozesse/Wissen/Lab mit M2/M3/M6/M5 |
| 23 | Sieben Akzeptanzworkflows | Tabelle unten; jeweils durchgängige Abnahme |
| 24 | Quality Gates | Projektverfassung und Meilensteinabnahme |
| 25 | Iterative Umsetzung | Implementierungsplan M0–M8 |
| 26 | Sechs Reviewperspektiven | Phase-0-Review und Teststrategie; Korrekturen vor Abnahme |
| 27 | Gesamt-Definition of Done | Projektverfassung, M8; kein vorzeitiger Vollständigkeitsanspruch |

## Fachmodule und Workflows

| Modul | Inhalt und Umfang | Erste Lieferphase | Zielworkflow |
| --- | --- | --- | --- |
| A | Unternehmensanforderungen, Assets, Arbeitslasten, Szenarien | M1, vertiefende Erweiterungen später | 1 |
| B | Regeln, Kosten/Leistung, Alternativen, TCO, Evidenz | begrenzter funktionsfähiger Kern M1 | 1 |
| C | CSV/JSON/XLSX/Parquet/DB, Profiling, Regeln, manuelle/assistierte Transformation, Lineage, Export | M2, Formate einzeln nachweisen | 2 |
| D | Eventdaten, KPIs, Engpässe, Prozessdiagramm, messbare Verbesserung | M3 | 3 |
| E | Azure/AWS-Ports, Inventar, FinOps, RBAC, RTO/RPO, Backup/DR, IaC-Pläne | M4, Provider einzeln nachweisen | 5 |
| F | Scope, nichtdestruktive Scanner, SBOM/Finding/Beleg/Remediation/Rescan | M5, Werkzeuge schrittweise | 4 |
| G | Hierarchie, minimale Rechte, strukturierte Ein-/Ausgabe, Budget, Trace, Freigabe | begrenzter Kern M1, Jobs M2, weitere Domänen danach | querschnittlich |
| H | Agent Factory, Versionen, Prüfungen, Evaluation, menschliche Aktivierung | M7 | 7 |
| I | freigegebenes Wissen, tenant-/rollenisoliertes Retrieval, Quellen, Eskalation, Feedback | M6 | 6 |
| J | Seiten-/Rollenhilfe, Fachbegriffe, manuelle und assistierte Schritte | einfache UI-Hilfe M1, universeller Assistent M7 | querschnittlich |

Kein Teil des Gesamtmandats wird durch die kleine erste Ausbaustufe stillschweigend gestrichen. Ein Modul bleibt TEILWEISE IMPLEMENTIERT, solange zugesagte Teilformate, Provider oder wesentliche Abläufe fehlen.

## Bewusste Änderungen und Verschiebungen

| Vorgabe / Annahme | Entscheidung | Begründung und Nachweis |
| --- | --- | --- |
| Englisch empfohlen | Deutsch für Projekt/Produkt; Originaltexte als Referenz | ausdrückliche Nutzerentscheidung |
| Sofort viele Agentenrollen | deterministische Koordination, ein optionaler Erklärungsspezialist zuerst | Fachrechnung braucht kein LLM; Agentenhierarchie/ADR |
| Service- und Deploymentmodelle als Liste | getrennte Achsen und verbundene Pläne | fachlich saubere Kandidatenbildung; Decision Engine |
| Redis/MinIO früh möglich | keine P1-Pflicht; Einführung bei echtem Bedarf | Technologie- und Docker-Matrix |
| Ein Security-Lab-Profil | separate Compose-Datei/Projekt, intern isoliert | Profile allein verhindern kein versehentliches Aktivieren |
| „Confidence“ | Vollständigkeit, Evidenzabdeckung, Rangstabilität | keine erfundene Erfolgswahrscheinlichkeit |
| Cloud Apply | M4 liefert lesenden Ablauf und Pläne; Apply als eigene spätere Erweiterung | Approval-/Idempotenz-/Driftnachweise erforderlich |
| Aktuelle Versionen | datierte Quellen und Kandidaten jetzt; gemeinsamer Lockfile-/Buildnachweis P1 | Recherche beweist keine Interoperabilität |
| IHK-Gesamtprojekt | Plattform als Portfolio, begrenzter betrieblicher Ausschnitt später | keine erfundenen Antragsbedingungen oder Arbeitsnachweise |

## Fortschreibung M2-CSV

M1 ist im lokalen Demo-Umfang implementiert. Der erste Teil von Modul C / Zielworkflow 2 ist jetzt durchgängig implementiert: CSV, Profiling, manuelle Transformation, Vorschau, bestätigte Historie, interaktive Kategorienansicht und Export. Persistente Jobs, begrenzter Worker, Speicherport und Lineage werden tatsächlich verwendet.

Die Dateiformate JSON/JSONL, XLSX und Parquet wurden anschließend ergänzt; seit 13.09.2026 sind auch SQLite-Snapshots bis zur bestätigten Version und zum Export implementiert. Direkte Netzwerk-Datenbankquellen, wiederverwendbare fachliche Qualitätsregeln, vertiefte Statistik sowie beaufsichtigte KI-Vorschläge bleiben offen; Modul C und M2 bleiben deshalb TEILWEISE IMPLEMENTIERT. [Aktueller SQLite-Nachweis](testing/M2_SQLITE_REPORT.md), [ursprünglicher CSV-Nachweis](testing/M2_CSV_REPORT.md).

## M2-Erweiterung vom 14.09.2026

Modul C ist im Code jetzt durch CSV/JSON/JSONL/XLSX/Parquet/SQLite und registrierte PostgreSQL-Snapshots, Schema/Profil, Fehlwerte/Duplikate, gültigkeits-/fachliche Regeln, R7-Verteilungen/IQR/Pearson/UTC-Zeitreihen, Qualitätsscore, wiederverwendbare Regelversionen, manuelle/geprüfte assistierte Bereinigung, unveränderliche Herkunft, visuelle Analyse und HTML-/JSON-Berichte abgedeckt. Modul G erhält hierfür begrenzte persistente Aufgaben und deterministische Agenten-/Freigabekontrollen. ML-Hooks werden als tatsächlicher typisierter Erweiterungsvertrag dokumentiert; ohne konkreten Bedarf keine leeren Clustering-/Forecasting-Gerüste. Die [lokalen Funktions-, Browser-, Sicherheits- und Betriebsnachweise](testing/M2_COMPLETION_REPORT.md) sind erbracht. Der aktuelle Restore-Lauf brach vor Backup/Wiederherstellung beim Prüfsummenvergleich ab. Auf ausdrückliche Nutzeranweisung wird M2 als erledigt geführt; dieser offene Nachweis wird dadurch nicht als bestanden umgedeutet. Live-KI bleibt NICHT LIVE GETESTET. M3 ist nicht begonnen.
