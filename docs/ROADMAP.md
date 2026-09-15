# Roadmap

Stand: **14.09.2026**. **M2 erledigt gemäß Nutzerentscheidung:** vereinbarter Funktionsumfang implementiert, integriert und lokal geprüft. Der aktuelle Restore-Nachweis bleibt nach Prüfsummen-Timeout offen; keine weitere Testserie beauftragt. [Abschlussbericht](testing/M2_COMPLETION_REPORT.md). Die zentrale Dataset-Quote mit Default 1000 bleibt erhalten. Auf Nutzeranweisung endet die Arbeit hier; **M3 wurde nicht begonnen**. Die datierten Fortschrittsabschnitte unten bleiben als historische Teilschritte erhalten.

| Meilenstein | Demonstrierbarer Nutzen | Hängt ab von | Aktueller Stand |
| --- | --- | --- | --- |
| M0 / Phase 0 | umsetzbare Architektur mit überprüfbaren Kriterien | Master Prompt | dokumentiert; M1 ausdrücklich aktiviert |
| M1 / Phase 1 | gespeicherter und geprüfter Unternehmens-/Architekturvergleich | M0-Durchsicht | IMPLEMENTIERT, lokale Demo |
| M2 | Daten importieren, analysieren, nachvollziehbar bereinigen und exportieren | M1 Identität/Audit | IMPLEMENTIERT · erledigt auf Nutzeranweisung; Browser und Betriebsgrenzen bestanden, aktueller Restore-Nachweis offen |
| M3 | Prozesse mit gemessenen KPIs verbessern | M2 Event-Verträge | NICHT IMPLEMENTIERT |
| M4 | Cloud-Kosten und Wiederanlauf planen | M1, M2 Jobs/Adapter | NICHT IMPLEMENTIERT |
| M5 | autorisiertes Labor prüfen und Findings nachverfolgen | M1 Rechte, M2 Jobs | NICHT IMPLEMENTIERT |
| M6 | belegter interner Support mit Eskalation | M2 Dokumente, Agentenverträge | NICHT IMPLEMENTIERT |
| M7 | geprüfte neue Agentenversionen und kontextbezogene Hilfe | M1–M6 reale Tools und Evals | NICHT IMPLEMENTIERT |
| M8 | alle Abläufe betreibbar und gemeinsam nachgewiesen | M1–M7 | NICHT IMPLEMENTIERT |

Observability, Security und Tests begleiten jeden Meilenstein; sie werden nicht bis M8 aufgeschoben. M8 vertieft und überprüft sie im Gesamtsystem.

Die erste sinnvolle Portfolio-Demo ist M1. Die erste Daten-/Prozess-Demo entsteht mit M2/M3. Ein IHK-Ausschnitt wird anhand eines konkreten betrieblichen Problems und der geltenden Rahmenbedingungen getrennt festgelegt.

Zeitplanung wird nach M1 mit tatsächlichem Aufwand, verfügbarer Arbeitszeit und Lernbedarf erstellt. Die Angaben zur Ausbildung im ursprünglichen Begleittext werden nicht ungeprüft als Projekttermine übernommen.

## M2-Fortschritt vom 12.09.2026

Reale CSV-Reparatur mit erfolgreicher Wiederaufnahme aller fünf beanstandeten Dateien abgeschlossen. JSON/JSONL als nächster flacher Tabellenadapter implementiert; aktuelle Nachweise im [JSON-Bericht](testing/M2_JSON_REPORT.md). XLSX wurde anschließend ergänzt; offen bleiben Parquet und Datenbankquellen sowie die weiteren Modul-C-Analysen und beaufsichtigten typisierten KI-Transformationsvorschläge. Die bestehende deterministische Freigabegrenze gilt auch für spätere Agenten.

## Gemeinsames Produktdesign und XLSX

IT-Kompass besitzt eine gemeinsame visuelle Grundlage für M1–M8; bestehende Komponenten und ECharts bleiben erhalten. XLSX ergänzt M2 um den kontrollierten Arbeitsblattimport. [Designsystem](DESIGN_SYSTEM.md), [ADR 0011](adr/0011-xlsx-tabellenadapter.md), [Nachweis](testing/M2_PRODUCT_XLSX_REPORT.md). Parquet ist implementiert; als Nächstes Datenbankquellen und weitere Modul-C-Analysen samt beaufsichtigten Transformationsvorschlägen. Die geplante Agentenhierarchie und die deterministische Freigabegrenze bleiben maßgeblich.

## Parquet am 13.09.2026

Der Parquet-Adapter ist bis zur bestätigten Bereinigung und zum Export implementiert und lokal geprüft. [Prüfbericht](testing/M2_PARQUET_REPORT.md). Offen bleiben Datenbankquellen, zusätzliche Qualitätsregeln/Statistik und beaufsichtigte KI-Transformationsvorschläge. Keine Erweiterung der Agentenrechte oder Umgehung der bestehenden Freigabegrenzen.

## Vertieftes Enterprise-Design

Die gemeinsame Oberfläche wurde am 13.09.2026 überarbeitet und lokal geprüft; [Nachweis](testing/M2_ENTERPRISE_DESIGN_REPORT.md). Die Dataset-Quote wurde vom Nutzer zentral konfigurierbar gemacht, Default 1000; diese Änderung bleibt erhalten. Als Nächstes folgen Datenbankquellen, Qualitätsregeln/Statistik und beaufsichtigte typisierte Agentenvorschläge. Langfristig isolierte Testdaten bleiben ein Betriebsaspekt, kein vorgeschalteter Quotenfehler.

## SQLite-Snapshots am 13.09.2026

Erster Datenbankadapter bis zur bestätigten Bereinigung und zum Export implementiert und lokal aktiv. Tabellenwahl und Korrektur ohne erneuten Upload, Herkunft in Folgeversionen und Quellschutz nachgewiesen. [Prüfbericht](testing/M2_SQLITE_REPORT.md). Direkte Netzwerk-Datenbankquellen bleiben ein separater nächster Schritt mit Secret-/Verbindungs-/Snapshotvertrag; danach zusätzliche Qualitätsregeln/Statistik und beaufsichtigte Transformationsvorschläge. Agentenhierarchie und deterministische Freigaben bleiben maßgeblich.
