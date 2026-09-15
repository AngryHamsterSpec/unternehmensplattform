# Vorgeschlagene Repository-Struktur

> Fortschreibung 10.09.2026: Der folgende Phase-0-Entwurf bleibt das Zielbild. Den konkreten Phase-1-Stand beschreiben [ADR 0002](adr/0002-phase1-runtime-and-contracts.md), [API-Verträge](API_CONTRACTS.md) und [Prüfbericht](testing/PHASE_1_REPORT.md). Entwurfswerte sind keine Laufzeitnachweise.

Status: ENTWURF. Nur Dokumentation und Konventionsdateien sind derzeit angelegt. Der folgende Baum beschreibt die spätere Zielstruktur; er ist kein Verzeichnis vorhandener Funktionen.

```text
/
├── AGENTS.md, README.md, CONTRIBUTING.md, SECURITY.md, CHANGELOG.md
├── .editorconfig, .gitattributes, .gitignore
├── docker-compose.yml                 # M1: Kern mit lokaler Anmeldung
├── .env.example, .dockerignore        # M1: geprüfte sichere Konfiguration
├── apps/
│   ├── api/
│   │   ├── pyproject.toml, uv.lock
│   │   ├── Dockerfile
│   │   ├── migrations/                # Alembic: versionierte SQL-Änderungen
│   │   ├── src/platform_app/
│   │   │   ├── main.py, configuration.py
│   │   │   ├── shared/                # AuthContext, IDs, Geld, Fehler
│   │   │   ├── identity/
│   │   │   ├── intake/
│   │   │   ├── decisions/
│   │   │   ├── agents/
│   │   │   └── audit/
│   │   └── tests/                     # Unit, PostgreSQL, API, Verträge
│   └── web/
│       ├── package.json, package-lock.json
│       ├── Dockerfile
│       ├── src/features/              # Szenarien, Vergleich, Audit
│       ├── src/api/generated/        # aus OpenAPI generiert
│       ├── src/components/            # kleines internes Designsystem
│       └── tests/
├── contracts/                        # generiertes OpenAPI, Schemas
├── configuration/                    # versionierte Regeln und Demo-Kataloge
├── fixtures/synthetic/               # belegbar fiktive Szenarien
├── tests/e2e/                        # Playwright über echten Compose-Stack
├── tests/evaluations/                # Regression, Live nur explizit
├── infra/
│   ├── proxy/
│   ├── identity/                     # lokaler Realm ohne echte Secrets
│   ├── compose/                      # test, demo, production-template
│   └── security-lab/                 # erst M5, separate Compose-Datei
├── scripts/                          # erst mit tatsächlich nötigen Befehlen
├── .github/workflows/                # ab M1 mit realen Prüfkommandos
└── docs/
    ├── PROJECT_CHARTER.md, ARCHITECTURE.md, DATA_MODEL.md
    ├── IMPLEMENTATION_PLAN.md, ROADMAP.md, STATUS.md
    ├── PHASE_1_SPEC.md, AGENT_HIERARCHY.md, API_CONTRACTS.md
    ├── TECHNOLOGY_MATRIX.md, DOCKER_ARCHITECTURE.md
    ├── REQUIREMENTS_TRACEABILITY.md, PHASE_0_REVIEW.md
    ├── requirements/                 # Originalmandate als Quellen
    ├── prompts/                      # deutscher nächster Arbeitsauftrag
    ├── adr/, security/, modules/, testing/, ihk/, learning/
```

## Regeln innerhalb eines Fachmoduls

Ein Modul erhält domain/ für reine Regeln, application/ für Anwendungsfälle und ports/ nur bei einer tatsächlich auswechselbaren Grenze. adapters/ enthält SQL-/Provider-Anbindung; api/ enthält DTOs und Routen. Kleine Module dürfen flacher bleiben. Jede Schicht rechtfertigt ihren Aufwand durch einen konkreten Verbraucher.

Implementierte Hauptmodule erhalten README.md, EXPLAIN.md und TESTING.md. Diese erläutern Problem, Fluss, wichtige Funktionen, Tabellen, Ausfälle, Erweiterungen und Interviewfragen. Die derzeitige Phase 0 erfindet weder Klassen noch Funktionsnamen einer noch nicht geschriebenen Anwendung.

Spätere Module data, processes, cloud, security, support, factory und assistant entstehen mit M2–M7. Ein Verzeichnis voller unbenutzter Klassen gilt nicht als Fortschritt.
