# M2 — JSON- und JSONL-Tabellen

Stand: 12.09.2026. [ADR 0009](../adr/0009-json-tabellenimport.md).

## Implementierter Umfang

UTF-8-JSON-Arrays flacher Objekte sowie JSONL werden über den bestehenden Abschnittsupload und begrenzten Worker importiert, profiliert, visualisiert, in Vorschauen transformiert und nach Bestätigung als neue Version gespeichert. Originaldownload und sicherer CSV-Export bleiben verfügbar. source_format begleitet auch abgeleitete Versionen.

Fehlende Schlüssel und null werden in der tabellarischen Ableitung zu leeren Zellen. Numerische JSON-Literale behalten ihre Schreibweise; die bestehende Typinferenz erkennt nur ihr dokumentiertes Dezimalformat. Verschachtelte Werte, doppelte Schlüssel, zusätzliche Spalten nach dem ersten Objekt und Nichtstandardzahlen werden abgewiesen. Originalbytes bleiben die verlustfreie Quelle.

## Gezielte erfolgreiche Prüfungen

- Zwölf JSON-Domänenfälle: lange Zelle über Readerabschnitte hinweg, BOM, fehlende Schlüssel, null, boolesche Werte, umgeordnete Schlüssel, Vorschau/Export, fehlerhafte Strukturen, doppelte Schlüssel, Verschachtelung, Zusatzspalten, Kodierung und Datensatzlimit.
- Gemeinsamer Lauf mit den zwölf CSV-Optionsfällen: 24 bestanden in 1,79 Sekunden.
- Zwei echte PostgreSQL-Fälle für JSON und JSONL: Abschnittsupload → Worker → Profil → Vorschau → Bestätigung → CSV-Export; Originalbytes und Formatkennzeichnung erhalten; Fremdmandant ausgeschlossen. 6,73 Sekunden.
- Ruff, strenge mypy-Prüfung über 47 Quelldateien und TypeScript-/Vite-Build bestanden.
- Autorisierter Quellscan erfolgreich; keine neuen Laufzeitabhängigkeiten hinzugefügt.

14 Frontendtests sowie Prettier und ESLint bestanden. Der gezielte echte OIDC-/Chromium-Ablauf für CSV-Wiederaufnahme und zusätzlichen JSON-Import mit Vorschau, bestätigter Version 2, Originaldownload und CSV-Export bestand in 10,6 Sekunden (11,4 insgesamt). Eine zunächst mehrdeutige Navigation im Test wurde durch exakte Linkauswahl korrigiert; keine Anwendungsänderung dafür nötig.

API, Web und regulärer Datenworker sind mit dieser Erweiterung aktiv. Der Quellscan meldet null Geheimnisse und keine Abhängigkeitsbefunde; seine bekannte Scannerfixture wurde erkannt. Es wurden keine zusätzlichen Laufzeitpakete eingeführt.

## Grenzen

1 GiB ist die gemeinsame zugelassene Uploadgrenze. Kein gesonderter vollständiger 1-GiB-JSON-Lasttest; der frühere vollständige Lastnachweis betrifft CSV. Kein allgemeines Flattening verschachtelter JSON-Dokumente. Kein JSON-Export der bereinigten Version (CSV-Export vorhanden). XLSX, Parquet, Datenbankquellen und Live-KI bleiben offen. Kein erneuter vollständiger Restore- oder Basisimagescan für diesen Adapter.
