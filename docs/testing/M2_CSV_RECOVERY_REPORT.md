# M2 — Robuster CSV-Import und Wiederaufnahme

Stand: 12.09.2026. [ADR 0008](../adr/0008-csv-format-und-wiederaufnahme.md).

## Bestätigte Ursachen

Falsche Semikolonvoreinstellung bei gültigen Kommadateien sowie ein unabhängiges Readerlimit von 16.384 Zeichen. Parserfehler waren fälschlich als UTF-8-Fehler ausgegeben. Vollständige strukturelle Prüfung der betroffenen großen Datei: 49.123 Zeilen, 170 Spalten, längste Zelle 175.026 Zeichen, keine abweichende Zeilenbreite. Es wurden keine Zellinhalte in den Nachweis übernommen.

## Bereits erfolgreiche gezielte Prüfungen

- 25 CSV-/Streamingtests: vier Trennzeichen, breite Tabellen, lange Zellen einschließlich Transformation, UTF-16, explizites Windows-1252, BOM, sep-Direktive, fehlende Kopfzeile, Mehrdeutigkeit, Quotierungsfehler und angeschnittener UTF-8-Codepunkt.
- Sechs echte PostgreSQL-Integrationstests: Wiederaufnahme/Idempotenz, unveränderte Originaldatei, erhaltene Fehlerhistorie, bestätigte Transformation und Export; CSRF, Viewer, Fremdmandant; bestehende Visualisierungs- und Versionskonsistenz.
- Strenge mypy-Prüfung über 46 Quelldateien, Ruff, TypeScript-/Vite-Build, Frontend-Formatprüfung und ESLint erfolgreich.
- 14 Frontendtests bestanden.
- Migration 0003 → 0004 in der bestehenden lokalen Datenbank angewendet; API, Web und Worker aktualisiert.

## Reale Originalimporte

Fünf ausdrücklich beauftragte gespeicherte Originaldateien wurden über den normalen authentifizierten API-Pfad erneut eingereiht. Alle fünf sind veröffentlicht: 25 Zeilen / 33 Spalten, 600 Zeilen / 170 Spalten und dreimal 49.123 Zeilen / 170 Spalten. Der vollständige Originaldownload der zuletzt beanstandeten Datei (140.484.689 Bytes) stimmt mit dem gespeicherten SHA-256 überein. Ihr vollständiger CSV-Export enthält 49.123 Zeilen, 170 Spalten und weiterhin die 175.026 Zeichen lange Zelle. Eine zusätzliche unveröffentlichte Trim-Vorschau derselben Datei wurde im regulären begrenzten Worker erfolgreich berechnet.

Der erfolgreiche frühere 1-GiB-Lastlauf wird nicht unnötig wiederholt. Der weiterhin offene vollständige Restore-Abschluss wird durch diese gezielten Prüfungen nicht als bestanden ausgegeben.

## Ergänzende Profiling-Korrektur und Browserabschluss

Das vollständige reale Profiling zeigte vermeidbare wiederholte JSON-Zerlegung für jede Spalte. Profilingversion csv-profile-stream-3 aggregiert mit SQLite json_each einmal gemeinsam und bewahrt genaue Werte sowie die ursprüngliche Gleichstandsreihenfolge. Im synthetischen Vergleich mit 1.000 Zeilen und 170 Spalten: 3,035 → 0,325 Sekunden, fachliche Profile exakt identisch. Dies ist eine begrenzte Vergleichsmessung, keine allgemeine Geschwindigkeitsgarantie. Fortschrittsinformationen gehen zwischen SQLite-Heartbeats nicht mehr verloren.

25 Domänentests und sechs PostgreSQL-Fälle nach dieser Änderung erneut bestanden. Der zweite DB-Lauf arbeitete außerdem wartende Originalimporte ab (166,64 Sekunden); er war deshalb kein isolierter Testlaufzeitvergleich. Die echte große Bearbeitungsvorschau lief anschließend im regulären Worker mit 256 MiB Limit. Strenge mypy-Prüfung über 46 Quelldateien erneut bestanden.

Der neue gezielte OIDC-/Chromium-Fall bestand in 7,4 Sekunden (8,1 insgesamt): falsches Trennzeichen → Fehlermeldung → gespeicherte Originaldatei mit Autoerkennung erneut importieren → Vorschau → bestätigte Version 2 → Export mit vollständigem langem Textfeld. Zunächst fehlte dem Dateifeld ein eindeutig auffindbarer zugänglicher Name; ein explizites aria-label behob diesen Browserbefund. Abschließender Webbuild erfolgreich.

Die Restore-Erwartung wurde wegen des zusätzlichen regulären Browserfalls auf sieben Fälle aktualisiert. Ein vollständiger Restore wurde hier nicht erneut ausgeführt.
