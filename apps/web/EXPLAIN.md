# Aufbau und Erweiterung

design-tokens.css definiert semantische Farb-, Schrift-, Abstands-, Dichte- und Diagrammrollen. DesignSystem.tsx stellt Marke, SVG-Symbole, Dichtewahl und Filterwerkzeugleisten bereit. components.tsx enthält native Felder, Lade-, Fehler- und Leerzustände. Die lokal lizenzierte IBM Plex Sans vermeidet externe Fontaufrufe. Normal- und Kompaktansicht verändern Abstände, nicht die Informationsmenge.

workspace.css bündelt Shell, Kataloge und Navigation; die früheren Shell-Regeln in styles.css wurden entfernt. WorkspaceSummary zeigt nur nachweisbare Werte aus geladenen Listen und bei ausstehender Antwort einen Gedankenstrich. SectionNav verwendet fokussierbare Abschnittsziele und öffnet die Herkunftsansicht bei Bedarf. Es schreibt keinen neuen Hash und erhält die Bearbeitungsvorschau. Die mobilen Navigationsaktionen schließen die Navigation und setzen den Fokus in den Inhalt; Escape kehrt zum Auslöser zurück.

Der Import ist ein natives details-Element. Die Hauptaktion öffnet es und fokussiert den Namen. Das Formular bleibt beim Zuklappen montiert: Dateiauswahl, Entwurf und laufender Upload gehen nicht verloren. Der neue Bestandsfilter bleibt außerhalb dieses Formulars. Ohne Datenversion bedeutet ausschließlich, dass noch kein veröffentlichter Stand existiert; ein fehlgeschlagener Auftrag wird dadurch nicht als laufend gekennzeichnet.

Szenario- und Datenkatalog filtern ausdrücklich nur geladene Einträge; Cursor-Paginierung lädt weitere Einträge. Stabile Mindestbreiten schützen Tabellen vor zerhackten Wörtern. Breite Tabellen scrollen innerhalb ihres Bereichs. ECharts übernimmt dieselben semantischen Rollen über chartTheme.ts; zugängliche Wertetabellen bleiben verfügbar.

DataWorkspace.tsx organisiert Abschnittsupload, Wiederaufnahme, Importoptionen, Auftragsstatus, Versionen, Vorschau und Bestätigung. CSV, JSON/JSONL, XLSX, Parquet und SQLite nutzen denselben Serverworkflow. Die Dateiendung bestimmt nur die Darstellung geeigneter Optionen; Validierung und Zugriffsprüfung bleiben serverseitig. Historische Prüfsummen sind in einer aufklappbaren Metadatenansicht erreichbar.

Ein Verbindungsfehler darf Upload und Original nicht verlieren. Bei einem Importfehler kann der Nutzer Leseoptionen ändern und das gespeicherte Original erneut verarbeiten. Die Oberfläche kann weder Berechnungsregeln noch Rechte umgehen. Spätere Agentenvorschläge müssen dieselben typisierten Serververträge verwenden.

Künftige komplexe Komponenten dürfen geprüfte Headless-Primitiven einsetzen, wenn deren Nutzen konkret belegt ist. Keine neue individuelle Modulpalette oder parallele Navigation. [Gemeinsamer Gestaltungsvertrag](../../docs/DESIGN_SYSTEM.md).

Parquet verwendet dasselbe Importformular und erklärt die Anforderungen an flache Spalten und begrenzte Zeilengruppen. Der eigene Browserfall nutzt ausschließlich e2e/fixtures/synthetisch.parquet. [Parquet-Prüfbericht](../../docs/testing/M2_PARQUET_REPORT.md).

SqliteSettings verwendet das bestehende native Field-Muster für table_name. Die Auswahl gehört zum Upload-Fingerprint, zur Wiederaufnahme und zum Retry-Vertrag; CSV-Optionen bleiben bei SQLite ausgeblendet. Das Profil zeigt source_table auch nach einer Bereinigung. Keine zusätzliche Komponentenbibliothek oder abweichende Gestaltungsregeln.
