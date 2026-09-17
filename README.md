# Unternehmensplattform

**Plattform für IT-Architekturentscheidungen und Datenqualität**

Eine Webanwendung zur strukturierten Bewertung technischer Unternehmensszenarien und zur nachvollziehbaren Verarbeitung tabellarischer Daten. Die Plattform verbindet Entscheidungslogik, Datenqualität, Versionierung, rollenbasierte Zugriffe und reproduzierbare Prüfabläufe in einer lokalen, containerisierten Umgebung.

> Alle Demo-Unternehmen, Beispieldaten und Katalogpreise sind synthetisch.

## Überblick

Die Anwendung deckt zwei zentrale Arbeitsbereiche ab:

- **Architekturentscheidungen:** technische Szenarien erfassen, Varianten bewerten, Kosten und Leistungsaspekte vergleichen und Ergebnisse versionssicher nachvollziehen.
- **Datenwerkstatt:** Dateien und freigegebene PostgreSQL-Quellen importieren, Qualität analysieren, Bereinigungen als Vorschau prüfen und bestätigte Versionen sicher exportieren.

Der Fokus liegt auf nachvollziehbaren Datenflüssen, klaren Berechtigungsgrenzen und automatisierter Qualitätssicherung.

## Kernfunktionen

### IT-Architektur und Bewertung

- Versionierte Unternehmensszenarien, Workloads und Infrastruktur-Assets
- Vergleich von SaaS-, PaaS-, IaaS- und Hybridvarianten
- Gewichtete Bewertung von Wirtschaftlichkeit und Leistung
- Reproduzierbare Berechnungen mit Dezimalarithmetik
- Vergleich gespeicherter Ergebnisse und historischer Stände
- Rollenbasierte Organisationszugriffe mit Mandantentrennung
- Auditierbare Änderungen und nachvollziehbare Bewertungsverläufe

### Datenwerkstatt

- Import von **CSV, JSON, JSONL, XLSX, Parquet und SQLite**
- Anbindung freigegebener **PostgreSQL-Quellen**
- Dateiuploads bis **1 GiB** mit abschnittsweiser Verarbeitung
- Qualitätsprofile, Statistiken und Datenvisualisierungen
- Manuelle und assistierte Bereinigungsschritte mit Vorschau vor Übernahme
- Versionierte Datensätze und unveränderte Originaldateien
- Sichere CSV-Exporte mit Schutz vor Formel-Injektion
- Diagramme als interaktive Ansicht sowie PNG-/SVG-Export

## Technischer Stack

| Bereich | Technologien |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy |
| Frontend | React, TypeScript, Vite, ECharts |
| Datenbank | PostgreSQL |
| Identität | OIDC / PKCE, Keycloak |
| Container | Docker, Docker Compose |
| Tests | Pytest, Vitest, Playwright |
| Qualität | Ruff, Mypy, Prettier, ESLint |
| Paketmanagement | pip mit Hash-Locks, pnpm |

## Architektur

```text
Browser
  │
  ▼
Reverse Proxy
  │
  ├── React Frontend
  │
  ├── FastAPI Backend
  │     ├── Entscheidungslogik
  │     ├── Datenverarbeitung
  │     ├── Rollen & Autorisierung
  │     └── Audit & Versionierung
  │
  ├── Keycloak (OIDC)
  │
  └── PostgreSQL
        └── Row-Level Security / Mandantentrennung
```

Die Backend-Module sind fachlich getrennt und dokumentieren Datenfluss, Fehlerfälle, Erweiterungspunkte und Tests jeweils in eigenen README-Dateien.

## Lokale Demo starten

### Voraussetzungen

- Docker Desktop mit Linux-Containern und Compose
- Python 3.12 oder neuer

### Start

```sh
python scripts/setup_local.py
docker compose up --build -d --wait --wait-timeout 240
```

Anschließend:

```text
http://localhost:8080
```

Die Demo-Konten `admin`, `analyst`, `viewer` und `mandant-b` verwenden das lokal erzeugte Passwort aus:

```text
.local/demo-zugang.txt
```

`.env` und lokale Zugangsdaten werden nicht versioniert.

### Stoppen und erneut starten

