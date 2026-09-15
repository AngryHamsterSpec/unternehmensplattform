# Datenintelligenz — Tabellenwerkstatt

Status: **IMPLEMENTIERT** im vereinbarten M2-Funktionsumfang; lokal integriert und geprüft. M2 auf Nutzeranweisung erledigt; **aktueller Restore-Nachweis wegen Prüfsummen-Timeout offen**. [M2-Abschlussbericht](../../../../../docs/testing/M2_COMPLETION_REPORT.md). Der frühere 1-GiB-Nachweis bleibt im [CSV-Prüfbericht](../../../../../docs/testing/M2_LARGE_CSV_REPORT.md) erhalten. Live-KI ist als separater optionaler Adapter weiterhin NICHT LIVE GETESTET.

Anmelden → Datenwerkstatt → synthetische UTF-8-CSV auswählen → Import starten → Fortschritt verfolgen → Qualitätsprofil prüfen → Bereinigungsschritte hinzufügen → Vorschau berechnen → als neue Version bestätigen → CSV exportieren.

Neue Dateien dürfen bis **1 GiB = 1.073.741.824 Bytes** groß sein. Der Browser überträgt Abschnitte bis 4 MiB. Uploads lassen sich pausieren, mit derselben Datei fortsetzen und abbrechen. Hintergrundaufträge haben Fortschritt, Lease, Wiederaufnahme und Abbruch. Original, Ergebnis und Export erhalten eigene SHA-256-Prüfsummen. Ein Download lädt die Gesamtdatei nicht in den JavaScript-Arbeitsspeicher.

CSV und JSON haben keine feste Zeilen- oder Gesamtzellenanzahlgrenze; Excel besitzt zusätzliche Formatgrenzen. Verbleibende Schutzgrenzen: 256 Spalten, 1.048.576 Zeichen je Zelle, 4 MiB je normalisiertem Datensatz, zehn Bereinigungsschritte und 8 GiB je Ableitung. Anzeigen kürzen einzelne Werte auf 512 Zeichen; vollständige Werte bleiben im Original und Export. Kennzahlen, verschiedene Werte, Häufigkeiten und Duplikate beziehen sich auf alle Zeilen. Das Basisprofil berechnet keine IQR-Hinweise; diese stehen in der ausdrücklich gestarteten Vollanalyse bereit.

Je Organisation: höchstens drei offene Uploads, 20 GiB reservierte/gespeicherte Dateiabschnitte, standardmäßig **1000 Datensätze** (zentral über `dataset_limit_per_organization` konfigurierbar), 500 Import-/Vorschauaufträge und zehn wartende/laufende Import-/Vorschauaufträge. Die zusätzlichen Analyse-/Quellen-/Planaufträge besitzen die unten genannten eigenen Grenzen. Importpfade verwenden `check_dataset_quota(db)`; die beabsichtigte Nutzeränderung bleibt erhalten. Je Datensatz höchstens 20 Versionen. Abgebrochene offene Uploads geben ihre Abschnitte frei; abgeschlossene Originale und Versionen bleiben unveränderlich.

Lesekonten dürfen vorhandene Daten sehen und herunterladen. Organisationsadministration und Architekturanalyse dürfen importieren und transformieren. Eine Vorschau wird erst durch explizite Bestätigung zur neuen Version.

Start: `docker compose up --build -d --wait`. Der Worker nutzt 256 MiB, eine CPU, das interne Datennetz und das temporäre Arbeitsvolume `data-work`. SQLite-Sortierungen liegen ebenfalls dort. Mindestens das Sechsfache der Quelldateigröße plus 256 MiB freier Arbeitsplatz wird vor Verarbeitung geprüft. DATA_WORKER_ORGANIZATION_IDS benennt die zugelassenen Mandanten; keine OIDC-/KI-/Migrationszugänge im Worker.

Weitere Erklärungen: [EXPLAIN.md](EXPLAIN.md), [TESTING.md](TESTING.md), [ADR 0006](../../../../../docs/adr/0006-gib-csv-streaming.md).

Direkte PostgreSQL-Quellen, Qualitätsregeln, Vollstatistik und geprüfte Pläne sind unten beschrieben. Die lokale Browser- und Betriebsprüfung ist bestanden. Der aktuelle Restore-Lauf brach beim anfänglichen Prüfsummenvergleich ab; dieser Nachweis bleibt offen. Spätere Betriebsoptionen sind verteilte Verarbeitung, S3 und administrative Aufbewahrung; sie werden nicht als implementiert behauptet.


## Diagramme

Die SQLite-Erweiterung verwendet dieselbe Diagrammansicht wie alle anderen tabellarischen Quellen.

Die deutsche Datenversion enthält eine visuelle Analyse mit sechs Diagrammtypen, interaktivem und statischem Modus, Filtern, Zoom, Wertetabelle sowie SVG-/PNG-Export. Das zusätzliche Diagramm-Beispiel enthält 180 synthetische Vertriebszeilen.

