# Produktgestaltung und XLSX — tatsächlicher Nachweis

Hauptprüfung: 12.09.2026; mobiler Abschluss: 13.09.2026. Lokale Windows-/Docker-Demo. Kein produktiver Release, kein Remote-CI-Lauf. M2 insgesamt **TEILWEISE IMPLEMENTIERT**.

## Lieferumfang

Fokussierter [Produktdesignreview](../PRODUCT_DESIGN_REVIEW.md) vor der Umsetzung. IT-Kompass besitzt jetzt ein gemeinsames [Designsystem](../DESIGN_SYSTEM.md): semantische Rollen, lokal ausgelieferte IBM Plex Sans, eigene SVG-Symbole, zurückhaltende Flächen, konsistente Formulare/Tabellen, normale und kompakte Dichte, Filter und Cursor-Nachladen. ECharts verwendet dasselbe Farbsystem. Keine Migration der funktionierenden React-Komponenten.

XLSX ergänzt CSV und JSON/JSONL um einen kontrollierten Arbeitsblattadapter. Originalbytes, Importoptionen, Profil, Vorschau, bestätigte Version und Exporte bleiben verknüpft. Formelzellen werden mit konkreter Meldung zurückgewiesen; keine Verwendung ungeprüfter Cachewerte. ZIP/XML-Vorprüfung und Reader teilen die bestehenden Worker-/Freigabegrenzen. [ADR 0011](../adr/0011-xlsx-tabellenadapter.md).

## Ausgeführte erfolgreiche Prüfungen

| Prüfung | Ergebnis |
| --- | --- |
| CSV-/JSON-/XLSX- und Streaming-Unitprüfungen | **53 bestanden**, 12,63 s; davon 16 XLSX-Fälle |
| Echte PostgreSQL-Abläufe XLSX, JSON/JSONL, CSV-Wiederaufnahme | **4 bestanden**, 16,37 s; Originalgleichheit, RLS, Vorschau, Bestätigung, Export und XLSX-Blattherkunft |
| mypy im Linux-Testimage | **48 Quelldateien**, keine Fehler |
| TypeScript/Vite, Prettier, ESLint | bestanden |
| Bestehende Frontend-Unitprüfungen | **14 bestanden**, 7,03 s |
| Chromium-E2E mit echtem OIDC | **5 bestanden**, 54,9 s |
| Quellscan Trivy 0.74.0 | Scannerfixture erkannt; keine Geheimnisse oder Paketbefunde im Quellscan |
| pip-audit für gesperrte Python-Laufzeitabhängigkeiten | keine bekannten Schwachstellen gemeldet |

Die fünf Browserabläufe umfassen Architekturvergleich und Mandantenschutz, Leserechte, XSS/Textdarstellung, Header, Tastatur und 390px, CSV inklusive aller Diagrammtypen und SVG/PNG-Export sowie CSV-Reparatur mit langem Textfeld und JSON/XLSX bis Version 2. Ergänzend geprüft: Dichtewahl nach Neuladen, Filterleerzustand und XLSX-Blattauswahl.

Sichtprüfung im eingebauten Browser: Login, Szenarien und synthetische Vertriebsanalyse. Eine bei mittlerer Breite entdeckte ungünstige Tabellenumbruchregel wurde durch stabile Lesebreite und internes Scrollen korrigiert. Schriftdateien sind lokal inklusive OFL-Lizenz und Herkunftshashes vorhanden.

[Desktop-Datenansicht](screenshots/design-data.png) · [390-Pixel-Nachweis](screenshots/design-mobile.png). Der mobile Sicherheitstest enthält absichtlich sichtbaren, inerten Testtext.

## Reproduktion

- python -m pytest apps/api/tests/test_xlsx_format.py apps/api/tests/test_json_format.py apps/api/tests/test_csv_import_options.py apps/api/tests/test_stream_engine.py -q
- docker compose --profile test run --rm --no-deps tests python -m pytest -q -p no:cacheprovider /app/tests/test_xlsx_integration.py /app/tests/test_json_integration.py /app/tests/test_import_retry_integration.py
- docker compose --profile test run --rm --no-deps tests python -m mypy --cache-dir /tmp/mypy /app/src/platform_app
- docker build -f infra/proxy/Dockerfile --target test -t unternehmensplattform-web-tests .
- python scripts/run_e2e.py --isolated (für den gezielten Lauf vorhandene Installation und --grep-invert "CSV über 128 KiB" verwendet)
- python scripts/check_security.py --sources-only
- python -m pip_audit --no-deps --disable-pip -r apps/api/requirements.lock

Bei DB-Prüfungen den regulären Projektworker pausieren; nach der Prüfung wieder starten. Der Nachweis verwendete den aktuellen Quellstand per schreibgeschütztem Bind-Mount im Testimage. Lokale Windows-Tests benötigen einen schreibbaren temporären Pfad.

## Grenzen und offene Roadmap

Der bereits bestandene 1-GiB-CSV-Lastlauf und der große 450.000-Zeilen-Browserfall wurden bewusst nicht wiederholt. Ebenso keine vollständige erneute Restore- oder Containerinventur für diesen Schritt. Die bestehenden Betriebsgrenzen gelten weiter.

XLSX: ein gewähltes sichtbares Blatt; maximal 256 Spalten, 2 GiB entpackt, 16 MiB Metadaten, 4 MiB gemeinsame Texttabelle; zusätzliche ZIP/XML-Grenzen gemäß ADR. Kein XLS/ODS, ZIP64, Makro-/Formelbetrieb oder Mehrblatt-Zusammenführung. Excel-Anzeigeformatierung ist nicht der importierte Zellwert. Bei großen textreichen Excel-Dateien CSV verwenden. Kein XLSX-Lastnachweis bei 1 GiB.

Parquet, Datenbankquellen, weitergehende Statistik/Qualitätsregeln und beaufsichtigte KI-Transformationsvorschläge bleiben offen. Die Agentenplattform bleibt gemäß Mastermandat geplant: typisierte Spezialistentools, deterministische Berechnung/Rechte, unabhängige Prüfung und ausdrückliche Bestätigung. Keine neue Live-KI oder Produktionsreife behauptet.

## Mobiler Abschluss am 13.09.2026

Die letzte Sichtkorrektur gibt Tabellen mit mindestens vier Spalten in schmalen Fenstern eine stabile Mindestbreite; der vorhandene Tabellenbereich übernimmt das horizontale Scrollen. Produktionsbuild erneut bestanden, nur Web aktualisiert. Der betroffene 390px-/Tastatur-/XSS-Browserfall wurde gezielt erneut ausgeführt: **1 bestanden, 9,3 s** einschließlich Start. Keine Wiederholung der übrigen Testpakete.

Webimage: sha256:dec3637479940f81b1a393fab5ea7b39f39a6ace94f10a85f9af8543cd28e463. API, PostgreSQL und Web melden gesund; Datenworker und IdP laufen. Der zunächst durch ein Nutzungslimit der automatischen Freigabeprüfung blockierte Build konnte anschließend regulär abgeschlossen werden. Keine offene Freigabeblockade.
