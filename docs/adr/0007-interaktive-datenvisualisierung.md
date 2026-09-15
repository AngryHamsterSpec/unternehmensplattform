# ADR 0007 — Interaktive und statische Datenvisualisierung

Status: angenommen für den lokalen M2-Umfang, 12.09.2026.

## Auftrag und Entscheidung

Der Nutzer hat moderne normale und interaktive Datenvisualisierung ausdrücklich ergänzt und anschließend kurze, gezielte Prüfungen gewünscht. Apache ECharts 6.1.0 wird mit exakter Version und Lockfile in die vorhandene React-Oberfläche integriert. Die Registry nennt Apache-2.0 als Lizenz. Es entsteht kein zweiter Dashboard-Server.

[Plotly für React](https://plotly.com/javascript/react/) wäre ebenfalls geeignet. Matplotlib/Seaborn passen zu Python-Berichten, Dash/Bokeh zu zusätzlichen Python-Weboberflächen. ECharts passt hier durch seine modularen Importe, Zoom-Komponenten und zwei Renderer zum bestehenden Webprodukt. Diese Entscheidung behauptet keine allgemeine Rangliste „beste Bibliothek“.

## Konkreter Umfang

Balken und Ring zeigen die acht häufigsten Werte einschließlich übriger und fehlender Werte. Die Qualitätsansicht zeigt belegte und fehlende Zellen je Spalte. Diese Ansichten verwenden das vollständige gespeicherte Profil.

Histogramm, Linie und Streudiagramm verwenden einen eigenen lesenden Endpunkt für eine begrenzte Detailauswahl. Spaltenwahl, Messwertgrenzen, Histogrammklassen, Zoom, Tooltips, Präsentationsmodus, vergrößerte Ansicht, Wertetabelle sowie SVG-/PNG-Export sind eingebunden. Eine zusätzliche synthetische Vertriebsdatei mit 180 Zeilen dient der Bedienung.

Die Linie folgt Originalzeilenpositionen. Sie ist keine automatisch erkannte Zeitreihe. Verbindungen können ausgelassene Zeilen überbrücken. Histogrammgrenzen und Diagrammkoordinaten verwenden Browserzahlen; finanzielle Berechnungen und gespeicherte Dezimalwerte bleiben unverändert.

## Grenzen, Herkunft und Speicher

GET /datasets/{id}/versions/{no}/chart-sample?x=0&y=1 liest höchstens zwölf gleichmäßig über die normalisierten Dateiabschnitte verteilte Abschnitte. Innerhalb dieser Abschnitte werden gleichmäßig Positionen gewählt: insgesamt höchstens 300 Zeilen. Anfang und Ende der gewählten Abschnitte sind enthalten. Alte Inline-Versionen verwenden gleichmäßige Zeilenpositionen.

Diese systematische Auswahl ist keine Zufallsstichprobe und kann verzerrt sein. Die API meldet complete ausschließlich, wenn die gesamte Zeilenanzahl enthalten ist; ansonsten systematic-chunks-v1. Jede Zeile enthält ihre ursprüngliche Position. Versionsnummer und vollständiger Inhaltshash begleiten die Antwort. Texte werden auf 512 Zeichen begrenzt, Kürzungen gezählt. Keine Download- oder Profilmutation entsteht.

Ein Abschnitt ist maximal 4 MiB groß. Die API hält jeweils einen Abschnitt und dessen begrenzte Zeilenzerlegung im Speicher; maximal 48 MiB gespeicherte Abschnittsdaten werden je Anfrage gelesen, zusätzlich Metadaten. Die Antwort enthält nur zwei ausgewählte Spalten. Lange Dateibodies landen nicht im Browser.

Der Detailabruf hält bis zum Lesen von Kopf, Versionen und Aufträgen eine geteilte Datensatzsperre. So kann die Veröffentlichung einer neuen Version nicht zwischen diesen Teilabfragen erfolgen. Diese Korrektur behebt einen im Restore-Browserlauf beobachteten gemischten Stand „Version 0 / vorhandene Version 1“.

## Darstellung und Sicherheit

[ECharts importiert nur benötigte Diagramme und Komponenten](https://echarts.apache.org/handbook/en/basics/import/). Das Diagrammmodul wird erst beim Öffnen einer Datenversion geladen. Bei höchstens 300 Punkten verwendet die Oberfläche SVG; PNG wird mit dem Canvas-Renderer in doppelter Auflösung exportiert. [Renderer-Abwägung](https://echarts.apache.org/handbook/en/best-practices/canvas-vs-svg/).

Tooltips verwenden richText, keine HTML-Formatter mit Dateiwerten. Achsen, Titel und Tabellen behandeln Dateiinhalte als Text. Die Anwendung behält CSP, gleiche Herkunft, Session und PostgreSQL-RLS. Auch Viewer dürfen lesen; fremde Versionen liefern 404. Bildexporte laufen lokal im Browser. Diagrammwerte werden nicht an externe Chart-Dienste gesendet. [ARIA-Unterstützung](https://echarts.apache.org/handbook/en/best-practices/aria/) ergänzt eine bedienbare Tabelle.

SVG/PNG enthalten Datenbasis, Version und gekürzten Hash. Filter stehen bei Detailansichten in der Bildbeschriftung. Vollständiger Hash und Originalwerte sind weiterhin in der Datenversion verfügbar. Diagrammeinstellungen bleiben auf die aktuelle Ansicht beschränkt; sie sind noch keine gespeicherten Dashboard-Definitionen.

## Verbleibender Ausbau

Exakte Histogramme über sämtliche Zeilen, frei konfigurierbare Aggregationen, Zeitachsen, Karten, Pivot-/Dashboard-Layouts und PDF-Berichte bleiben weitere Ausbauschritte. Vor solchen Erweiterungen werden zusätzliche Hintergrundaggregate benötigt; der Browser darf nicht unbemerkt aus einer Auswahl eine Vollauswertung machen.

Gezielte Ergebnisse und offene Prüfungen: [Visualisierungsbericht](../testing/M2_VISUALIZATION_REPORT.md).
