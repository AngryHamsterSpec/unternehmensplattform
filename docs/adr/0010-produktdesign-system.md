# ADR 0010 — Gemeinsame visuelle Identität

Datum: 12.09.2026. Status: implementiert und lokal geprüft.

Der [fokussierte Designreview](../PRODUCT_DESIGN_REVIEW.md) bestätigt die vorhandene native React-Infrastruktur als geeignete Grundlage. Die bisherige verstreute Gestaltung erhält eine gemeinsame semantische Ebene, konsistente Identität IT-Kompass, lokal lizenzierte Typografie und wiederverwendbare Komponenten. Einzelne Fachmodule behalten ihre bewährten API-/Freigabeabläufe.

[Detaillierter Gestaltungsvertrag](../DESIGN_SYSTEM.md). ECharts bleibt erhalten und liest das gemeinsame Theme. Base UI/Radix sind künftige Optionen bei tatsächlichem Bedarf an komplexen Interaktionen; eine pauschale Migration wäre momentan zusätzlicher Aufwand ohne belegten Produktnutzen.

Der Datenkatalog erhält Filter auf geladenen Einträgen und fehlendes Nachladen vorhandener Seiten. Suchfelder behaupten keine vollständige Suche über noch nicht geladene Serverdaten. Keine Backend-/Lasttestwiederholung für die gemeinsame Gestaltung; relevante Frontend- und Browserprüfungen sichern die betroffenen Ansichten.

Fortschreibung am 13.09.2026: Die vertiefte Browserprüfung führt zu einer eigenen mineralischen/graphitgrünen Farbwelt, fachlich gruppierter Navigation, Bestandsübersicht und einem aufklappbaren Import. Die vorhandene native Infrastruktur bleibt bestehen. Shell-Regeln werden in workspace.css konsolidiert, gemeinsame Komponenten um Bestandswerte und Abschnittsaktionen ergänzt. Backendverträge und Agentenrechte ändern sich dadurch nicht. [Aktueller Gestaltungsvertrag](../DESIGN_SYSTEM.md).
