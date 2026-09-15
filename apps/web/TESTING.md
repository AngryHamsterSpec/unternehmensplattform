# Relevante Prüfungen

- pnpm build: TypeScript und Produktionsbundle.
- pnpm run format:check, pnpm run lint, pnpm test: Format, Hooks/Code und 17 Unitprüfungen, einschließlich Import-Entwurf beim Zuklappen und kombinierter Bestandsfilter.
- pnpm test:e2e: echte lokale OIDC-Anmeldung, Szenarien, Rollen und Mandanten, Tastatur, 390-Pixel-Ansicht, CSV/JSON/XLSX/Parquet bis Vorschau/Version/Export. Dichtewahl bleibt nach Neuladen erhalten; Filterleerzustände sind sichtbar.
- Für reine Gestaltung den größeren CSV-Lastfall gezielt auslassen: --grep-invert "CSV über 128 KiB". Die vollständige Suite bleibt für die Integrationsabnahme verfügbar.
- Alle Dateien und Konten für E2E sind synthetisch. e2e/fixtures/synthetisch.xlsx enthält ein Hinweisblatt und ein Datenblatt mit zwei Zeilen. Echte Zugangsdaten kommen ausschließlich aus lokaler Umgebung; keine Traces mit Zugangsdaten.

Die mobilen Browserprüfungen decken Öffnen/Schließen der Navigation, Escape und Fokusrückgabe ab. Der Parquet-Fall prüft den direkten Fokuswechsel zur Bereinigung. Alle Importfälle öffnen den Import über die sichtbare Hauptaktion. CSV-Formaterkennung/JSON/XLSX und Parquet verwenden den vorhandenen synthetischen Testmandanten B. Anlass war die während der Designprüfung erreichte damalige 100er-Quote; der Nutzer hat sie inzwischen zentral konfigurierbar gemacht, Default 1000. Diese manuelle Änderung bleibt erhalten. Ein künftig dauerhaft wiederholbarer Gesamtlauf benötigt eine eigene kurzlebige Testumgebung oder geregelte Testdatenverwaltung.

Docker-Teststage: docker build -f infra/proxy/Dockerfile --target test -t unternehmensplattform-web-tests .
Aktuelle tatsächliche Ergebnisse: [Produktdesign- und XLSX-Prüfbericht](../../docs/testing/M2_PRODUCT_XLSX_REPORT.md). Kein aktueller vollständiger Restore- oder 1-GiB-Neunachweis für diesen Designschritt.

Parquet verwendet dasselbe Importformular und erklärt die Anforderungen an flache Spalten und begrenzte Zeilengruppen. Der eigene Browserfall nutzt ausschließlich e2e/fixtures/synthetisch.parquet. [Parquet-Prüfbericht](../../docs/testing/M2_PARQUET_REPORT.md).

Der Browserfall „SQLite-Snapshot“ lädt e2e/fixtures/synthetisch.sqlite mit zwei synthetischen Tabellen, korrigiert die fehlende Auswahl am gespeicherten Original und prüft Vorschau, Version 2, Herkunft und bytegleichen Originaldownload. Gezielter Aufruf: pnpm test:e2e --grep SQLite-Snapshot. [Tatsächlicher Nachweis](../../docs/testing/M2_SQLITE_REPORT.md).

## M2-Erweiterung vom 14.09.2026

`DataIntelligence.test.tsx` verhindert die Anzeige bzw. versehentliche Öffnung eines alten Quellenresultats nach einem neuen Auftrag. Listen und Detailabrufe sind getrennt; Polling endet erst, wenn der ausgewählte Detailzustand abgeschlossen ist. `e2e/m2-intelligence.spec.ts` prüft die echte PostgreSQL-Quelle, wiederverwendbare Regeln, persistente Vollanalyse, Korrelationsmatrix/Zeitdiagramm, statischen Modus, Bericht-/SVG-Download und einen geprüften Plan bis zur ausdrücklich bestätigten Version. Abschließend werden Originalbytes und die 390-Pixel-Ansicht geprüft. Tatsächlich ausgeführte Ergebnisse: [M2-Abschlussbericht](../../docs/testing/M2_COMPLETION_REPORT.md).


Abschluss: 17 Frontendtests sowie Typprüfung, Lint und Build bestanden. Der neue M2-Browserworkflow besteht mit tatsächlichem OIDC; ein verzögerter Importauftrag blendet den alten Quellenverweis sofort aus. Der Restorefall wurde um Analysebericht und Ergebnis-Hash erweitert, aber im letzten Lauf wegen Timeout beim initialen Datenbankvergleich nicht erreicht; kein erfolgreicher neuer Restore-Browsernachweis. Auf diesem Windows-Host startete das gebündelte Chromium nicht; `E2E_BROWSER_CHANNEL=chrome` verwendet gemäß [Playwright-Dokumentation](https://playwright.dev/docs/browsers#google-chrome--microsoft-edge) den vorhandenen Chrome in einem isolierten Testprofil. Ohne Variable bleibt der bisherige Chromium-Standard erhalten.
