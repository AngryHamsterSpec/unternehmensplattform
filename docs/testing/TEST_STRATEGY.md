# Teststrategie

Stand: **9. September 2026**. Status: **Planung; keine Anwendungstests implementiert oder ausgeführt**.

Das wichtigste Qualitätsmerkmal ist ein nachvollziehbarer Ablauf vom angemeldeten Benutzer über eine tatsächlich gespeicherte Anforderung zur geprüften Entscheidungsrechnung und zur deutschen Vergleichsansicht. Tests sichern fachliche Eigenschaften, Berechtigungen und Ausfallverhalten ab. Sie dienen nicht dazu, durch viele gleichartige Assertions eine umfangreiche Implementierung vorzutäuschen.

## Teststufen und Belege

| Stufe | Was sie beweist | Vorgesehene Mittel | Umgebung |
| --- | --- | --- | --- |
| Statische Prüfung | Syntax-/Typfehler, unzulässige Modulabhängigkeiten, inkonsistenter Stil | Ruff, mypy, TypeScript, ESLint; genaue Versionen vor P1 prüfen | Ohne externe Zugangsdaten |
| Domänentests | Regeln, Gewichtung, Ausschlussbedingungen, Kosten, Versionsbindung | pytest, Tabellenfälle, gezielt Hypothesis | Ohne DB oder KI |
| Verträge | DTOs, API-Schema, Agenten-/Tool-Ein- und Ausgaben, Providerfehler | Pydantic-Schemas, OpenAPI-Differenz, unabhängige Vertragsszenarien | Deterministischer Provider |
| PostgreSQL-Integration | Transaktionen, Fremdschlüssel, Migration, RLS, Rollen, Parallelität | Reales PostgreSQL der gesperrten Version | Frische isolierte Datenbank |
| Auth-/API-Integration | OIDC, Sitzungen, CSRF, RBAC, Mandantengrenzen, HTTP-Semantik | Echter lokaler IdP für Integrationsfälle; kontrollierter IdP nur für gezielte Fehler | Compose-Testumgebung |
| UI-Komponenten | Formulareingaben, Tastaturverhalten, Berechnungsanzeige, Fehlerzustände | Vitest und geeignete Testing-Library | Typisierte API-Fixtures |
| Browser-Ende-zu-Ende | Realer fachlicher Hauptablauf über Proxy, IdP, API und DB | Playwright | Gebaute Demo-/Testimages |
| Betrieb/Sicherheit | Start, Restore, Ausfälle, Geheimnisse, Abhängigkeiten, Container | Compose, Scanner, begrenzte Fehler- und Lastszenarien | Isolierter Testbetrieb |
| Live-KI-Evaluation | Tatsächliche Anbieterkompatibilität, Belegtreue, Budget und Latenz | Explizit gestarteter gesonderter Workflow | Nur synthetische Daten und freigegebenes Testgeheimnis |

Die Integration ersetzt keine Datenbank durch SQLite. Browser-E2E darf den zu prüfenden Hauptworkflow nicht durch einen abgefangenen API-Aufruf vortäuschen. Komponentenfixtures und deterministische KI-Doubles sind erlaubt, müssen aber als solche bezeichnet werden. Ein Testbericht nennt Commit, Umgebung, Versionen, Kommando, Zeitpunkt, Exitcode und gespeicherte Belege.

## Reproduzierbare Testdaten

Mindestens zwei vollständig getrennte synthetische Mandanten, identische sichtbare Szenarionamen und jeweils Administrator, Analyst und Viewer verhindern Tests, die nur aufgrund unterschiedlicher Namen bestehen. Weitere Rollen kommen mit ihren Modulen hinzu. Benutzeridentitäten werden über Issuer und Subject gebunden, nicht allein anhand einer E-Mail-Adresse.

Versionierte Szenarien repräsentieren ein kostenorientiertes kleines Unternehmen, ein leistungsorientiertes Technikunternehmen, eine Organisation mit strengen Datenanforderungen, Fertigung, Cloud-Native und Legacy-Hybrid. Es sind **erfundene Testorganisationen**. Preise sind entweder klar bezeichnete synthetische Testwerte oder belegte/versionierte Eingaben; sie erscheinen nicht als aktuelle Marktpreise.