visualization.py liest für zwei Spalten maximal 300 Zeilen aus höchstens zwölf Abschnitten. Die Auswahl begleitet immer die Datenversion samt Hash und Originalpositionen; vollständige Profile liefern unabhängig davon exakte Häufigkeiten und Fehlwerte. ECharts läuft lokal im Webfrontend. Keine neue Migration oder externe Dashboard-Infrastruktur.

## Robuste Leseeinstellungen

Standard ist automatische Trennzeichenerkennung. UTF-8 und UTF-16 mit BOM werden erkannt; Windows-1252 kann ausdrücklich gewählt werden. Dateien ohne Kopfzeile benötigen die entsprechende Auswahl. Fehlgeschlagene Originalimporte können mit neuen Leseoptionen ohne erneuten Upload wiederholt werden. [ADR 0008](../../../../../docs/adr/0008-csv-format-und-wiederaufnahme.md).

## JSON und JSONL

Dateien mit .json (Array flacher Objekte) oder .jsonl (ein Objekt je Zeile) verwenden denselben Upload und Versionsworkflow. Nur UTF-8 mit optionalem BOM; null und fehlende Schlüssel werden in der Ableitung leer. Doppelte Schlüssel, spätere Zusatzspalten und verschachtelte Werte werden abgewiesen. Die Oberfläche erklärt diese Abbildung. Originaldownload bleibt unverändert; bereinigte Tabellen werden als CSV exportiert. [JSON-Nachweis](../../../../../docs/testing/M2_JSON_REPORT.md).

## XLSX-Arbeitsblätter

Der Abschnittsupload akzeptiert .xlsx. Arbeitsblattnummer 1–100 auswählen; erste nichtleere Zeile enthält standardmäßig Spaltennamen. Eine XLSX-Datei bleibt als Original erhalten, Ableitungen verwenden dieselben Profile, Vorschauen, Bestätigungen und CSV-Exporte.

Keine Formelberechnung: Formel- und Excel-Fehlerzellen werden ausdrücklich abgewiesen. Datums-/Zeitwerte werden ISO-Texte, Wahrheitswerte true/false, fehlende Zellen leer. Zahlenformate (etwa angezeigte führende Nullen) und verbundene Zellbereiche werden nicht nachgebildet. Verdeckte ausgewählte Blätter, Makros, externe Arbeitsmappen und eingebettete Objekte sind unzulässig. Für große Excel-Textbestände CSV verwenden.

Grenzen: 2 GiB entpackt, 2.048 ZIP-Mitglieder, 2 MiB Zentralverzeichnis, 16 MiB Metadaten und 4 MiB gemeinsame Texttabelle. Kein ZIP64/Mehrteilarchiv. XML wird vor dem Reader begrenzt geprüft; keine DTD/Entitäten. Datenblattadressen müssen geordnet und eindeutig sein, innerhalb der ersten 256 Spalten und der Excel-Zeilengrenze. [ADR 0011](../../../../../docs/adr/0011-xlsx-tabellenadapter.md).

## Parquet

Einzelne .parquet-Dateien sind im selben Abschnittsupload zugelassen. Spaltennamen kommen aus dem Dateischema. Flache Strings, Ganzzahlen, endliche Zahlen, Dezimalwerte, Wahrheitswerte und Datums-/Zeitwerte werden als Stringtabelle weiterverarbeitet; null wird leer. Verschachtelte oder binäre Spalten benötigen vorherige Aufbereitung. Originaldatei und Herkunft bleiben erhalten; bereinigte Versionen werden als CSV exportiert.

Vorprüfung: PAR1-Marker, höchstens 8 MiB Metadaten, 4.096 Zeilengruppen, 256 Spalten, 64 MiB deklarierte entpackte Daten je Gruppe und 8 GiB insgesamt. Keine verschlüsselten Dateien, Verzeichnis-/Cloud-/Globimporte oder externen Spalten. Größere Gruppen bitte beim Export aufteilen. Der 1-GiB-Upload ist kein pauschaler Nachweis für jede komprimierte Parquet-Datei. [ADR 0012](../../../../../docs/adr/0012-parquet-tabellenadapter.md).

## SQLite-Datenbanksnapshots

Eine vollständige SQLite-Sicherung mit Endung `.sqlite`, `.sqlite3` oder `.db` importieren. Bei mehreren gewöhnlichen Tabellen den genauen Namen im Feld „SQLite-Tabelle“ angeben; ein fehlender/falscher Name kann am gespeicherten Original korrigiert werden. Bei genau einer Tabelle ist die Angabe optional. Der Dateiname allein legt keinen Tabellennamen fest.

