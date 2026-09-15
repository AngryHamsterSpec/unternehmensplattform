# Entscheidungen und Datenfluss

## Upload und Herkunft

Die Oberfläche verwendet POST /data-uploads, wiederholbare PUT-Abschnitte und POST /complete. Die API prüft Sitzung, CSRF, Schreibrechte, Mandant, Reihenfolge, deklarierte Größe und Speicherquote. Für jeden Abschnitt wird SHA-256 gespeichert. Eine Wiederholung mit identischem Inhalt ist idempotent; abweichender Inhalt oder eine Lücke wird abgelehnt.

Abschließen liest alle Abschnitte mit begrenztem Speicher und prüft die Gesamt-SHA-256. Währenddessen bleibt keine lange Schreibtransaktion offen. Erst anschließend werden Objektversiegelung, Originalverweis, Datensatz, Importauftrag und Audit atomar veröffentlicht. Derselbe Abschluss liefert denselben Auftrag. Der Dateiname ist Metadatum, niemals ein Dateisystempfad.

data_objects und data_chunks haben FORCE RLS und zusammengesetzte Mandanten-Fremdschlüssel. Versiegelte Objekte und deren Abschnitte schützt die Datenbank gegen Änderung und Löschung. Offene Uploads können kontrolliert abgebrochen werden. Das alte Base64-API bleibt ausschließlich als kleiner Kompatibilitätsweg erhalten.

## Verarbeitung ohne vollständige Tabelle im RAM

Ein kurzer Claim setzt RUNNING, Lease-Token und 90 Sekunden Laufzeitberechtigung. Der Worker erneuert sie ungefähr alle zwei Sekunden und prüft erneut die aktuellen Schreibrechte. Abgelaufene Claims können übernommen werden; nach drei unterbrochenen Versuchen wird der Auftrag FAILED. Nur der aktuelle, noch gültige Token darf das Ergebnis veröffentlichen. Abbruch setzt CANCELLED und verhindert auch dann eine Version, wenn ein alter Prozess kurz weiterrechnet.

Quelldateien werden abschnittsweise auf das temporäre Arbeitsvolume kopiert und nochmals vollständig gehasht. Der CSV-Parser erhält begrenzte physische/logische Datensätze, prüft UTF-8, Kopfzeilen, Rechteckigkeit, Zellgrößen und Steuerzeichen. Leere physische Zeilen bleiben als leere Datenzeilen erhalten.

SQLite speichert kanonische JSON-Zeilen auf dem Arbeitsvolume, mit 8 MiB Cache und dateibasierter Sortierung. Verschiedene Werte, Häufigkeiten und zusätzliche identische Zeilen werden exakt über sämtliche Datensätze berechnet. Minima, Maxima und Mittelwerte verwenden Decimal. Konservative Typprüfung erhält führende Nullen, Dezimalkomma und Exponentialschreibweisen als Text. Das Verfahren csv-profile-stream-2 berechnet keine Ausreißer; die Oberfläche erklärt dies. Vorschauwerte werden begrenzt, die gespeicherten Daten bleiben vollständig.

Technische Unterbrechungen lassen die Lease auslaufen. Fach-/Berechtigungsfehler werden datenarm FAILED. Normale Fehler und Abbruch entfernen unveröffentlichte Objekte des aktuellen Versuchs und temporäre Dateien. Ein harter Prozessabbruch kann Arbeitsdateien oder offene Ableitungen hinterlassen; administrative Bereinigung dieser verwaisten Reste ist noch ein Betriebs-Ausbauschritt. Die Speicherquote begrenzt weitere Aufnahme.

## Transformation und Freigabe

Bis zu zehn deklarative Schritte bearbeiten Zeilen in sichtbarer Reihenfolge. SQLite-Tabellen je Deduplizierungsschritt erhalten die genaue Semantik auch bei späterer Groß-/Kleinschreibung. SQL, Python und Shellbefehle sind keine Eingabeformate.

Ein vollständiges Vorschauergebnis wird vor Bestätigung als indizierte JSONL-Abschnitte samt sicherem CSV-Export gespeichert. Seitenabfragen lesen nur passende Abschnitte und liefern höchstens 25 Zeilen. Auftrags-ID, Ergebnis-Hash und erwartete Version binden die Bestätigung an das geprüfte Resultat. Organisations-/Datensatzlocks schützen Rechteänderung und Versionsnummer. Wiederholte Bestätigung ist idempotent; veraltete Vorschauen erzeugen einen Konflikt.

## Export, Bestand und Restore

Der Worker erzeugt CSV mit UTF-8-BOM, Semikolon, vollständigem Quoting und Apostroph vor gefährlichen Formelpräfixen. Original-, Versions- und Export-Hashes sind absichtlich verschieden. Downloads streamen versiegelte Abschnitte mit bekannter Länge und Prüfsumme direkt an den Browser. Originale erhalten die Endung .csv.txt.