Für jeden fachlichen Referenzfall werden Eingaben, Regeln, Ausschlüsse, Gewichte und erwartete Zwischensummen unabhängig vom getesteten Produktionspfad beschrieben. Zufallsbasierte Tests speichern den fehlgeschlagenen Seed bzw. Gegenbeispielwert. Uhrzeit, Zufall, IDs und KI-Antworten sind kontrollierbare Abhängigkeiten. Ein bloßer Snapshot einer automatisch erzeugten großen Antwort reicht nicht als fachlicher Beweis.

## Deterministische Entscheidungsrechnung

Folgende Eigenschaften sind Phase-1-Pflicht:

- Identische validierte Eingaben, Regelversion, Preisgrundlage und Gewichtung ergeben identische Werte und eine stabile Reihenfolge. Darstellungssprache und UI-Sortierung verändern die Rechnung nicht.
- Geld verwendet Dezimalarithmetik mit dokumentierter Währung, Einheit, Rundung und Betrachtungszeitraum. CAPEX wird nicht versehentlich jeden Monat erneut gezählt; OPEX wird nicht als Einmalpreis behandelt.
- Zulässige normalisierte Gewichte summieren sich gemäß Vertrag; negative, nicht endliche und vollständig null gesetzte Gewichte werden abgewiesen. Grenzen und extreme gültige Eingaben lösen keinen Überlauf oder `NaN` aus.
- Ein hartes Ausschlusskriterium kann nicht durch einen hohen weichen Score überstimmt werden. Sind alle Alternativen ausgeschlossen, entsteht „keine geeignete Alternative“ mit Gründen.
- Unbekannte Kriterien oder fehlende Preise werden nicht als null Kosten bzw. Bestwert behandelt. Unvollständige Evidenz und nicht vergleichbare Kosten werden sichtbar ausgewiesen.
- Ein Gleichstand bleibt ein Gleichstand; technische Sortierregeln werden offengelegt. Die Reihenfolge der Eingabekriterien darf das Ergebnis nicht verändern.
- Gewichtung mit einem gemeinsamen positiven Faktor verändert bei normierter Berechnung das Ergebnis nicht. Steigt nur ein positiv gewichteter Nutzenwert einer weiterhin zulässigen Alternative, darf ihr eigener Score nicht sinken. Solche Eigenschaften werden nur dort angewandt, wo die definierte Formel sie tatsächlich garantiert.
- Kostensteigerung einer einzelnen Kostenposition darf bei ansonsten identischen Mengen, Preisen und Zeiträumen deren TCO nicht verringern. Mengen-/Einheitenumrechnung erhält den wirtschaftlichen Wert.
- Ergebnis und Empfehlung bleiben an die bewertete Szenarioversion gebunden. Eine nachträgliche Bearbeitung schreibt vergangene Ergebnisse nicht um.
- „Konfidenz“ ist keine erfundene statistische Wahrscheinlichkeit. Verwendete Vollständigkeits-/Evidenzindikatoren und Sensitivitätsanalyse müssen ihrer benannten Bedeutung entsprechen.

Die Ergebnisse des Managers werden zusätzlich durch den Verifier auf Eingabe-/Versionsbindung, Rechenintegrität, Zulässigkeit und Quellenbezug geprüft. Fehlerhaft manipulierte Kandidatenergebnisse müssen scheitern. Der Verifier darf nicht lediglich das vom Manager gesetzte Feld `verified=true` übernehmen.

## Authentifizierung und Mandantentrennung

Verbindliche Sicherheits-IDs und konkrete Assertions stehen im [Threat Model](../security/THREAT_MODEL.md). Für Phase 1 gelten **SEC-01 bis SEC-12 sowie SEC-20 bis SEC-22**. Die folgenden Prüffamilien operationalisieren diese Anforderungen; sie erzeugen keine zweite konkurrierende ID-Liste.

