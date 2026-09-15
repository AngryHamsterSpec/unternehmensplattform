# ADR 0002 — Umsetzung des ersten Entscheidungsablaufs

Datum: 10.09.2026. Status: angenommen für Phase 1 durch den ausdrücklichen Umsetzungsauftrag. Ergänzt [ADR 0001](0001-system-architecture.md); spätere Module bleiben Entwurf.

## Entscheidung

Der modulare Monolith ist FastAPI mit SQLAlchemy/psycopg und PostgreSQL 18.6. React 19.2.8/Vite 8.2.2 liefert eine deutsche SPA; Nginx übernimmt denselben Ursprung für API und OIDC. Keycloak 26.7.3 ist der lokale Identitätsanbieter. Python 3.14.7 ist das gepinnte Containerziel; die lokal vorhandene Python-3.12.14-Laufzeit ist eine zusätzlich geprüfte Entwicklungsbasis. Der genaue Stand steht in den Lockfiles und Image-Digests.

TypeScript 6.0.3 ersetzt den zunächst erprobten Stand 7.0.2: Die verwendete typescript-eslint-Version konnte die TS-7-Programmierschnittstelle im realen Lintlauf nicht verwenden. Version 6 besteht die strenge Typprüfung und den Build. pnpm 11.19.0 liest Projekteinstellungen aus pnpm-workspace.yaml; globaler Virtual Store ist explizit deaktiviert, damit interaktive und CI-Läufe dieselbe Installation verwenden. verifyDepsBeforeRun=error macht Drift sichtbar.

## Daten und Verträge

19 Tabellen bilden Identitäten, Mitgliedschaften, Sessions, Profilversionen, Workloads, Assets, Kataloge, Bewertungen, Kandidaten, Kostenpositionen, Agentenläufe, Audit und optionale Erklärungsbudgets ab. Fachliche Detailobjekte bleiben zusätzlich als vollständig typisierte, unveränderliche JSON-Snapshots erhalten. Phase-0-Untertabellen für einzelne Anforderungen oder Gewichtungen werden in M1 in diesen Snapshots gespeichert. Zusammengesetzte Fremdschlüssel erzwingen Mandantenkonsistenz; RLS ergänzt die API-Prüfungen.

Die generierten TypeScript-Domänentypen stammen aus den Pydantic-Serialisierungsschemas. UI und Backend teilen dadurch Dezimal-, Kandidaten- und Ergebnisverträge. API-Hüllen für Sitzung und Pagination bleiben kleine explizite Typen. FastAPI stellt die zugehörige OpenAPI-Beschreibung bereit. Ein universell generierter HTTP-Client entsteht erst bei entsprechendem Bedarf.

Originale Profilversionen, Bewertungen, Kostenzeilen, Agentenläufe und Audit sind für die Anwendungsrolle nur les- und ergänzbar. Der Bewertungskatalog wird ausschließlich über Migration/Seed versioniert. Regeln rules-1.1.0 und synthetischer Preiskatalog demo-2026-09-v2 werden mit Hashes gespeichert.

## Agenten und externe Verarbeitung

Manager, Cost Estimator und Verifier sind deterministische Anwendungsrollen. Der Verifier berechnet Regeln, Kosten und Gewichte unabhängig nach. Es laufen keine autonomen Shell- oder Toolschleifen.

Der optionale Erklärungsadapter verwendet die Responses-Schnittstelle des installierten OpenAI-SDK über einen kleinen Provider-Port. Das Agents SDK ist als vorgesehene spätere Integrationsbasis gesperrt installiert, steuert in M1 aber keine Ausführung. Live-Aufrufe benötigen Modell, echte Preise, Organisationsfreigabe, Budget und Zustimmung pro Anfrage. Es gibt keine Tools, keine automatischen Retries und höchstens zehn Sekunden Gesamtlaufzeit.

Eine persistierte Reservierung wird vor dem externen Aufruf committed. Bei unklarem Prozessabbruch zeigt die Leseansicht nach 30 Sekunden INDETERMINATE; die DB-Reservierung bleibt bestehen und wird nicht automatisch erneut ausgeführt. Dieser Zustand behauptet keine Nichtverarbeitung beim Anbieter.

## Folgen und Grenzen

Die Transaktions- und Rechteprüfung liegt im Code und in PostgreSQL. LLM-Text kann keine Ergebnisse oder Rechte ändern. Das Compose-Profil ist eine lokale HTTP-Demo auf Loopback. Produktiver TLS-Betrieb, ARM-Ausführung, umfassende Lastmessung und Live-KI benötigen eigene Nachweise; aktuelle Ergebnisse siehe [Prüfbericht](../testing/PHASE_1_REPORT.md).

Quellen der verwendeten Schnittstellen: [pnpm-Einstellungen](https://pnpm.io/settings), [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [OpenAI-Datenkontrollen](https://developers.openai.com/api/docs/guides/your-data). Die Build-Digests stehen direkt in Compose und Dockerfiles.
