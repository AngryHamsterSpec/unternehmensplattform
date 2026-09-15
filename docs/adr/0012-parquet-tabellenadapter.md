# ADR 0012 — Kontrollierter Parquet-Import

Datum: 13.09.2026. Status: implementiert und lokal geprüft.

Parquet ergänzt die vorhandenen Tabellenadapter. Polars 1.44.2 besitzt eine passende musllinux-Laufzeit für das bestehende Alpine-Image. Kein Wechsel der Basissysteme oder der Berechnungspipeline. Apache Thrift 0.24.0 liest ausschließlich den begrenzten Metadatenfuß zur Vorprüfung.

Der Adapter akzeptiert eine einzelne lokal gespeicherte PAR1-Datei mit flachem Schema. Keine Verzeichnis-/Glob-/Cloudquellen, externen Column-Chunks oder Verschlüsselung. Native Dezimal-, Datums-/Zeit- und Ganzzahlwerte werden ohne Umweg über Python-Fließkommazahlen in Stringzellen überführt. Null wird leer; Binärdaten und verschachtelte Spalten benötigen vorherige Aufbereitung. Nichtendliche Zahlen werden ausdrücklich abgewiesen.

Vor dem nativen Reader: Dateimarker, Footergröße, begrenzte Thrift-Struktur, Spaltenzahl, Row-Groups und deklarierte entpackte Größen prüfen. Grenzen: 8 MiB Footer, 4.096 Row-Groups, 64 MiB unkomprimiert je Gruppe und 8 GiB insgesamt. Jede geprüfte Zeilengruppe wird synchron gelesen; die Umwandlung erfolgt danach in geordneten 64-Zeilen-Abschnitten. Das ersetzt keine harte Prozessgrenze: der Worker bleibt auf 256 MiB/1 CPU begrenzt; komprimierte/native Dateiformate erhalten keine pauschale 1-GiB-Verarbeitungszusage.

Die als instabil dokumentierte collect_batches-Schnittstelle wird nicht verwendet: die installierte Version bietet keinen expliziten stop-Aufruf am Iterator. Stattdessen beendet ein synchroner Gruppenaufruf seine Arbeit, bevor der Worker die nächste Gruppe freigibt. Das ist bei sehr vielen kleinen Gruppen langsamer, hält aber Lebensdauer und Abbruchpunkte eindeutig. Exakte Versionsbindung und Adaptertests sichern die Nutzung. Originalbytes, Schemaherkunft, Vorschau und bestätigte Version verwenden dieselben bestehenden Rechte und Tools. Keine ausführbaren Modellpläne oder zusätzlichen Agentenrechte.

Quellen: [Polars-Runtime](https://pypi.org/project/polars-runtime-32/1.44.2/), [Batch-Verarbeitung](https://docs.pola.rs/api/python/stable/reference/lazyframe/api/polars.LazyFrame.collect_batches.html), [Scan-Optionen](https://docs.pola.rs/api/python/stable/reference/api/polars.scan_parquet.html), [Apache-Parquet-Metadaten](https://github.com/apache/parquet-format/blob/master/src/main/thrift/parquet.thrift).
