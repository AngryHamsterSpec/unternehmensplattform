# Phase 1 — Der erste vollständige Funktionsablauf

Status: UMSETZUNG AKTIV. Der ausdrückliche Nutzerauftrag hat Phase 1 gestartet. Dieses Dokument enthält Abnahmeanforderungen, keine Implementierungsbehauptung.

## Ergebnis aus Nutzersicht

Eine Person startet die lokale Plattform, meldet sich an, wählt ihre Organisation, erfasst ein Unternehmensszenario und vergleicht begründet passende Architekturpläne. Sie kann jede Zahl und jeden Ausschluss nachvollziehen und das gespeicherte Ergebnis nach Neustart wieder öffnen. Die gesamte Oberfläche spricht Deutsch.

## Lieferumfang

1. Reproduzierbarer Compose-Kern mit Reverse Proxy/SPA, FastAPI, PostgreSQL, lokalem OIDC-Anbieter und kontrolliertem Migrationsschritt. Lockfiles und Imagepins aus verifizierten stabilen Versionen.
2. Reale Anmeldung und Logout, serverseitige Sessions, CSRF, Org-Mitgliedschaften, Rollen und Mandantentrennung; keine Abnahme mit einem Development-Auth-Bypass.
3. Unternehmensszenarien mit unveränderlichen Profilversionen, Anforderungen, Arbeitslasten und Assets. Eingabefehler werden verständlich erklärt; parallele Änderungen führen zu einem sichtbaren Konflikt.
4. Kandidatenpläne über getrennte Service-, Deployment- und Hostingachsen. Mindestens vier dokumentierte Varianten: unterstütztes SaaS-Angebot, Public-PaaS, Public-IaaS und verbundener Hybridplan mit lokalem Anteil.
5. Regelbasierte harte Constraints, nachvollziehbare Gewichte, Kosten-/Leistungsmodus, TCO-Aufteilung, Unsicherheit und Alternativvergleich.
6. Deterministischer Manager, Cost Estimator und unabhängiger Verifier. Deutsche regelbasierte Erklärung als Standard; optionaler OpenAI-Adapter mit eigener Freigabe, konfigurierbarem Modell, Limits und Nachweisen.
7. Persistierte Snapshots, Versionen, Evidenz, Prüfung und Audit. Wiederholte Requests erzeugen keine doppelten Assessments.
8. Sachliche deutsche UI mit Szenarioliste/-formular, Ergebnis, Vergleich, Nachweisen und rollenabhängiger Mitgliederverwaltung.
9. Reproduzierbare synthetische Demo, echte PostgreSQL-Integration, Browser-E2E, negative Sicherheitsfälle, CI und Docker-Nachweise.
10. Verständliche README/EXPLAIN/TESTING-Dateien für implementierte Module und aktualisierter Projektstatus.

Die vollständige Domäne B ist nach M1 noch begrenzt: Demo-Kandidaten und Demo-Kosten sind keine allgemeine kommerzielle Architekturberatung. Eine erfolgreiche M1-Abnahme bedeutet einen echten vollständigen Ablauf innerhalb dieses ausdrücklich beschriebenen Scopes.

## Demo und überprüfbarer Ablauf

Synthetische Organisation „Musterwerk IT“, zweite Organisation „Testmandant B“, Admin/Architektur-Analyst/Viewer. Alle Angaben und Kosten werden als fiktiv gekennzeichnet. Keine Behauptung über eine reale Firma.

Der Reviewer führt aus:

1. Nach Konfiguration Compose bauen/starten; Status und Migrationen kontrollieren.
2. Als Analyst anmelden, Arbeitslasten und Anforderungen speichern, Seite neu laden.
3. Bewertung im Wirtschaftlichkeitsmodus ausführen; Ausschlüsse und Kriterienbeiträge prüfen.
4. Gleiche Profilversion im Leistungsmodus bewerten; Unterschiede nachvollziehen.
5. Preise und 36-Monats-TCO anhand der dokumentierten Demo-Eingaben nachrechnen.
6. Eine erforderliche Angabe entfernen; unvollständiges Ergebnis ohne erfundenen Sieger sehen.
7. Als Viewer lesen; Bearbeitung serverseitig abgewiesen bekommen.
8. Aus Testmandant B direkte IDs, Vergleich und Audit des ersten Mandanten anfragen; keine Daten erhalten.
9. Optionalen Providerfehler auslösen; das gespeicherte Ergebnis bleibt unverändert.
10. Stack neu starten und Daten wiederfinden; Backup in getrennte leere Testdatenbank zurückspielen und dieselben fachlichen Ergebnisse prüfen.

## Grenzen für Implementierung und Tests

Maximal 10 Arbeitslasten und 20 Kandidatenpläne je Assessment. Referenzlast: 10 parallele Nutzer und 100 Szenarien pro Organisation. Ziel p95 Lesen unter 500 ms, deterministische Bewertung unter 2 s; Hardware und Datenumfang mit jeder Messung dokumentieren. Nicht gemessen bedeutet nicht erfüllt.

Optionaler KI-Aufruf maximal 10 Sekunden und null Toolrechte; nicht in den Kernlatenzzielen enthalten. Lange Operationen und die dauerhafte Jobqueue beginnen in M2.

Keine Infrastruktur anwenden, keine fremden Ziele scannen, keine Daten importieren, keine Supportnachrichten versenden. Diese gehören zu späteren spezifizierten Abläufen.

## Abschlussnachweise

[Meilensteinabnahme](testing/MILESTONE_ACCEPTANCE.md), [Teststrategie](testing/TEST_STRATEGY.md) und [SEC-Testkatalog](security/THREAT_MODEL.md) sind die verbindlichen Prüflisten. CI muss tatsächliche Kommandos ausführen und Fehler blockieren; Mocks dürfen weder Datenbank-/Login- noch Browserstrecken der Abnahme ersetzen.

M1 kann mit verifiziertem deterministischem Kern abgeschlossen werden, während der optionale OpenAI-Adapter als NICHT LIVE GETESTET ausgewiesen bleibt. Seine Vertrags-/Fehlerprüfungen müssen dennoch bestehen; ein Live-Erfolg darf erst nach einem ausdrücklich konfigurierten Live-Test behauptet werden.

## Direkt anschließender Arbeitsauftrag

Der [deutsche Phase-1-Prompt](prompts/PHASE_1_IMPLEMENTATION_PROMPT.md) verbindet diese Spezifikation mit dem Master Prompt. Die gemeinsame Durchsicht kann konkrete Anpassungen festlegen; danach wird derselbe Umfang implementiert und durchgängig geprüft.