Migration 0003 erweitert den Bestand additiv. Alte Blobs und csv-profile-1/csv-transform-1-Versionen bleiben lesbar und werden nicht neu berechnet. Sämtliche Original-/Ergebnisabschnitte liegen in PostgreSQL; ein Datenbank-Backup enthält daher auch große Dateien. Das Arbeitsvolume enthält keine alleinige Kopie veröffentlichter Daten.

Ein späterer S3-Adapter muss dieselben Mandanten-, Hash-, Versiegelungs-, Veröffentlichungs- und Wiederherstellungsregeln erfüllen. 1 GiB Dateigröße bedeutet hier Verarbeitung auf einem begrenzten lokalen Worker; horizontale Big-Data-Verteilung ist noch offen.


## Warum eine begrenzte Diagrammauswahl?

Eine 1-GiB-Datei darf nicht zur Darstellung vollständig in den Browser geladen werden. Balken/Ring und Spaltenqualität greifen daher auf das bereits über alle Zeilen berechnete Profil zu. Histogramme und Koordinatendiagramme lesen eine begrenzte systematische Auswahl. Diese kann verzerrt sein und wird sichtbar als solche bezeichnet. Eine spätere genaue Analyse benötigt Hintergrundaggregate, keine größeren Browserarrays.

Die Auswahl liest Abschnittsmetadaten unter RLS, wählt höchstens zwölf Positionen und prüft jeden gelesenen Abschnitt gegen seinen SHA-256. Jeweils zwei Spalten und Originalzeilennummern werden zurückgegeben. Kurze Transaktionen, endliche Antwortgröße und unveränderte Versionen erlauben wiederholbare Ansichten. Bei Fremdmandant, ungültiger Spalte oder Integritätsfehler liefert die API einen Fehler; ein Versionswechsel verwirft die alte Ansicht.

Beim Datensatzdetailabruf verhindert eine geteilte Kopfzeilensperre die Veröffentlichung zwischen Kopf- und Versionsabfrage. Ohne diese Sperre konnte die UI die neue Version mit einer alten aktuellen Versionsnummer erhalten und ihre Bereinigungsaktionen ausblenden.

## CSV-Detektor und Importversuche

csv_format.py prüft eine begrenzte Probe, stream_engine.py validiert anschließend jede Zeile. Ein eindeutiger Vorschlag ersetzt keine explizite widersprechende Auswahl. Ein Importversuch besitzt unveränderliche import_options; das Ergebnisprofil dokumentiert erkannte Kodierung, Trennzeichen und Kopfzeilenmodus. retry-import fügt einen neuen Auftrag mit identischen Originalbytes hinzu. Fehlerhistorien bleiben auditierbar. Spätere Agentenvorschläge müssen dieselben typisierten Prüf- und Bestätigungswege nutzen.

## JSON-Eingabeadapter

json_format.py liest einzelne begrenzte Objekte, liefert eine Kopfzeile und anschließend Stringzellen an stream_engine.py. Zahlen behalten ihre JSON-Schreibweise. Der Originalblob speichert das zugelassene Format; source_format im Profil erhält die Herkunft auch bei Vorschauen. CSV-spezifische Leseoptionen werden nur vom CSV-Adapter ausgewertet. Es entstehen keine weiteren Agentenrechte, Shelltools oder alternativen Veröffentlichungswege.

## XLSX und Agentenverträge

xlsx_format.py prüft das ZIP-Zentralverzeichnis vor dessen Speicherallokation. Eine abschnittsweise SAX-Vorprüfung verhindert DTD/Entitäten, übergroße XML-Tokens und Zellen sowie problematische Adressen. Heartbeats bleiben auch während dieser Prüfung aktiv; Abbruch/Rechteentzug können den Auftrag beenden. openpyxl arbeitet anschließend read_only, data_only=False und keep_links=False, mit defusedxml. Unzutreffende Blattdimensionen schneiden Daten nicht ab.

ImportOptions erweitert CsvOptions um worksheet. Importjobs speichern diese Auswahl unveränderlich. DataProfile führt source_format=xlsx und source_worksheet; der Worker überträgt die Herkunft in nachfolgende Versionen. Reale Zellen werden in die bestehende begrenzte Stringtabellen-Pipeline überführt. Formeln werden vor einer Veröffentlichung zurückgewiesen, keine ungesicherten Cachewerte verwendet.

Die spätere Hierarchie Supervisor → Domänenmanager → Spezialisten bleibt auf diese deterministischen Tools angewiesen. Eine Agentenantwort wird weder Importformat noch Berechtigung noch Freigabequelle. Die Erweiterung fügt keine ungenutzte Agentenlaufzeit hinzu.

## Parquet-Adapter

parquet_metadata.py prüft den größenbegrenzten Dateifuß mit Apache Thrift 0.24.0. Container-/Stringlängen, Komplexität, Tiefe und die in Thrift begrenzten Varints schützen diese Vorprüfung. Sie kontrolliert Schema, Zeilen-/Größenkonsistenz und Seitenpositionen innerhalb der Originaldatei. Metadaten sind weiterhin nicht vertrauenswürdig; der native Reader und das Workerlimit bleiben zusätzliche Grenzen.

