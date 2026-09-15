# ADR 0013 — SQLite-Datenbanksnapshots

Status: angenommen, 13.09.2026. Erster begrenzter Datenbankadapter in M2.

## Entscheidung

SQLite-Sicherungsdateien (`.sqlite`, `.sqlite3`, `.db`) werden über den bestehenden Abschnittsupload importiert. Eine gewöhnliche Tabelle wird explizit gewählt; bei genau einer geeigneten Tabelle kann die Auswahl entfallen. Ein falscher oder fehlender Name lässt sich am gespeicherten Original korrigieren. Der Adapter erzeugt dieselben Profile, Bereinigungsvorschauen, bestätigten Versionen, Diagramme und CSV-Exporte wie die übrigen Formate.

Der Datenquellenvertrag erhält `table_name`, das Profil `source_table` und `source_format=sqlite`. Die Auswahl bleibt bei abgeleiteten Versionen erhalten. Vorhandene JSONB-Verträge erhalten kompatible Standardwerte; keine neue Migration, kein Dienst und keine zusätzliche Abhängigkeit. CSV-Leseoptionen werden bei SQLite nicht verwendet.

## Gründe und Alternativen

Ein portabler Snapshot liefert einen überprüfbaren Datenbankworkflow ohne Zugangsdaten, Netzwerkfreigaben oder Änderungen an fremden Datenbanken. Direkte PostgreSQL-/andere Netzwerkquellen bleiben ein eigener M2-Schritt mit separatem Secret-, Verbindungs-, Snapshotkonsistenz- und Berechtigungsvertrag. Ein generischer SQL-Editor oder vom Modell erzeugte Abfragen würden die bestehende Toolgrenze unnötig erweitern.

Die Plattformdatenbank bleibt PostgreSQL mit RLS. SQLite dient hier ausschließlich als importierte Quelle und weiterhin als bestehender temporärer Profilierungsspeicher.

## Schutz und Grenzen

- Originaldatei unverändert, vollständiger Hash vor Verarbeitung, vorhandene Mandanten-/Rollen-/CSRF-/Audit-/Lease-/Abbruchregeln. Die vom Nutzer eingeführte zentrale Dataset-Quote mit Default **1000** bleibt bestehen.
- Quelle mit `mode=ro&immutable=1`, defensive Konfiguration und deaktiviertem vertrauenswürdigem Schema. Kein Laden von Erweiterungen; keine eigenen SQL-Funktionen im Quellenreader. Der Authorizer erlaubt ausschließlich SELECT und Lesen der gewählten gewöhnlichen Tabelle.
- Namen werden zuerst mit dem Schema abgeglichen und anschließend als SQL-Bezeichner zitiert. Keine frei eingegebenen SQL-Fragmente. Ansichten, virtuelle Tabellen, berechnete/versteckte Spalten und binäre beziehungsweise unendliche Werte benötigen vorherige Aufbereitung.
- Nur vollständige, unverschlüsselte SQLite-3-Snapshots im DELETE-Journalmodus. WAL-Dateien werden ausdrücklich zurückgewiesen: Eine einzeln hochgeladene Hauptdatei kann bestätigte Änderungen aus dem zugehörigen WAL vermissen. Auch eine DELETE-Datei muss als konsistente Sicherung exportiert werden; der Dateikopf allein beweist das nicht.
- Zeilen werden einzeln gelesen; 4 MiB SQLite-Datensatzlimit, 4 MiB normalisierter Datensatz, 256 Spalten, 100 Zeichen je Tabellen-/Spaltenname und die bestehenden Zellgrenzen. Bis 1.000 Einträge in der Schemaübersicht, 64 KiB SQL-Länge, 25.000 VM-Instruktionen je vorbereitetem Statement, keine angehängten Datenbanken, 4 MiB Seitencache und kein mmap. Diese Grenzen ersetzen nicht das separate Workerlimit von 256 MiB/1 CPU.
- Fortschrittscallback erhält Lease und Abbruchfähigkeit auch während einer Abfrage. Quelle wird bei Erfolg, Fehler und vorzeitigem Generatorende geschlossen. Reihenfolge nach unverdeckter Rowid oder bei WITHOUT ROWID nach Primärschlüssel; sind alle Rowid-Aliase verdeckt, ist ein CSV-Export nötig.
- SQLite NULL wird in der Tabellenableitung leer; Ganzzahlen durchlaufen keinen Float, gespeicherte endliche REAL-Werte behalten ihre vorhandene Genauigkeit. Datums- und Boolean-Semantik werden nicht aus deklarierten SQLite-Typnamen erfunden. Originalwerte bleiben im Snapshot verfügbar.

## Agentenarchitektur

Ein späterer Data Manager kann anhand des typisierten Profils Vorschläge erstellen. Der Quellenadapter erteilt keine SQL-/Netzwerk-/Dateisystemrechte an Agenten. Änderungen laufen weiterhin über begrenzte Steps, deterministische Prüfung, Vorschau und ausdrückliche Bestätigung. Keine neue Live-KI.

## Referenzen

[Python sqlite3](https://docs.python.org/3/library/sqlite3.html), über Context7 geprüft: URI-Modus, setconfig/setlimit, Authorizer, Fortschrittscallback und Schließen. [Prüfbericht](../testing/M2_SQLITE_REPORT.md).