| Prüffamilie | Positivfall | Erforderliche Negativfälle |
| --- | --- | --- |
| OIDC | Echter Login über Proxy erzeugt serverseitige Sitzung | Falscher Issuer/Audience, fehlender oder falscher State/Nonce, Code-Replay, falscher Redirect, abgelaufene Signatur-/Tokenbasis; kein erfolgreicher Login bei fehlgeschlagener Prüfung. |
| Sitzung/CSRF | Berechtigter Benutzer ändert eigenes Szenario mit gültigem CSRF-Nachweis | Fremder Origin, fehlender/falscher CSRF-Nachweis, abgelaufene/widerrufene Sitzung, Session-Fixation; kein Token in LocalStorage oder Log. |
| RBAC | Analyst bearbeitet, Viewer liest | Viewer schreibt direkt per API; UI-ausgeblendete Aktion bleibt serverseitig gesperrt. Rollenänderung wirkt auf bestehende Sitzungen nach dokumentierter Regel. |
| Objektzugriff | A liest und bewertet A-eigenes Szenario | B-ID in Pfad, Query, JSON, Vergleichsliste und verschachtelter Referenz; keine fremden Inhalte oder Metadaten. |
| Listen/Export | Paginierte Liste und Vergleich enthalten nur freigegebene A-Daten | Filter, Sortierung, Zähler, Suchtreffer, spätere Exporte/Downloads und Fehlermeldungen verraten keine B-Daten. |
| RLS | Laufzeitrolle mit gültigem Transaktionskontext liest A | Fehlender Kontext liefert keinen Zugriff; A-Kontext liest/schreibt B nicht; Insert/Update mit fremdem Tenant scheitert. Die Laufzeitrolle besitzt weder `BYPASSRLS` noch Eigentümerrechte. |
| Pool/Nebenläufigkeit | Viele A-/B-Anfragen korrekt getrennt | Derselbe wiederverwendete Connection-Pool wechselt A/B nach Commit, Rollback, Fehler und Cancellation; kein Kontext bleibt erhalten. |
| Relationen | Kind und Elternobjekt gehören demselben Tenant | Manipulierter Fremdschlüssel verbindet keine A-Bewertung mit B-Szenario; Integrität gilt auch für direkte SQL-Integrationstests. |
| Auth-Bootstrap | `platform_auth` findet berechtigte Sitzung/Mitgliedschaft | Auth-Rolle liest keine Fachtabelle; App-Rolle erhält nicht die privilegierte Auth-Verbindung. Tenant aus freiem Header wird nicht als Berechtigung behandelt. |
| Audit/Diagnose | Berechtigter Reviewer sieht erlaubte Zusammenfassung | Viewer liest keinen fremden Trace; manipulierte Nutzdaten injizieren keine Logzeilen; Laufzeitrolle ändert keine bestehenden Auditereignisse. |

Ein bestandener Filtertest unter der Migrationsrolle zählt nicht als RLS-Nachweis. Die Suite prüft die tatsächlichen DB-Rollen und vergleicht Rechte gegen die Sollmatrix. Tests müssen auch die übergreifenden Authentifizierungstabellen und deren eng begrenzte Zugriffsfunktionen einbeziehen.

## Agenten, KI und menschliche Freigaben

Phase 1 verwendet einen deterministischen Supervisor/Manager, Cost Estimator und Verifier. Deren Namen bedeuten keine Pflicht zu mehreren LLM-Aufrufen. Routing, Verantwortungsgrenzen, erlaubte Werkzeuge, Schemafehler, Timeouts und Auditbezug werden als Verträge getestet. Read-only-Rollen bekommen keine schreibenden Werkzeuge; unbekannte Toolnamen werden abgewiesen.

Eine optionale KI-Erklärung ist ein **gesonderter, nachgelagerter Request**. Sie darf keine Bewertung verändern und erhält keine Tools. Tests erzwingen ein globales Zeitbudget von zehn Sekunden ohne automatische Wiederholung, ungültiges JSON, fremde Evidenz-IDs, erfundene Preise, widersprüchliche Scoreangaben, verweigerte Antwort, leere Ausgabe und Anbieterfehler. Der gespeicherte deterministische Bericht bleibt in allen Fällen abrufbar. UI und API kennzeichnen die fehlende Erklärung korrekt.

Zusätzlich werden Erklärung-Doppelklicks, parallele identische Aufträge, Crash nach Reservierung, unklarer Providerausgang und konkurrierende Budgetreservierungen geprüft. Sie erzeugen keine automatische zweite Abrechnung; unklare Reservierungen werden nicht als kostenlos freigegeben.

Die reguläre CI verwendet einen expliziten deterministischen Provider; ein versehentlich konfigurierter echter API-Schlüssel darf keinen Live-Aufruf auslösen. Erlaubte Fixtures prüfen Eigenschaften und Schema, keine zufällige exakte Prosa. KI-Evaluation misst später Routing, Werkzeugwahl, Belegtreue, unbelegte Behauptungen, Berechtigungsverstöße, Schemaquote, Kosten, Latenz und sichere Fehlerbehandlung. Kritische Berechtigungsverstöße dürfen nicht in einem guten Durchschnittswert verschwinden.

