# Phase-0-Review und Übergabe

Stand: 09.09.2026. **Architekturentwurf ausgearbeitet; gemeinsame Durchsicht mit dem Projektinhaber offen.**

## Empfehlung

Mit einem modularen Python/FastAPI-Backend, PostgreSQL und einer deutschen React-Arbeitsoberfläche beginnen. Der erste vollständige Ablauf ist ein Unternehmensszenario mit geprüfter Architekturentscheidung und gespeichertem Kosten-/Leistungsvergleich. OIDC, RBAC, Mandantentrennung, Audit, Tests und Docker gehören bereits dazu.

KI-Erklärungen sind eine begrenzte Ergänzung. Die Fachentscheidung ist unabhängig vom Provider. Weitere Module folgen als durchgängige Erweiterungen.

## Prüfung aus sechs Perspektiven

| Perspektive | Konkretes Ergebnis | Übernommene Konsequenz |
| --- | --- | --- |
| Architektur | Zehn Domänen rechtfertigen noch keine zehn Dienste | modularer Monolith; Worker erst bei langlaufenden Aufgaben |
| Sicherheit | Eine ungeprüfte Tenant-ID oder LLM-Aussage darf keine Autorität erhalten | geprüfter AuthContext, RLS/Composite-FKs, getrennte DB-Rollen, werkzeugloser P1-Erklärer |
| Daten | Service-Modelle und Deploymentformen waren im Ausgangstext vermischt | getrennte Achsen; vollständige Kandidatenpläne je Arbeitslast |
| QA | Erfolgsfälle übersehen Replay und fehlende Evidenz | negative Tenant-/Provider-/Verifierprüfungen und Idempotenz für kostenpflichtige Erklärungen |
| Betrieb | vorhandene Docker-CLI beweist keinen startfähigen Stack | Start-/Migration-/OIDC-/Restore- und Multiarch-Gates in P1 |
| Wartbarkeit | zu viele frühe Abstraktionen erschweren Lernen | keine leeren Fachmodule; Modulerklärungen mit tatsächlich implementierten Klassen/Flüssen |

Drei unabhängig bearbeitete Teilbereiche – Sicherheit, Datenmodell und Betrieb/Teststrategie – wurden mit dem Gesamtentwurf abgeglichen. Die Dokumente sind KI-unterstützt erstellt; dies ist kein externer Sicherheitsaudit.

## Im Review korrigiert

- Einheitliche Grenzen: 10 Arbeitslasten und 20 vollständige Kandidatenpläne je Bewertung.
- Healthpfade einheitlich unter /api/v1/health/.
- Auth-Bootstrap bekommt begrenzten eigenen DB-Zugang; Authentifizierungsereignisse bleiben von mandantengebundenem Fachaudit getrennt.
- Kostenkataloge in P1 sind tenant-eigene unveränderliche Demokopien.
- Kostenbeispiel und DB-Constraints verwenden denselben P1-TCO ohne Restwert; Erweiterungen benötigen eine spätere Formelversion.
- KI-Sicherheits-/Budget-/Timeouttests bereits P1; externe Traceexporte in P1 immer aus.
- Erklärung vor Provideraufruf atomar reservieren; Doppelaufrufe starten keine zweite Abrechnung. Unklarer Ausgang wird nicht automatisch wiederholt.
- Optionale Providerkosten besitzen eigene belegte Preiskonfiguration und begrenzte atomare Budgetreservierung; keine fiktiven Marktpreise aus dem Infrastruktur-Demokatalog.
- Ein fehlerhafter Score ist ein eigener Manipulationstest, kein falscher Wert in der fachlichen Referenztabelle.

## Schwache Annahmen des Ausgangstextes

Eine große Funktionsliste beweist keinen Unternehmensnutzen. M1 muss deshalb eine konkrete nachvollziehbare Entscheidung liefern. LLM-Verifier allein verhindern keine Halluzination; ein unabhängiger Rechenkern prüft Zahlen und Bezüge. „Read only“ ist eine tatsächlich begrenzte Berechtigung, kein Agentenname.

RTO, RPO und Verfügbarkeit sind ohne Abhängigkeiten, Last- und Wiederherstellungsnachweis keine Garantie. Fehlende Eventdaten beweisen keine Prozesswartezeit. Budget und Preislisten sind Annahmen mit Zeitbezug. Begriffe wie „kontinuierliches Lernen“ werden als versionierter Verbesserungsprozess umgesetzt.

Docker Compose ist ein lokales Betriebsmodell; Hochverfügbarkeit und Produktionsfreigabe werden damit nicht automatisch erreicht. RLS reduziert Datenzugriffsfehler, schützt aber nicht vor einer vollständig kompromittierten API. Lokale append-orientierte Audits sind gegenüber DB-Administratoren nicht unveränderbar.

## Offene Entscheidungen und technische Nachweise

| Punkt | Für die aktuelle Planung angenommener Standard | Wann festlegen / prüfen |
| --- | --- | --- |
| Produktname und öffentliches Repository | neutraler Arbeitsname, lokal | vor Veröffentlichung |
| Tatsächliche Zielorganisation | rein synthetische Demo | vor realem Einsatz |
| OIDC-Anbieter | lokaler Keycloak, austauschbarer Firmenadapter | P1-Interop; Firmenbetrieb später |
| Laufzeiten, Bibliotheken und Images | Kandidaten aus Technologiematrix | exakte Pins + Build/Integration am Beginn P1 |
| OpenAI-Modell, Providerpreise und Freigabe | deaktiviert; kein Schlüssel nötig für Kern | vor kostenpflichtigem Live-Test |
| Reale Daten, Aufbewahrung und Incident-Kontakte | keine Produktivdaten | vor realem Betrieb |
| CPU-/Hostunterstützung | Linux amd64/arm64 als Ziel | konkrete Builds/Starts separat nachweisen |
| IHK-Teilprojekt und zeitlicher Umfang | keine erfundene Frist | bei tatsächlichem betrieblichen Auftrag |

Diese Punkte erlauben eine konkrete lokale M1-Umsetzung ohne voreilige Produktivannahmen. Die gemeinsame Durchsicht kann den Entwurf ändern; der vorbereitete [Phase-1-Prompt](prompts/PHASE_1_IMPLEMENTATION_PROMPT.md) übernimmt danach den beschlossenen Stand.

## Tatsächlicher Prüfstand

Die unabhängigen Inhaltsprüfungen und beschriebenen Korrekturen sind erfolgt. Die abschließende Dateivollständigkeits-, Link- und Quellenübernahmeprüfung wird im [Status](STATUS.md) mit ihrem tatsächlichen Ergebnis protokolliert. Keine Anwendungstests, Migrationen, Docker-Builds, Live-KI-Aufrufe oder Deployments wurden als Teil von Phase 0 ausgeführt.