parquet_format.py lädt Polars 1.44.2 erst bei Verwendung. Jede freigegebene Zeilengruppe wird synchron gelesen; je 64 Zeilen erfolgt die Stringumwandlung. Große Ganzzahlen und Dezimalwerte durchlaufen keinen Python-Float. Gruppen und Sichten werden vor dem nächsten Gruppenaufruf freigegeben. Der gemeinsame Builder schließt Quellgeneratoren jetzt ausdrücklich, auch bei nachgelagerten Validierungsfehlern.

POLARS_MAX_THREADS=1 passt zur vorhandenen Worker-CPU-Grenze. Abbruch/Rechteprüfung erfolgen vor/nach Gruppen und zwischen Umwandlungsabschnitten; ein laufender synchroner nativer Gruppenaufruf wird nicht mitten in der Dekodierung unterbrochen. Die native Verarbeitung bleibt durch 256 MiB begrenzt. Weder Dateinamen noch Zelltexte oder spätere Agentenvorschläge werden als externe Pfade oder Ausdrücke ausgeführt.

## SQLite-Quellen

sqlite_format.SQLiteSource liest einen vollständigen Snapshot mit mode=ro und immutable=1. Tabellen werden anhand des Schemas gewählt, Bezeichner korrekt zitiert; ein Authorizer begrenzt die eigentliche Abfrage auf die gewählte gewöhnliche Tabelle. Defensive Konfiguration, deaktiviertes trusted_schema, Record-/SQL-/Spaltenlimits und progress_handler begrenzen die Quelle. Abbruchausnahmen werden über den nativen Callback hinweg erhalten und die Verbindung im finally geschlossen.

Der gemeinsame Builder übernimmt den tatsächlich gewählten Namen in source_table. Der Worker überträgt ihn beim Bereinigen aus dem Quellprofil; Import- und Wiederaufnahmejobs speichern table_name im typisierten Vertrag. Originalbytes und alle bisherigen RLS-/Audit-/Freigabegrenzen bleiben bestehen. SQLite ist hier keine Ablösung der PostgreSQL-Plattformdatenbank und kein SQL-Tool für Agenten. [Entscheidung und Grenzen](../../../../../docs/adr/0013-sqlite-datenbanksnapshots.md).

## M2-Erweiterung vom 14.09.2026

Analyse, Quelle und Plan werden in `data_tasks` gespeichert; sie ersetzen keine bestehenden Import-/Vorschaujobs. Aufgaben und Regeln haben eigene RLS-Richtlinien, mandantengebundene Fremdschlüssel, Eingabe-/Ergebnishashes und unveränderliche Abschlusszustände. Die Liste liest nur Metadaten; große Berichte werden einzeln geladen. Analysen prüfen den Quellhash und verarbeiten normalisierte Zeilen über einen begrenzten SQLite-Arbeitsindex. Legacy-Inline-Versionen bleiben unterstützt. Quellen veröffentlichen Snapshot, Dataset und Importjob atomar; der vorhandene Dateiworker übernimmt danach das Profiling.

Ein Quellenmonitor erneuert die Lease auch bei einer blockierten PostgreSQL-Abfrage und fordert bei Abbruch eine sichere Cancellation an. Vor Veröffentlichung werden Rolle, Lease und Registry erneut geprüft. Ein Crash führt höchstens zu drei Versuchen; verwaiste offene Abschnitte dieses Auftrags werden freigegeben. Fertige Originale werden nicht entfernt. Nicht erreichbare Quellen, ungültige Strukturen, Ressourcenüberschreitung und Rechteentzug ergeben sichtbare Fehler. Analyse-/Quellenaufträge können bewusst neu angefordert werden; unklare externe KI-Ausgänge werden nicht automatisch wiederholt.

Supervisor, Data Manager und Spezialist trennen Auftrag, Profilbefunde und Kandidatenauswahl. Verifier, Risiko-, Kosten- und Freigabekontrolle sind deterministischer Anwendungscode. Die Rollenanzeige behauptet keine sieben Live-LLM-Aufrufe. Ein KI-Vorschlag ist keine Berechtigungsquelle. Er darf nur Kandidaten-IDs wählen; die Vorschau und die explizite Versionsübernahme bleiben unabhängig. Die manuelle Bereinigung ist weiterhin vollständig verfügbar.

Weitere Datenbankadapter können denselben Snapshotvertrag nutzen. Zusätzliche Analysen benötigen typisierte Resultate, reproduzierbare Methodik, Ressourcenbudgets und Mandantentests. Keine ungenutzten ML-, Prozess- oder Agent-Factory-Gerüste. Entscheidung, Alternativen und Vertrauensgrenzen: [ADR 0014](../../../../../docs/adr/0014-datenanalyse-quellen-und-gepruefte-plaene.md).
