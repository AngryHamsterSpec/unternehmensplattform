# IT-Kompass — visuelles System

Stand: 13.09.2026. Grundlage aller vorhandenen und künftigen Module M1–M8. [Designreview](PRODUCT_DESIGN_REVIEW.md).

## Rollen statt Einzelwerte

design-tokens.css enthält Flächen, Text, Linien, Aktionen, Navigation, Status, Fokus, Abstände, Radien und Diagrammfarben. Mineralische warme Flächen, dunkles Graphitgrün und kontrollierte Messingakzente bilden die Identität. Messing kennzeichnet Marke und Navigation; fachliche Warnungen behalten eigene semantische Rollen. Neue Fachmodule verwenden diese Rollen. Bestehende --ink/--muted/--petrol-Variablen sind Kompatibilitätsnamen auf dieselben Rollen; neue Komponenten verwenden semantische Namen.

Schrift: lokal ausgelieferte IBM Plex Sans in 400/500/600, Systemfallback Segoe UI; tabellarische Ziffern. Lizenz und SHA-256 stehen unter apps/web/public/fonts. Kein externer Fontdienst zur Laufzeit. Text 14px, Datenzellen 13px, Formulare 13–14px, Metadaten 11–12px, Seitenüberschriften 32px beziehungsweise 28px mobil. Flächenradius 6px, Bedienelemente 4px. Keine Fachinformation ausschließlich in winzigem Text.

## Gemeinsame Komponenten und Muster

DesignSystem.tsx liefert das Kompasszeichen, einheitliche SVG-Symbole, Dichteschalter, Tabellenwerkzeugleiste, WorkspaceSummary und SectionNav. components.tsx bleibt die Quelle für Felder, Status, Fehler, Lade- und Leerzustände. Vorhandene native Buttons, Selects, Labels, Details und Tabellen behalten Browser- und Tastaturverhalten. workspace.css enthält ausschließlich Shell, Navigation und Katalogmuster; frühere konkurrierende Shell-Regeln wurden aus styles.css entfernt. styles.css verwaltet gemeinsame Felder und Fachansichten, charts.css die Visualisierung.

Normale Dichte: 40px Felder, 12px vertikale Tabellenzellenabstände. Kompakt: 34px Felder, 7px Tabellenzellenabstände. Schriftgröße bleibt lesbar. Die lokale Präferenz ist unabhängig von Fach-/Mandantendaten; bei gesperrtem lokalen Speicher funktioniert der Schalter weiterhin.

Seiten: gruppierte Navigation nach Architekturplanung, Datenintelligenz und rollenabhängiger Verwaltung; schmale Kontextleiste, eindeutiger Seitentitel und Hauptaktion. Mobile Navigation wird mit beschriftetem Button geöffnet; Escape schließt sie und setzt den Fokus zurück. Nach Auswahl erhält der Inhalt den Fokus. Seitenwechsel beginnen oben. Keine Bedienelemente für nicht implementierte Module.

Kataloge stehen vor der Eingabe: Bestandskennzahlen beziehen sich ausschließlich auf geladene Einträge, bei fehlender Antwort erscheint ein Gedankenstrich. Der Datenstandfilter unterscheidet versionierte Datensätze und solche ohne Version; letzteres behauptet keinen laufenden Auftrag. Suche und Statusfilter werden kombiniert. Nachladen bleibt möglich. Der native aufklappbare Importbereich bleibt montiert: Zuklappen verliert weder Eingaben noch einen laufenden Upload. Die Hauptaktion öffnet ihn und fokussiert die Eingabe. Abschnittsaktionen springen zu Analyse, Datentabelle, Bereinigung und Herkunft, ohne den Hash-Router oder Entwürfe zu verändern. Die Herkunftsaktion öffnet die Metadatenansicht.

## Datenvisualisierung

chartTheme.ts liest die CSS-Rollen auch für ECharts. Diagrammexporte nutzen dieselben Optionen wie die Ansicht. Die kategoriale Palette ist von Statusfarben getrennt. Balken/Marker, Legenden, Beschriftungen und die zugängliche Wertetabelle ergänzen Farbe; Ringdiagramme nutzen zusätzliche Muster. Datenbasis, Version und Auswahlgrenzen bleiben erhalten. Kein neuer Chartanbieter oder CDN.

## Zugänglichkeit und Erweiterung

Sichtbarer Fokus; Status mit Text, nicht nur Farbe. Native Tabellen und Überschriften, Fokuszustand in Zeilen, Tastaturzugang, reduzierte Bewegung, mobile Umbrüche und Druckregeln. 390px ist Mindestnachweis, breite Datentabellen scrollen innerhalb ihrer Fläche.

Neue Dialoge/Comboboxen dürfen bei konkretem Bedarf ein geprüftes Headless-Primitiv verwenden. Keine globale Migration auf eine Vorlage. Neue Farben, Dichten oder Navigationsebenen benötigen eine Ergänzung dieses Dokuments und Sichtprüfung in vorhandenen Modulen.
