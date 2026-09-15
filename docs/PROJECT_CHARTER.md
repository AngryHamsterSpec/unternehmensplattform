# Projektverfassung

Stand: 09.09.2026. Aus dem vollständigen Master Prompt abgeleitete deutsche Arbeitsgrundlage. Status: verbindliche Projektziele; Phase 1 wurde ausdrücklich zur Umsetzung beauftragt.

## Auftrag und Rangfolge

Die Plattform unterstützt Unternehmen beim Verstehen und Verbessern ihrer IT, Daten, Prozesse, Cloud-Kosten und Sicherheit. Sie verbindet prüfbare Fachlogik mit beaufsichtigten Agenten. Sie soll als reales erweiterbares Produkt, Portfolio und verständliche Lerncodebasis dienen.

Es gilt der [vollständige Master Prompt](requirements/MASTER_PROMPT_ORIGINAL.md). Diese Verfassung ersetzt keine Detailanforderungen. Die [Anforderungsmatrix](REQUIREMENTS_TRACEABILITY.md) ordnet alle Abschnitte und Module den Lieferphasen zu. Der [Phase-0-Auftrag](requirements/PHASE_0_PROMPT_ORIGINAL.md) beschreibt den abgeschlossenen Entwurf; M1 wurde gemäß [Phase-1-Auftrag](prompts/PHASE_1_IMPLEMENTATION_PROMPT.md) umgesetzt. Seit der ausdrücklichen Zustimmung am 11.09.2026 ist der [M2-CSV-Auftrag](prompts/PHASE_2_IMPLEMENTATION_PROMPT.md) aktiviert.

Die jüngste Nutzerentscheidung legt **Deutsch** als Projektsprache und die Reihenfolge **Master Prompt → Phase 0 → gemeinsame Durchsicht → Phase 1** fest. Die Empfehlung im Begleittext, auf Englisch zu arbeiten, wird damit ersetzt. Die englischen Originalprompts bleiben lediglich als unveränderte Referenz erhalten; persönliche Angaben aus dem Begleittext werden nicht ins Repository kopiert.

## Engineering-Grundsätze

1. Fachliche Richtigkeit, Sicherheit, Wartbarkeit und verständliche Begründungen bestimmen Entscheidungen.
2. Ein modularer Monolith mit expliziten Verträgen bildet den Anfang. Neue Infrastruktur entsteht aus messbarem Bedarf.
3. Zahlen, Regeln, Autorisierung und Freigaben werden deterministisch geprüft. Sprachmodelle ergänzen Erklärungen.
4. Jede Empfehlung nennt Daten, Evidenz, Versionen, Annahmen, Grenzen und Alternativen.
5. Rohdaten und historische Entscheidungen bleiben reproduzierbar. Änderungen erzeugen Versionen.
6. Mandanten- und Objektberechtigungen gelten für API, Datenbank, Jobs, Dateispeicher, Retrieval und Exporte.
7. Agenten arbeiten hierarchisch, begrenzt und überprüfbar. Ihr Text erteilt niemals Rechte.
8. Externe Seiteneffekte benötigen einen nachvollziehbaren Freigabeablauf. Cloud-Adapter beginnen lesend; Security-Adapter prüfen nur registrierte autorisierte Ziele.
9. Feedback führt über Evaluation und menschliche Freigabe zu einer neuen Version. Produktion verändert sich nicht selbst.
10. Jede implementierte Phase endet mit relevanten Prüfungen, behobenen Fehlern und aktualisiertem Status.

## Gesamter Produktumfang

A Unternehmens- und IT-Erfassung; B Architekturberatung; C Datenintelligenz; D Prozessanalyse; E Cloud, FinOps und Resilienz; F defensives Security Lab; G Agentenplattform; H Agent Factory; I Kundensupport; J kontextbezogene In-App-Hilfe. Alle bleiben Teil des Zielbilds, auch wenn Phase 1 nur A/B und den nötigen Teil von G liefert.

## Sprache und Darstellung

UI, Erklärungen, Dokumentation und fachliche Fehlermeldungen sind deutsch. Codebezeichner, API-Feldnamen und standardisierte Statuswerte bleiben konsistent englisch. Anzeige: de-DE; Datenübertragung: ISO-Zeitwerte mit UTC, explizite Einheiten und Währung. Geldwerte werden ohne binäre Fließkommaarithmetik verarbeitet.

Die Oberfläche ist eine sachliche Arbeitskonsole: verständliche Formulare, Tabellen, Filter, Herkunftsnachweise, Vergleichsansichten, zugängliche Tastaturbedienung und klare Lade-, Fehler- und Leerzustände. KI-Chat ergänzt die Bedienung.

## Ehrlicher Lieferstand

Die Begriffe IMPLEMENTIERT, TEILWEISE IMPLEMENTIERT, EXPERIMENTELL, NICHT IMPLEMENTIERT, BENÖTIGT EXTERNE ZUGANGSDATEN und NICHT LIVE GETESTET werden in [STATUS.md](STATUS.md) geführt. Ein Entwurf ist keine implementierte Schutzmaßnahme. Ein Test-Double ist keine Live-Integration. Keine erfundenen Testergebnisse, Preise, Firmenangaben, Projektstunden oder Eigenleistungen.

## Definition of Done

Ein Fachmodul benötigt relevante Geschäftslogik, Persistenz, Autorisierung, Validierung, API, UI, Fehlermeldungen, Diagnose, Dokumentation und bestandene durchgängige Tests. Ein Reviewer muss die Demo starten, Ergebnisse nach einem Neustart wiederfinden, Entscheidungen erklären und das Modul gezielt verändern können.

Die Gesamtplattform erfüllt diese Definition erst nach allen sieben Zielworkflows und der abschließenden Härtung. Phase 0 erfüllt ausschließlich den Architekturauftrag.