Nur unverschlüsselte konsistente Sicherungen im DELETE-Journalmodus; keine einzeln kopierten offenen Datenbanken oder WAL-Hauptdateien. Views, virtuelle Tabellen, berechnete/versteckte Spalten, Binärwerte und unendliche Zahlen vorher aufbereiten. NULL wird leer; Quelle und Tabellenname bleiben in Profil und Folgeversionen sichtbar. Bereinigung wird erst nach Vorschau und Bestätigung veröffentlicht, Export als CSV. Keine Liveverbindung zu fremden Datenbanken. [ADR 0013](../../../../../docs/adr/0013-sqlite-datenbanksnapshots.md).

## M2-Erweiterung vom 14.09.2026

Der Code ergänzt die vorhandenen Formate um direkte PostgreSQL-Snapshots, Vollanalysen, Qualitätsregelsätze, analytische HTML-/JSON-Berichte und beaufsichtigte Bereinigungspläne. Der tatsächliche Prüf-/Betriebsstand steht im [Abschlussbericht](../../../../../docs/testing/M2_COMPLETION_REPORT.md); der vereinbarte Funktionsumfang ist integriert und geprüft; der Meilenstein ist auf Nutzeranweisung mit offen dokumentiertem Restore-Nachweis erledigt.

Im Datensatz **Qualität & Statistik → Analyse konfigurieren** öffnen, höchstens acht numerische Spalten und optional Zeitspalte/Kennzahl wählen. Ohne numerische Auswahl gelten die ersten acht erkannten Zahlenspalten. Pflichtwert-, Eindeutigkeits-, Typ-, Zahlenbereichs- und Wertelistenregeln lassen sich als unveränderliche, versionierte Regelsätze speichern und wiederverwenden. Vollanalysen enthalten R7-Quartile, Stichproben-Standardabweichung, Histogramme, IQR-Hinweise, paarweise Pearson-Korrelationen und UTC-Tages-/Monatsaggregate. Alle Zeilen werden geprüft, höchstens die ersten 1000 Zeitperioden dargestellt. Das frühere Basisprofil berechnet weiterhin keine IQR-Hinweise; hierfür die Vollanalyse starten. Berichte enthalten Methodik, Grenzen, Original-/Quell-/Ergebnishash, Ersteller und Zeitpunkte. Interaktive/statische Diagramme und SVG-Export verwenden das gemeinsame Designsystem.

`python scripts/setup_local.py` legt eine leere `.local/data-sources.json` nur dann an, wenn keine Registry existiert. `python scripts/setup_data_source_demo.py` ergänzt einmalig eine getrennte synthetische PostgreSQL-Quelle mit SELECT-Rolle und wirksamer Quellen-RLS. Bestehende Quellen und Plattformdaten werden nicht überschrieben. In der Datenwerkstatt **Datenbankquelle importieren** öffnen, Quelle/Tabelle und Namen wählen, anschließend den gespeicherten Snapshot im normalen Importablauf öffnen.

Eigene Quellen registriert der Betreiber mit `id`, `name`, `organizations` (UUID-Liste), `host`, `port`, `database`, `user`, `password`, `sslmode: verify-full`, optionalem `sslrootcert` und erlaubten `tables` als `schema.table`. Registry und TLS-Vertrauensmaterial werden geschützt und nur lesbar gemountet. Keine Zugangsdaten im Repository, keine freie Nutzer-SQL-Eingabe. Externe Quelldatenbanken gehören nicht zum Plattformbackup; erfasste Snapshots und ihre Referenzen dagegen vollständig.

Unter **Assistierte Bereinigungsplanung** entstehen begründete regelbasierte Vorschläge, ausdrücklich keine KI. Der echte optionale OpenAI-Adapter kann aus belegten Kandidaten wählen; benötigt werden Organisationsfreigabe, Modell, Preisstand, Tagesbudget und ausdrückliche Zustimmung. Übertragen werden nur aggregierte Zähler und anonymisierte Kandidateninformationen. Status ohne echten Anbieternachweis: **NICHT LIVE GETESTET / BENÖTIGT EXTERNE ZUGANGSDATEN**. Der Verifier lehnt unbekannte Schritte und veraltete Quellen ab. Ein geprüfter Plan darf nur eine Vorschau anstoßen; erst die ausdrückliche Bestätigung erstellt eine neue Datenversion. Keine Modellskripte oder automatischen Wiederholungen nach unklarem KI-Ausgang.

Der separate `intelligence-worker` besitzt 256 MiB/1 CPU, eigene Arbeitsplatte, 90-Sekunden-Lease, höchstens drei Versuche und 30 Minuten pro Versuch. Zehn aktive und 10.000 gespeicherte Analyse-/Quellen-/Planaufträge, 500 Regelsatzversionen und 8 GiB temporäre Statistikdaten begrenzen Ressourcen. Die zentrale Dataset-Quote mit Default **1000** bleibt erhalten. [ADR 0014](../../../../../docs/adr/0014-datenanalyse-quellen-und-gepruefte-plaene.md).
