# ADR 0001 — Modularer Monolith mit deterministischem Entscheidungskern

Datum: 09.09.2026. Status: VORGESCHLAGEN, fachlich ausgearbeitet; gemeinsame Durchsicht ausstehend.

## Kontext

Zehn eng verbundene Domänen sollen eine erweiterbare, verständliche Portfolio-Plattform bilden. Der erste nachweisbare Nutzen ist ein gespeicherter, erklärbarer Architekturvergleich. Ein einzelner Lernender muss Entwicklung und Betrieb verstehen können. Noch gibt es weder Skalierungsdaten noch eine bestehende Anwendung.

## Entscheidung

Python/FastAPI implementiert einen modularen Monolithen mit expliziten Domänenverträgen. PostgreSQL speichert normalisierte Fachdaten, versionierte Bewertungssnapshots und Audit. React/TypeScript/Vite liefert eine SPA hinter demselben Origin. OIDC übernimmt Anmeldung; lokale Entwicklung enthält Keycloak.

Deterministische Regeln bestimmen Zulässigkeit, Scores und TCO. Manager, Cost Estimator, Verifier und Policy Gate sind zunächst gewöhnliche kontrollierte Anwendungsservices. Ein optionaler LLM-Spezialist erklärt geprüfte Ergebnisse über einen Provider-Port.

PostgreSQL-RLS ergänzt Service-Autorisierung, mandantengebundene Schlüssel und eine getrennte Auth-Rolle. Migration und Anwendung teilen keine privilegierten Zugangsdaten. Langlaufende Aufträge kommen ab M2 in einen Worker desselben Images mit PostgreSQL-Queue. Objektspeicherung folgt mit dem ersten echten Dateiworkflow.

## Bewertete Alternativen

| Alternative | Nutzen | Nachteil im jetzigen Kontext | Urteil |
| --- | --- | --- | --- |
| Viele Microservices | unabhängige Skalierung und Releases | Netzwerkverträge, Deployment- und Transaktionsaufwand ohne Beleg | zurückgestellt |
| Django mit integriertem Admin/Auth | schnelle CRUD- und Administrationsbasis | bevorzugte FastAPI-/Pydantic-Verträge und separate SPA; Admin allein löst OIDC/Objektrechte nicht | valide Alternative, derzeit nicht gewählt |
| Next.js mit Server Rendering | SSR und Fullstack-Funktionen | zweite Server-Geschäftsschicht ohne Bedarf im internen Portal | Vite-SPA |
| Selbst entwickeltes Passwortlogin | ein Dienst weniger | zusätzliche Recovery-, Passwort- und Identitätsrisiken | OIDC |
| LLM entscheidet vollständig | schnelle offene Antworten | keine reproduzierbare Fachrechnung; erfundene Kosten möglich | abgelehnt |
| Redis/Celery sofort | verbreitete Jobwerkzeuge | M1 hat keine lange Datenverarbeitung; zusätzlicher Dienst | Bedarf ab M2 erneut messen |
| SQLite als Laufzeitbasis | leichter lokaler Start | Abweichung von PostgreSQL/RLS und Mehrbenutzerverhalten | nur kurzlebige lokale Experimente, kein Abnahmenachweis |

## Folgen und Nachteile

OIDC und RLS erhöhen den Aufwand in M1. Deshalb sind Login, Connection-Pooling und negative Mandantentests frühe technische Gates. Der Monolith verlangt disziplinierte Modulgrenzen; Importregeln und Vertragsprüfungen begleiten Änderungen.

Deterministische Bewertungsregeln müssen fachlich begründet und gepflegt werden. Ihre Ergebnisse sind Szenarioanalysen, keine Gewissheit über die Realität. Synthetische Preise ermöglichen eine überprüfbare Demo, aber noch keine Einkaufsentscheidung.

Ein PostgreSQL-Jobworker bringt eigene Lease-/Retry-Pflichten. Er wird erst mit M2 umgesetzt und durch Crash-/Duplicate-Tests abgesichert.

## Auslöser für Neubewertung

Messbarer Queue-Rückstau, unabhängige Teams/Releases, regulatorisch begründete physische Mandantenisolation, ein vorhandener Firmen-IdP, notwendiges SSR oder Scanner mit zusätzlicher Isolation können weitere ADRs auslösen. Markenpräferenz oder Lebenslaufwirkung sind keine ausreichenden Gründe.