Der optionale Live-Workflow benötigt manuellen Start, explizite Aktivierung, synthetischen Evaluationssatz, Anbieter-/Modellkonfiguration, Budgetobergrenze und ein gesondertes Testgeheimnis. Er läuft nicht in ungeprüftem Fork-/PR-Code. Ein fehlender Schlüssel führt zu „übersprungen – externe Zugangsdaten erforderlich“, nicht zu „bestanden“. Vor öffentlicher Behauptung, ein konkreter Live-Adapter funktioniere, muss dieser mit dokumentiertem Modell-/SDK-Stand durchlaufen sein. Die deterministische P1-Abnahme ist davon unabhängig.

Der erste Slice führt keine externen schreibenden Aktionen aus. Deshalb wird in P1 die grundsätzliche Ablehnung solcher Aktionen geprüft; die vollständige langlebige Approval-Engine wird erst mit ihrem ersten tatsächlichen Anwendungsfall implementiert. Für die späteren Zustände `PLAN → REVIEW → APPROVE → APPLY` bzw. die Agentenfreigabe sind bereits jetzt folgende Abnahmefälle festgelegt:

- Freigabe ist an Tenant, Akteur, konkrete Ressourcen, kanonischen Inhaltshash, Version, Gültigkeitsfenster und eindeutige Aktions-ID gebunden.
- Geänderter Plan, geänderte Agentenrechte, abgelaufene Freigabe, fremder Tenant oder widerrufene Rolle verhindern Apply.
- Wiederverwendung derselben Freigabe und zwei parallele Apply-Aufrufe erzeugen höchstens einen autorisierten Effekt; doppelter Aufruf liefert nachvollziehbaren Status.
- Crash vor Wirkung, nach Wirkung vor Bestätigung und bei Wiederholung werden mit einem idempotenten Adapter bzw. Abgleich gegen das Zielsystem behandelt. „Exactly once“ wird nicht ohne Nachweis versprochen.
- Nutzerablehnung und Widerruf bleiben auditierbar; Agent oder Modell kann keine menschliche Freigabe selbst herstellen.

Diese späteren Replay-/Race-Tests werden bei M4 bzw. M7 Pflicht, sobald entsprechende Aktionen existieren. Die Risiken SEC-13 bis SEC-19 werden mit den zugehörigen Modulen aktiviert.

## Fehler- und Wiederanlauftests

| Eingespritzter Fehler | Erwartetes Verhalten | Erste Pflichtphase |
| --- | --- | --- |
| PostgreSQL vor Start nicht verfügbar | Endliche Wartezeit, keine erfolgreiche Bereitschaft | P1 |
| Migration schlägt fehl | Anwendung und Seed werden nicht freigegeben; verständliche Diagnose | P1 |
| DB-Verbindung bricht vor Commit ab | Keine Erfolgsmeldung/Teilbewertung; Wiederholung mit Idempotenzschlüssel bleibt konsistent | P1 |
| DB-Commit erfolgreich, HTTP-Antwort verloren | Wiederholung erstellt keine zweite identische Bewertung | P1 |
| IdP nicht erreichbar | Login scheitert sicher; keine Auth-Umgehung | P1 |
| Frontend-API-Timeout | Ladezustand endet, Eingaben bleiben erhalten, verständlicher Wiederholungsweg | P1 |
| KI-Timeout, Rate Limit oder defekte Ausgabe | Kernbewertung bleibt verfügbar; Erklärung als fehlgeschlagen markiert | P1, falls optionaler Adapter enthalten |
| Gleichzeitige Änderung des Szenarios | Optimistische Versionsprüfung verhindert stilles Überschreiben | P1 |
| Worker stirbt, Auftrag wird abgebrochen | Definierter Lease-/Cancel-Zustand, keine doppelte Wirkung | M2 |
| Defekte/überdimensionierte Datei, ZIP-Bombe, Speicher voll | Frühe Grenzen, sicherer Abbruch, Original-/Metadatenzustand konsistent | M2 |
| Redis fällt aus | Dokumentiertes Degradations-/Retry-Verhalten | Erst wenn Redis tatsächlich eingeführt wird |
| Cloudanbieter 429/403/Timeout | Begrenztes Retry, überprüfbare Teilabdeckung, kein erfundenes vollständiges Inventar | M4 |
| Scanner hängt, Ziel wechselt IP/Redirect | Prozess beendet, Scope erneut geprüft, keine Freigabe fremder Ziele | M5 |
| Veraltetes/vergiftetes Retrieval | Quellen- und Rechteprüfung, Unsicherheit bzw. Eskalation | M6 |

