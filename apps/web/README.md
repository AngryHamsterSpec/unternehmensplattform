# Webanwendung — IT-Kompass

Deutsche Arbeitskonsole für Architekturplanung, Vergleich, Datenintelligenz und rollenabhängige Verwaltung. React 19, TypeScript, Vite und Apache ECharts; vorhandene native Komponenten bleiben die Grundlage.

Die aktuelle Gestaltung verwendet warme mineralische Flächen, Graphitgrün und sparsame Messingakzente. Gruppierte Navigation, kompakte Kataloge mit tatsächlichen Bestandswerten und Datenstandfilter, aufklappbarer Import und direkte Zugänge zu Analyse/Bereinigung bilden das gemeinsame Bedienmodell. Mobile Navigation ist aufklappbar; die Dichtewahl bleibt verfügbar. Dafür wurden keine Abhängigkeiten hinzugefügt.

Das [Designsystem](../../docs/DESIGN_SYSTEM.md) gilt für alle Module M1–M8. [Review und Entscheidung](../../docs/PRODUCT_DESIGN_REVIEW.md), [ADR 0010](../../docs/adr/0010-produktdesign-system.md).

Start und Umgebung: [Projekt-README](../../README.md). Lokaler Zugriff über http://localhost:8080. Es werden keine echten Unternehmensdaten oder produktiven Betriebszusagen vorausgesetzt.

[Erklärung](EXPLAIN.md) · [Prüfung](TESTING.md).

Parquet verwendet dasselbe Importformular und erklärt die Anforderungen an flache Spalten und begrenzte Zeilengruppen. Der eigene Browserfall nutzt ausschließlich e2e/fixtures/synthetisch.parquet. [Parquet-Prüfbericht](../../docs/testing/M2_PARQUET_REPORT.md).

SQLite-Snapshots ergänzen den Import um eine Tabellenwahl. Bei genau einer Tabelle ist sie optional; eine fehlerhafte Auswahl kann ohne erneuten Upload korrigiert werden. Der Tabellenname bleibt in Analyse und Folgeversionen sichtbar. Derselbe Bereinigungs-/Bestätigungsablauf gilt; direkte Netzwerk-Datenbankverbindungen bleiben geplant. [SQLite-Nachweis](../../docs/testing/M2_SQLITE_REPORT.md).
