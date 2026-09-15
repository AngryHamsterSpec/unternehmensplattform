# ADR 0008 — CSV-Formaterkennung und wiederholbare Originalimporte

Datum: 12.09.2026. Status: angenommen und implementiert.

## Auslöser und belegte Ursachen

Mehrere gültige Komma-Dateien scheiterten zunächst an der voreingestellten Semikolonauswahl. Die zusammengezogene Kopfzeile führte zur irreführenden Spaltennamenmeldung. Ein erneuter Import mit Komma scheiterte unabhängig davon am Readerlimit von 16.384 Zeichen je Zelle. Die gemeinsame Fehlerbehandlung für Parser- und Dekodierungsfehler meldete fälschlich ungültiges UTF-8. Die betroffene Datei ist gültiges UTF-8 und enthält eine Zelle mit 175.026 Zeichen.

## Entscheidung

Ein begrenzter Detektor untersucht höchstens 256 KiB. Automatisch werden Komma, Semikolon, Tabulator und senkrechter Strich erkannt, sofern die Struktur eindeutig ist. UTF-8 und UTF-16 mit BOM werden automatisch gelesen; Windows-1252 muss ausdrücklich gewählt werden. Mehrdeutige Formate verlangen eine Auswahl. Explizite Entscheidungen werden nicht still überschrieben. Excel-sep-Direktiven und führende Leerzeilen werden berücksichtigt. Dateien ohne Kopfzeile bekommen auf ausdrückliche Auswahl generierte Namen; ihre erste Datenzeile bleibt erhalten.

Zellen dürfen bis 1.048.576 Zeichen enthalten; Originaldateien weiterhin bis 1 GiB. Die 4-MiB-Grenze je normalisiertem Datensatz und die Worker-/Speicherlimits bleiben wirksam. Anzeigen kürzen Werte; Original, Transformation und Export bewahren sie vollständig innerhalb der dokumentierten Grenzen. Parser-, Kodierungs-, Spalten- und Größenfehler erhalten getrennte deutsche Meldungen.

Migration 0004 speichert unveränderliche Leseoptionen je Importauftrag. Wiederholung liest dieselben Originalbytes und erzeugt einen neuen auditierten Auftrag. Fehlgeschlagene Historien werden nicht überschrieben. Ein aktiver gleicher Auftrag wird idempotent zurückgegeben; abweichende Optionen oder bereits veröffentlichte Versionen ergeben einen Konflikt. Rollen, CSRF, RLS und Quoten gelten unverändert.

## Einordnung in die Agentenplattform

Formatbestimmung, Validierung, Transformation und Veröffentlichung bleiben deterministisch. Ein späterer Data Manager darf typisierte Vorschläge liefern; weder Agententext noch Dateiinhalte erteilen Schreibrechte. Der erneute Import nutzt denselben überwachten Worker und dieselbe Publikationsgrenze, keinen zweiten KI- oder Dateipfad.

## Grenzen und Nachweis

Kein stilles Reparieren beschädigter CSVs, kein Umbenennen von XLSX in CSV, kein verlustbehaftetes Ersetzen ungültiger Zeichen. Weitere Eingabeformate erhalten eigene Adapter gemäß M2. Prüfungen und reale Wiederaufnahme: [Prüfbericht](../testing/M2_CSV_RECOVERY_REPORT.md).

## Gemessene Erweiterung

Breite reale Dateien machten wiederholte JSON-Zerlegung je Spalte teuer. Profilingversion csv-profile-stream-3 berechnet deshalb die exakten Häufigkeiten einmal gemeinsam in einer dateibasierten SQLite-Aggregation. Sortierung bei gleicher Häufigkeit bleibt durch die erste Zeilenposition bestimmt. Fortschrittsmeldungen werden vor dem Heartbeat-Throttling vorgemerkt.