## Ende-zu-Ende-Abnahme und Leistung

Der P1-Browserfall startet an einem frischen Stack, meldet einen echten Demo-Benutzer an, legt zwei Szenarien an, verändert Gewichte, führt eine Bewertung aus, sieht geprüfte Alternativen/Kostenhinweise und ruft das Ergebnis nach Reload und Containerneustart wieder ab. Anschließend beweisen ein Viewer und ein zweiter Mandant die negativen Grenzen. Tastaturbedienung, Formularfehler, Fokusführung und nicht ausschließlich farbcodierte Ergebnisse gehören dazu.

Als **vorläufiges Messprofil**, nicht als gemessene Produkteigenschaft, gelten: 100 Szenarien je Organisation und zehn gleichzeitige Nutzer. Eine Bewertung umfasst höchstens zehn Workloads und 20 vollständige Kandidatenpläne. Diese fachlichen Grenzen werden validiert; ein höherer Wert darf keine unkontrollierte Berechnung auslösen. Das konkrete Referenzsystem mit CPU, RAM, Betriebssystem und Containerlimits wird vor der Messung protokolliert. P1 misst warme Listen-/Detailaufrufe und die kurze deterministische Bewertung; vorgeschlagene Zielwerte sind p95 unter 500 ms bzw. unter 2 s bei diesem Profil, ohne IdP-Login und optionale KI. Datengröße, Wiederholungen, Fehlerquote und Rohdaten werden dokumentiert. Können diese Bedingungen nicht bereitgestellt werden, bleibt das Leistungs-Gate offen. Werte werden erst nach Baseline-Messung verbindlich angepasst, nicht nachträglich als ursprüngliche Zusage ausgegeben.

Ab M2 erhalten Upload-/Profiling-/Exportpfade eigene Größen- und Speicherbudgets. Große Daten werden nicht im Webprozess oder Browser vollständig geladen. Ab M8 kommen längere Last-/Wiederanlauftests; bekannte Grenzen werden vorher schon dokumentiert.

## CI, Sicherheitsprüfungen und Freigabe

Geplante GitHub-Actions-Prüfungen: Format/Lint/Typen, Domäne/Verträge, PostgreSQL-/OIDC-Integration, Frontendkomponenten, SPA-/Dockerbuild, wichtiger Browserworkflow, Abhängigkeitsprüfung, Geheimnissuche, SBOM und Containerscan. Fremde Actions werden bei Umsetzung auf einen überprüften Commit festgelegt. Caches enthalten keine Geheimnisse und dürfen gesperrte Abhängigkeiten nicht umgehen.

Konkrete Scanner werden nach Wartungs-/Lizenzprüfung ausgewählt; mögliche Werkzeuge sind pip-audit, npm audit, Bandit/Semgrep und Trivy. Ein nicht erreichbarer Advisory-Feed gilt als „Prüfung unvollständig“. Eine neue relevante kritische/hohe Lücke blockiert die Freigabe, bis sie behoben oder nachvollziehbar mit Verantwortlichem, Begründung und Ablaufdatum bewertet wurde. Eine hohe Testabdeckung ersetzt keine fehlenden Sicherheitsfälle.

Jeder Meilenstein erhält Architektur-, Sicherheits-, Daten-, QA-, Betriebs- und Wartbarkeitsreview. Befunde werden vor Abnahme behoben oder offen mit Auswirkung dokumentiert. Es gibt keine Pflicht zu einer willkürlichen globalen Coverage-Prozentzahl; für Decision Engine, Autorisierung, RLS und Approval-State-Machine sind relevante Verzweigungen und negative Fälle nachweislich abzudecken. Gezielte Mutationen manipulierter Scores oder ausgelassener Tenantprüfung prüfen bei Bedarf die Aussagekraft der Tests.

Nicht ausgeführte Tests und fehlende Infrastruktur werden immer getrennt von bestandenen Tests geführt. Die tatsächlichen Abnahmekriterien und der Status stehen in [MILESTONE_ACCEPTANCE.md](MILESTONE_ACCEPTANCE.md) und [STATUS.md](../STATUS.md).
