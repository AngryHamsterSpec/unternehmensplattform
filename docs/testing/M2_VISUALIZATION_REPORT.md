# M2 — Moderne Datenvisualisierung

Stand: 12.09.2026. Implementierung mit Apache ECharts 6.1.0. [Architekturentscheidung](../adr/0007-interaktive-datenvisualisierung.md).

## Prüfstrategie

Auf ausdrücklichen Nutzerwunsch kurze, gezielte Prüfungen. Der bereits erfolgreiche vollständige 1-GiB-Lasttest wird nicht wiederholt. Keine erneute komplette M1- oder Betriebsabnahme nur wegen der Diagrammbibliothek.

## Bisherige Ergebnisse

- TypeScript-/Vite-Build, ESLint und Prettier bestanden.
- 14 kurze Frontendtests bestanden, davon vier neue Fälle: fehlende/überlaufende Zahlen, Histogrammgrenzen, vollständige Ringanteile und Filter.
- Fünf gezielte PostgreSQL-Fälle bestanden (15,76 Sekunden): alte und neue Datenversionen, 300-Zeilen-Grenze, Originalpositionen, deterministische Wiederholung, Spaltenvalidierung, Viewer, Fremdmandant Textkürzung und konkurrierende Veröffentlichung während des Detailabrufs.
- npm-Laufzeitaudit: sechs Abhängigkeiten, keine gemeldeten Schwachstellen.
- Strenge mypy-Prüfung über 45 Quelldateien bestanden. Ruff: 92 Dateien bereits formatiert, Lint erfolgreich.
- Gezielter echter OIDC-/Chromium-Browserablauf bestanden: ein Fall in 15,1 Sekunden (17 Sekunden Gesamtausführung). Sechs Diagrammtypen, SVG-Inhalt/Versionshinweis, PNG-Signatur, Wertefilter, ungültige Grenzen, statischer Modus, vergrößerte Ansicht, 390-Pixel-Breite sowie bestehende Vorschau/Bestätigung/Versionen/CSV-Export/Leserechte/Mandantenschutz.
- Eine zunächst nicht eindeutig über das Label auffindbare Modusauswahl erhielt ein explizites aria-label; derselbe Browserfall bestand danach.
- Sichtprüfung der synthetischen Vertriebsanalyse mit 180 Zeilen im Anwendungsbrowser; Kennzahlen-Umbrüche und die Aussage bei vollständiger kleiner Auswahl verbessert. Abschließender TypeScript-/Vite-Build ebenfalls bestanden.
- Vier Prüfungen der Restore-Bereinigung bestanden. Dokumentationsprüfung: 64 Markdown-Dateien und 179 interne Links.

Der erste ECharts-Build erzeugte ein nachgeladenes Diagrammmodul mit etwa 636 kB minifiziert / 216 kB gzip. Vite meldet dafür die reguläre 500-kB-Chunkwarnung. Das Modul ist vom etwa 269-kB-Hauptbundle getrennt und wird bei Datenversionen benötigt; kein global geladenes CDN.

## Funktionsgrenzen

Balken/Ring/Qualität beruhen auf dem gesamten gespeicherten Profil. Histogramm/Linie/Streudiagramm beruhen auf maximal 300 systematisch ausgewählten Zeilen aus bis zu zwölf Abschnitten; nur bei vollständig enthaltenen kleinen Datenständen gilt „alle Zeilen“. Auswahl ist nicht zufällig, mögliche Verzerrung wird angezeigt. Bildexporte enthalten die Datenbasis.

Noch keine exakten frei wählbaren Aggregate über eine beliebig große Datei, keine automatische Zeitreiheninterpretation, kein PDF-Bericht und keine gespeicherten Dashboard-Layouts. [1-GiB-Nachweis](M2_LARGE_CSV_REPORT.md) bleibt separat erhalten.


## Nachweise und verbleibende Betriebsprüfung

Die 1-GiB-Erweiterung hat einen eigenständigen Last-/Runtime-/Security-Nachweis. Ihr erneuter vollständiger Restorelauf bleibt nach dem gefundenen und jetzt korrigierten Kopf-/Versionskonflikt offen. Das wird hier nicht als bestandene Restore-Abnahme ausgegeben.

Der neue Runtime-Abhängigkeitsscan ersetzt keinen vollständigen neuen Scan sämtlicher Basisimages. Die vorherige Imageinventur und ihre Keycloak-Grenzen stehen im 1-GiB-Bericht.


## Vorhandene 1-GiB-Datei und Sichtnachweis

Die neue API las die bereits gespeicherte synthetische 1-GiB-Version: 262.144 Zeilen insgesamt, 300 Auswahlzeilen, erste Zeile 1 und letzte Zeile 262.144. Antwortgröße 15.327 Bytes, serverseitig gemessener Abruf 1.331,15 ms. TestClient einschließlich regulärer synthetischer Sessioneinrichtung: 6,859 Sekunden. Echte PostgreSQL-Abschnitte; kein erneuter Upload, kein vollständiges Profiling und keine zusätzliche Nginx-Lastmessung.

[Ansicht der interaktiven Vertriebsanalyse](../screenshots/m2-interaktive-diagramme.png). Nach dem letzten Darstellungsbuild wurden SVG- und PNG-Export zusätzlich im Anwendungsbrowser ohne Exportfehlermeldung ausgelöst. [Maschinenlesbare Nachweise](m2-visualization-evidence.json).
