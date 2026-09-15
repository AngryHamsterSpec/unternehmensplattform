# Änderungen

## 2026-09-14 — M2 auf Nutzeranweisung abgeschlossen

- Datei- und PostgreSQL-Workflows, Vollanalysen, wiederverwendbare Regeln und versionierte Berichte integriert.
- Beaufsichtigte Bereinigungspläne mit Verifier, Vorschau und ausdrücklicher Versionsfreigabe ergänzt; optionaler Live-Adapter nur mit Test-Double geprüft.
- Veralteten Quellenverweis während verzögerter Importannahme korrigiert.
- PostgreSQL-Verträge, 17 Frontendtests, realer Browserworkflow und Betriebsgrenzen bestanden. Aktueller Restore-Nachweis bleibt nach Timeout beim initialen Prüfsummenvergleich offen.
- Zentrale Dataset-Quote **1000** und manuelle Änderungen erhalten. Stopp nach M2; M3 nicht begonnen. [Nachweis](docs/testing/M2_COMPLETION_REPORT.md).

## 2026-09-12 — CSV-Dateien bis 1 GiB

- Base64-Gesamtübertragung in der Oberfläche durch abschnittsweisen Upload mit Fortschritt, Pause, Fortsetzen und Abbruch ersetzt.
- PostgreSQL-Abschnittsspeicher, unveränderliche Versiegelung und additive Migration 0003 ergänzt.
- Worker-Leases, dateibasierte CSV-/SQLite-Verarbeitung, exakte Aggregate und Schutz vor Veröffentlichung nach Abbruch ergänzt.
- Indizierte Datenansicht und vollständige Streaming-Downloads für Originale und sichere Exporte.
- Exakt 1 GiB mit 262.144 Zeilen erfolgreich über HTTP importiert, verarbeitet und anhand beider Downloads gehasht; [Prüfbericht](docs/testing/M2_LARGE_CSV_REPORT.md).


## 2026-09-11 — M2: CSV-Datenwerkstatt

- Deutschen Ablauf für CSV-Import, Profiling, manuelle Bereinigung, Vorschau, Versionsbestätigung und sicheren Export ergänzt.
- Unveränderte Originalbytes, Ergebnis-Hashes, Pipeline und Urheber in vier neuen FORCE-RLS-Tabellen verknüpft.
- Begrenzten PostgreSQL-Worker mit Wiederanlauf, frischer Rechteprüfung und transaktionalem Speicheradapter ergänzt.
- Echte DB-, Browser-, Unicode-, Formel-, Mandanten-, Konkurrenz- und Widerrufsprüfungen hinzugefügt.
- Umfang und Grenzen: [M2-Prüfbericht](docs/testing/M2_CSV_REPORT.md) und [ADR 0005](docs/adr/0005-bounded-csv-data-workflow.md).

## 2026-09-11 — Phase 1: Härtung und Abnahme

- API auf verifiziertes offizielles Python-3.14.7-Alpine-Image umgestellt; 60 hohe/kritische API-Befunde beseitigt, gesperrte Python-Abhängigkeiten unverändert.
- Vollständigen Restore mit echtem OIDC-Login und historischem Ergebnishash ohne erneutes Demo-Seeding erfolgreich geprüft.
- Automatische Wiederaufnahme des Originalproxies auch bei Bereinigungsfehlern abgesichert.
- Neue HTTP-Messung bei 300 Szenarien: p95 210 ms Einzelabruf, 129 ms Liste, 314 ms Bewertung.
- Basisvergleich und vollständigen Wiederherstellungsablauf in ADR 0004 dokumentiert.

- Datenbankabfragen gebündelt und Lese-/Bewertungslatenzen unter dem Referenzziel gemessen.
- Verwundbare entbehrliche Image-Werkzeuge entfernt und Alpine-Bibliotheken aktualisiert.
- Eng begrenzte befristete Scannerbewertung samt neun Negativ-/Konfigurationstests ergänzt.
- Browserprüfung um gespeicherten XSS-Text, Header, Tastatur und schmale Ansicht erweitert; Umbruch langer Namen korrigiert.
- Containergrenzen, Ausfallprüfung und Test-Secretrotation im getrennten Restore-Ablauf ergänzt.
- Tatsächliche Ergebnisse und verbleibende Grenzen stehen im [Prüfbericht](docs/testing/PHASE_1_REPORT.md).

## 2026-09-10 — Phase 1 in Abnahme

- Deutsche Anwendung für OIDC-Anmeldung, Organisationen, versionierte Szenarien, Bewertungen, Vergleich und Audit implementiert.
- Deterministische Regeln, Dezimal-TCO, vier synthetische Architekturpläne und unabhängigen Verifier ergänzt.
- PostgreSQL-Migration mit getrennten Rollen, FORCE RLS, zusammengesetzten Fremdschlüsseln und unveränderlichen historischen Datensätzen erstellt.
- Optionalen OpenAI-Erklärungsport mit Datenminimierung, Zustimmung, Budgetreservierung, Idempotenz und unklarem Abschlusszustand ergänzt; kein Live-KI-Aufruf.
- Docker, gesperrte Abhängigkeiten, CI, echte DB-/Browsertests sowie Neustart-/Restore-Prüfskript hinzugefügt.
- Fehlerzustände bei Organisationswechsel und veralteten Frontendantworten korrigiert.
- Umsetzungsentscheidungen in ADR 0002 und Modul-README/EXPLAIN/TESTING dokumentiert. Tatsächliche Prüfresultate: docs/testing/PHASE_1_REPORT.md.


## 2026-09-09 — Phase 0

- Master Prompt und Phase-0-Auftrag als Anforderungen übernommen; Deutsch als Projektsprache festgelegt.
- System-, Daten-, Agenten- und Docker-Architektur entworfen.
- Bedrohungsmodell, Teststrategie, Anforderungsabdeckung und Meilensteine erstellt.
- Ersten vollständigen Funktionsablauf und späteren Phase-1-Umsetzungsauftrag definiert.
- Repository-Konventionen angelegt. Anwendung, Docker-Stack und CI sind noch nicht implementiert.


## 12.09.2026 — Visuelle Datenanalyse

Apache ECharts 6.1.0: sechs Diagrammtypen, interaktiver und statischer Modus, Zoom, Messwertfilter, vergrößerte Ansicht, Wertetabelle und SVG-/PNG-Export. Begrenzte Diagramm-API mit Versionshash und Originalzeilenpositionen. Neue synthetische Diagramm-Demo. Konsistenter Datensatzdetailabruf während paralleler Veröffentlichung. Gezielte Prüfungen gemäß Nutzerwunsch; Details im Visualisierungsbericht.
