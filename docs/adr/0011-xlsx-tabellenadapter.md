# ADR 0011 — Kontrollierter XLSX-Tabellenimport

Datum: 12.09.2026. Status: implementiert und lokal geprüft.

Der nächste M2-Adapter liest ein ausdrücklich gewähltes Arbeitsblatt (Nummer ab 1, Standard erstes Blatt). openpyxl 3.1.5 im Lesemodus verarbeitet Zeilen und erhält Excel-Datums-/Booltypen. defusedxml 0.7.1 schützt die XML-Verarbeitung. Beide sind exakt gepinnt. Keine neue Jobplattform, kein Excel-Prozess und keine Makroausführung.

Vor dem Lesen werden ZIP-Inhalt, Anzahl, Pfade, Verschlüsselung und entpackte Größen geprüft. Tabellen-XML bleibt dateibasiert; sharedStrings und andere im RAM gelesene Metadaten erhalten separate Grenzen. Ausgeblendete Arbeitsblätter, Makro-/eingebettete Objekte und externe Verknüpfungen werden abgewiesen. Formelzellen werden ausdrücklich zurückgewiesen: gespeicherte Cachewerte können veraltet sein; die Plattform rechnet Excel-Formeln nicht nach. Zellwerte als Werte exportieren ist der dokumentierte Importweg.

Das Original bleibt vollständig unverändert. Leere Zellen werden leere Stringzellen, Zahlen werden deterministisch als Text übertragen, Excel-Daten als ISO-Datum/-Zeit. Formatierung und zusammengeführte Zellen sind keine Tabellenwerte; nur der tatsächliche Wert einer Zelle wird übernommen. Falsch deklarierte Blattdimensionen dürfen Daten nicht still abschneiden; Spaltenbreite wird aus tatsächlich gelesenen Zeilen geprüft. Dieselbe Profil-, Vorschau-, Freigabe- und Exportpipeline gilt.

ImportOptions erweitert die vorhandenen CSV-Leseoptionen um die Blattnummer; Original-/Auftragsmetadaten bleiben unveränderlich. Profile dokumentieren Format und Blattnummer. KI-/Agentenrechte verändern sich nicht.

Quellen: [openpyxl](https://pypi.org/project/openpyxl/), [Leseoptionen](https://openpyxl.readthedocs.io/en/stable/tutorial.html). Weitere Formate wie XLS/ODS, Makros, Passwortdateien, automatische Formelberechnung und kombinierte Mehrblattimporte bleiben außerhalb dieses Adapters.
