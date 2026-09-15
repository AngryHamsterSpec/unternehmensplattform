# M2 — Datenintelligenz, erster CSV-Ablauf

Aktiviert am 11.09.2026 durch die Nutzerzustimmung zum angekündigten M2-Schritt. M1 bleibt erhalten; dies ist keine produktive Betriebsfreigabe.

Implementiere CSV-Import → persistenter Auftrag → Profiling → manuelle Transformation → Vorschau → ausdrückliche Bestätigung → unveränderliche neue Version → interaktive Qualitätsansicht → sicherer CSV-Export.

Der erste überprüfbare Umfang umfasst UTF-8 mit optionalem BOM, explizite Trennzeichen, **bis 1 GiB Originaldatei**, abschnittsweisen Upload, Streaming-Verarbeitung, Fortschritt und Abbruch. Die Erweiterung wurde am 12.09.2026 ausdrücklich beauftragt und ersetzt die bisherigen kleinen Demogrenzen. Es gibt keine feste Zeilen-/Gesamtzellenanzahlgrenze; 256 Spalten, 1.048.576 Zeichen je Zelle und 4 MiB je normalisiertem Datensatz bleiben Schutzgrenzen. Ableitungen sind ebenfalls begrenzt. Fehler erzeugen deutsche, datenarme Meldungen. Originalbytes, Hash, Urheber, Pipeline und Versionen bleiben verknüpft. Bestehende Mandanten-, Rollen-, CSRF- und Auditregeln gelten auch für Dateien, Aufträge und Exporte.

Verwende den vorhandenen Python-/PostgreSQL-Stack. Ein eigener begrenzter Worker verarbeitet persistente PostgreSQL-Aufträge. Ein tatsächlich verwendeter Speicherport erhält zunächst einen transaktionalen PostgreSQL-Adapter. Begründe Grenzen und spätere S3-Erweiterung in einem ADR.

Prüfe insbesondere CSV-Randfälle, Formula-Injection im Export, Mandantenwechsel, Lesekonten, Vorschau-Manipulation, parallele Bestätigung, unveränderte Originaldaten, Worker-Ausfall, Neustart und Migration bestehender Daten. Führe Format-, Lint-, Typ-, Unit-, echte PostgreSQL-, Browser- und Sicherheitsprüfungen aus; dokumentiere tatsächlich gemessene Ergebnisse.

JSON/XLSX/Parquet, Datenbankquellen, allgemeine Qualitätsregeln, tiefere Statistik, KI-Transformationsvorschläge und verteilte Datenverarbeitung bleiben weitere M2-Ausbauschritte. Kennzeichne den gesamten breiteren M2-Umfang bis dahin als TEILWEISE IMPLEMENTIERT.


## Zusätzlicher Nutzerauftrag vom 12.09.2026

Moderne normale und interaktive Datenvisualisierung direkt in der deutschen Anwendung. Beispiele des Nutzers (u. a. Plotly, Matplotlib, Bokeh) sind Vergleichsmöglichkeiten, keine Pflicht zur Installation aller Bibliotheken. Auswahl: Apache ECharts im bestehenden React-Frontend. Vollständige Profilwerte und begrenzte Detailauswahl müssen eindeutig getrennt und versionstreu sein. Auf späteren ausdrücklichen Wunsch: gezielte relevante Prüfungen statt Wiederholung der langen vollständigen Last- und Betriebsläufe. [ADR 0007](../adr/0007-interaktive-datenvisualisierung.md).

## Fortsetzung nach CSV-Reparatur

Am 12.09.2026 ausdrücklich autonom beauftragt. Nach Wiederaufnahme aller fünf fehlerhaften Originalimporte wird JSON/JSONL als nächster M2-Adapter umgesetzt. Derselbe deterministische Worker-, Profil-, Vorschau- und Bestätigungsablauf gilt. Die spätere Data-Manager-Hierarchie verwendet typisierte Profile und Pläne; dieser Formatadapter behauptet keine neue Live-KI. [ADR 0009](../adr/0009-json-tabellenimport.md).