```sh
docker compose ps
docker compose stop
docker compose up -d --wait
```

`docker compose stop` erhält die Volumes. `docker compose down --volumes` entfernt lokale Testdaten vollständig.

## Typischer Ablauf

### Architekturentscheidung

```text
Anmelden
→ Organisation wählen
→ Szenario anlegen
→ Beispiel oder eigene Werte erfassen
→ Bewertung starten
→ Ergebnis prüfen
→ Varianten vergleichen
```

### Datenanalyse

```text
Anmelden
→ Datenwerkstatt öffnen
→ Datei oder Datenquelle importieren
→ Qualität und Statistik prüfen
→ Bereinigung planen
→ Vorschau kontrollieren
→ neue Version bestätigen
→ Ergebnis exportieren
```

## Sicherheit

Die Plattform verwendet unter anderem:

- OIDC mit PKCE
- serverseitige Sessions
- CSRF-Schutz
- rollenbasierte Autorisierung
- PostgreSQL Row-Level Security
- Mandantentrennung
- unveränderte Originaldateien und Prüfsummen
- sichere Exportbehandlung für Tabelleninhalte
- restriktive Security-Header
- automatisierte Dependency- und Containerprüfungen

Weitere Details befinden sich in [SECURITY.md](SECURITY.md) und im [Bedrohungsmodell](docs/security/THREAT_MODEL.md).

## Tests und Qualitätssicherung

Backend, Frontend und Laufzeitumgebung werden automatisiert geprüft. Der CI-Ablauf umfasst unter anderem:

```sh
python -m ruff format --check --config apps/api/pyproject.toml apps/api/src apps/api/tests scripts
python -m ruff check --config apps/api/pyproject.toml apps/api/src apps/api/tests scripts
python -m mypy --config-file apps/api/pyproject.toml apps/api/src/platform_app
python -m pytest apps/api/tests -p no:cacheprovider -q

pnpm --dir apps/web run format:check
pnpm --dir apps/web run lint
pnpm --dir apps/web run build
pnpm --dir apps/web run test
```

Zusätzlich werden Integrations- und Browserabläufe mit PostgreSQL, Keycloak, Docker und Playwright geprüft.

## Projektstruktur

```text
.
├── apps/
│   ├── api/                # FastAPI-Backend
│   └── web/                # React-/TypeScript-Frontend
├── docs/                   # Architektur, Verträge, ADRs und Prüfberichte
├── infra/                  # Container- und Proxy-Konfiguration
├── scripts/                # Setup-, Prüf- und Wartungsskripte
├── .github/workflows/      # CI
├── compose.yaml
├── SECURITY.md
└── README.md
```

## Wichtige Dokumentation

- [Architektur](docs/ARCHITECTURE.md)
- [API-Verträge](docs/API_CONTRACTS.md)
- [Projektverfassung](docs/PROJECT_CHARTER.md)
- [Sicherheitsmodell](docs/security/THREAT_MODEL.md)
- [Datenmodul](apps/api/src/platform_app/data/README.md)
- [Identität und Zugriff](apps/api/src/platform_app/identity/README.md)
- [Entscheidungslogik](apps/api/src/platform_app/decisions/README.md)
- [Bewertungen](apps/api/src/platform_app/assessments/README.md)

## Entwicklung

```sh
python -m venv .venv
python -m pip install --require-hashes -r apps/api/requirements-test.lock
python -m pip install --no-deps -e apps/api
pnpm --dir apps/web install --frozen-lockfile
```

Für lokale Python-Aufrufe `PYTHONPATH=apps/api/src` setzen, falls das Backend nicht editable installiert wurde.

## Projektziel

Dieses Repository demonstriert die Umsetzung einer modularen Unternehmensanwendung mit Fokus auf:

- saubere Systemarchitektur
- reproduzierbare fachliche Logik
- sichere Authentifizierung und Autorisierung
- robuste Datenverarbeitung
- Versionierung und Nachvollziehbarkeit
- automatisierte Tests über mehrere Ebenen
- containerisierte lokale Ausführung

Die technische Dokumentation im Repository beschreibt Entscheidungen, Grenzen und Prüfnachweise detaillierter als diese Übersicht.
