# Produkt-Designreview — IT-Kompass

Erstreview: 12.09.2026. Vertiefung: 13.09.2026. Auftrag: eigenständige Unternehmenssoftware; Funktionen und Zugänglichkeit erhalten. Die Abschnitte unten dokumentieren zunächst die erste Iteration; die aktuelle Richtung steht in der Vertiefung.

## Befund vor der Umsetzung

Die React-Anwendung verwendet eigene native Komponenten, kein shadcn. Ein Austausch des Frameworks behebt deshalb die visuelle Beliebigkeit nicht. Die aktuelle Identität ist uneinheitlich: M als Zeichen, Unternehmensplattform im Produkt und IT-Kompass im Browser. Große gerundete Flächen, grüne Verläufe, verstreute Farbwerte, wechselnde Radien und separate Diagrammgestaltung erzeugen einen Demonstrator-Eindruck. Navigationszeichen sind unterschiedliche Unicode-Glyphen. Tabellen benötigen eine klarere Werkzeugleiste und kompaktere Zeilen. Wiederkehrende Drei-Schritt-Banner beanspruchen viel Platz.

## Richtung

IT-Kompass wird eine ruhige technische Arbeitskonsole: dunkle tintenfarbene Navigation, helle mineralische Arbeitsfläche, präzise blaue Aktionen, warme zurückhaltende Warnfarben. Rechteckige Flächen, klare Trennlinien, kompakte Metadaten und konsistente kleine Radien. IBM Plex Sans wird lokal mit Lizenz ausgeliefert; Zahlen verwenden tabellarische Ziffern. Ein eigenes geometrisches Kompasszeichen und konsistente SVG-Symbole ersetzen die zufälligen Glyphen. Kein dekoratives Dashboard und keine erfundenen Kennzahlen.

Normale und kompakte Dichte werden bewusst angeboten. Tabellen bleiben semantisches HTML mit sichtbaren Zeilenfokussen, Bedienfeldern, Such-/Ergebnisangaben und nachvollziehbarer Seitennavigation. Gemeinsame Tokens und Komponenten gelten auch für M3–M8. Datenvisualisierung nutzt dieselbe Schrift-, Achsen-, Raster- und Farbwelt.

## Vergleich und Entscheidung

| Ansatz | Bewertung | Entscheidung |
| --- | --- | --- |
| Eigenes System auf vorhandenen nativen Komponenten | Bestehende Formulare und Rechteflüsse bleiben stabil; visuelle Kontrolle ohne neue Laufzeitbibliothek | jetzt umsetzen |
| shadcn als Startvorlage | Einzelne offene Komponenten können nützen, ein Vorlagenwechsel liefert noch keine eigene Identität | keine pauschale Migration |
| Base UI / Radix | Unstyled Primitive für komplexe Popover, Comboboxen und Dialoge; zusätzliche Abhängigkeit muss konkreten Nutzen haben | bei entsprechendem Funktionsbedarf gezielt auswählen |
| Apache ECharts | Bestehende interaktive Analyse, zugängliche Werteansicht und Bildexport; eigene Themes vorgesehen | behalten und einheitlich gestalten |

## Quellen und Einordnung

[Carbon: Data tables](https://carbondesignsystem.com/components/data-table/usage/) beschreibt Werkzeugleisten, Zeilengrößen, Hoverzustände und Pagination. Übernommen werden diese Bedienprinzipien, nicht IBMs Oberfläche.
[Base UI](https://base-ui.com/react/overview/about) bietet ungestylte zugängliche React-Primitiven. Ein Bibliothekswechsel ist für die derzeitigen nativen Felder nicht erforderlich.
[IBM Plex](https://github.com/IBM/plex) liefert die offen lizenzierte technische Schriftfamilie; die ausgelieferten Dateien und ihre Lizenz werden im Repository festgehalten.
[ECharts: Style](https://echarts.apache.org/handbook/en/concepts/style/) unterstützt gemeinsame Themes und explizite Gestaltung.

## Abnahme

Anmeldung, Szenarien, Formulare, Bewertung, Vergleich, Datenkatalog/-analyse und Verwaltung konsistent gestalten. Desktop und 390-Pixel-Ansicht, Fokus, Dichte, Filter, Diagrammexport und bestehende Kernabläufe gezielt prüfen. Für reine Gestaltung keine erneuten Backend-/1-GiB-Lastläufe. Roadmap anschließend mit XLSX als nächstem Datenadapter fortführen; dessen Dateisicherheit erhält eigene Prüfungen.

## Vertiefung vom 13.09.2026

Die Browserprüfung zeigte trotz vereinheitlichter Tokens eine zu formularlastige Datenwerkstatt: Der vollständige Import und wiederholte Einführungstexte verdrängten den Datenbestand. Architektur- und Datenmodule waren in derselben Navigationsliste ohne Fachgliederung vermischt. Auf kleinen Displays beanspruchte die dauerhaft sichtbare Navigation zu viel Höhe. Die erste blaue Gestaltung blieb austauschbar.

Die aktuelle Richtung ist eine ruhige technische Arbeitskonsole mit warmer mineralischer Fläche, Graphitgrün und einem sparsamen Messingakzent für Marke und Navigationsmarkierungen. Tabellen werden zu zusammenhängenden Arbeitsflächen mit Filtern, Dateitypen und Versionsständen. Tatsächliche Bestandswerte ersetzen Einführungsbanner. Analyse und Bereinigung erhalten direkte Abschnittsaktionen; Originalnachweise bleiben erreichbar. Schrift und Diagrammfarben folgen denselben Rollen in allen Modulen.

Serena wurde zur gezielten Komponentennavigation verwendet. Ein shadcn-MCP war nicht verfügbar; Context7 lieferte aktuelle Referenzen aus dem offiziellen offenen Repository: [Dashboard-Sidebar](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/blocks/dashboard-01/components/app-sidebar.tsx), [Tabellenprimitive](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/ui/table.tsx) und [Tabellenpagination](https://github.com/shadcn-ui/ui/blob/main/apps/v4/app/(app)/examples/tasks/components/data-table-pagination.tsx). Übernommen wurden Gliederungs- und Bedienprinzipien. Native Tabellen, Details, Selects und die vorhandenen React-Komponenten decken den konkreten Bedarf ab; eine zusätzliche Bibliothek oder Vorlagenmigration hätte hier keinen belegten Vorteil. Kein Registry-Code wurde ungeprüft installiert.

Relevante Prüfung: Build, Format/Lint, Komponententests, vorhandene OIDC-/Dateiabläufe und tatsächliche Desktop-/Mobilansichten. Kein erneuter Last-, Restore- oder Backendvolltest für diesen Frontendschritt. M2 bleibt insgesamt teilweise implementiert; Datenbankquellen sind der nächste fachliche Ausbau.
