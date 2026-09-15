# ADR 0014 – Datenanalysen, registrierte Quellen und geprüfte Bereinigungspläne

Datum: 14.09.2026 · Entscheidung implementiert; technische Abschlussnachweise im [M2-Abschlussbericht](../testing/M2_COMPLETION_REPORT.md).

## Kontext

Der vollständige Modul-C-Umfang benötigt über Dateiimport und manuelle Bereinigung hinaus fachliche Qualitätsregeln, vertiefte Statistik, analytische Berichte, echte Datenbankquellen und beaufsichtigte KI-Vorschläge. Die vorhandene unveränderliche Datenpipeline, zentrale Dataset-Quote mit Default 1000, RLS und menschliche Versionsfreigabe bleiben maßgeblich. M3 ist nicht aktiviert.

## Entscheidung

`data_tasks` ergänzt die vorhandenen Import-/Vorschaujobs um ANALYSIS, SOURCE und PLAN. Ein eigener Worker verarbeitet Analysen und Quellen. Der bisherige Dateiworker behält ausschließlich sein internes Datennetz. Beide Worker haben 256 MiB, eine CPU, ein eigenes Arbeitsvolume, einen schreibgeschützten Root und ausschließlich Anwendungs-DB-Zugang. Der Quellenworker erhält zusätzlich Egress und eine nur lesbare Betreiberregistrierung; keine Identitäts-, Migrations- oder Modellgeheimnisse.

Aufträge binden Organisation, Ersteller, Quellversion, Eingabehash und Idempotenzschlüssel. RLS wird erzwungen; Schreibrechte werden vor Aufnahme, während der Lease und vor Veröffentlichung erneut geprüft. Lease: 90 Sekunden, Heartbeat höchstens alle zwei Sekunden, höchstens drei Versuche, Gesamtverarbeitung höchstens 30 Minuten pro Versuch. Abbruch verhindert Veröffentlichung. Fertige Zustände und Resultate sind durch DB-Trigger unveränderlich. Wiederholen erzeugt einen neuen nachvollziehbaren Auftrag. Listen laden ausschließlich Metadaten; Ergebnisse werden einzeln abgerufen.

### PostgreSQL

Der Betreiber registriert pro Organisation erlaubte Tabellen und eine begrenzte Quellenrolle. Nutzer wählen keine Hosts, DSNs oder SQL-Texte. TLS ist standardmäßig `verify-full`; die einzige unverschlüsselte Ausnahme ist die konkrete lokale synthetische Quelle `postgres/source_demo/source_reader` im Demo-/Testbetrieb. Plattform-, Identitäts- und Systemdatenbanken sind gesperrt. Superuser-, Rollenverwaltungs- und RLS-Bypass-Rollen werden abgelehnt. Die Rolle benötigt nur CONNECT, USAGE und SELECT; RLS der Quelle bleibt wirksam.

Ein lesender Repeatable-Read-Auftrag sperrt die freigegebene Tabelle gegen konkurrierende DDL, prüft Schema und Zeilengrößen und streamt CSV über COPY. Bezeichner werden als Bezeichner gequotet, Metadatenwerte als Parameter gebunden. Zulässig sind gewöhnliche Tabellen und partitionierte Tabellen mit Standardtypen, höchstens 256 Spalten, Namen bis 100 Zeichen, begrenzte Datensätze und höchstens 1 GiB Snapshot. Views, Fremdtabellen und benutzerdefinierte Typen sind nicht Teil dieses Adapters. Die Prüfung großer Zeilen erfolgt vor COPY im selben Snapshot. Ein separater Lease-Monitor kann auch blockierte Quellenabfragen abbrechen; Verbindungs-, Lock-, Statement- und Transportzeitgrenzen sind gesetzt.

Der Snapshot erhält Hash, Tabelle, Erfassungszeit, Datenbanktypen und Quellenkennung. Veröffentlichung von Original, Dataset, Importjob und Auftragsresultat erfolgt atomar. Danach verarbeitet der bestehende Dateiworker den Snapshot. Änderungen der Quellenregistrierung während des Imports verhindern die Veröffentlichung. Eine registrierte Quelle ist eine Vertrauensentscheidung des Betreibers, keine Möglichkeit zum Ausführen beliebiger Nutzer-SQLs. Zusätzliche Unternehmensnetze sollten Egress separat auf die registrierten Quellen beschränken.

### Analyse und Regeln

Die Analyse prüft zuerst die gespeicherte Versionsprüfsumme. Sie verarbeitet alle Zeilen mit begrenztem RAM und einem temporären SQLite-Index. Auch ältere Inline-Versionen werden unterstützt. Numerische Vollanalysen sind auf acht ausgewählte Spalten begrenzt. Dezimalwerte, lineare R7-Quantile, Stichproben-Standardabweichung, zehn Histogrammklassen und 1,5-IQR-Hinweise sind deterministisch. Pearson verwendet paarweise gültige Werte; konstante Spalten ergeben keinen Koeffizienten. Weder Ausreißerhinweis noch Korrelation begründen automatisch eine fachliche Korrektur.

Zeitreihen verwenden ISO-Kalenderdaten bzw. Zeitstempel mit explizitem Offset, normalisiert auf UTC. Es gibt Tages-/Monatsaggregate, keine erfundenen Zwischenperioden; Berichte enthalten höchstens die ersten 1000 Perioden und die tatsächliche Gesamtanzahl. Ungültige und fehlende Daten bleiben getrennt sichtbar. Temporäre Statistikdaten sind auf 8 GiB begrenzt; fehlender Plattenplatz führt zu einem sichtbaren Fehler.

Unveränderliche `data_rule_sets` enthalten Pflichtwert-, Eindeutigkeits-, Typ-, Bereichs- und Wertelistenregeln. Neue Fassungen referenzieren ihren Vorgänger. Analysen enthalten den verwendeten Regelsatz als Snapshot. Der Qualitätsscore ist das gleichgewichtete Mittel von Vollständigkeit, Eindeutigkeit ganzer Zeilen und optionaler Regelkonformität; leere Daten erhalten keinen Score. HTML-/JSON-Berichte binden Quelle, Original, Ergebnis, Ersteller und Zeitpunkte. HTML escaped alle Daten und lädt weder Skripte noch externe Ressourcen.

### Agenten und menschliche Freigabe

Der Datenplan folgt Supervisor → Data Manager → Cleaning Specialist → Verifier → Risk Reviewer → Cost Estimator → Approval Gate. Dies sind durch Anwendungscode durchgesetzte Verantwortlichkeiten; die Rollenanzeige behauptet keine sieben unabhängigen LLM-Aufrufe. Regelbasierte Vorschläge sind ausdrücklich keine KI. Der optionale OpenAI-Adapter liefert eine strukturierte Auswahl aus belegten Kandidaten-IDs. Er erhält aggregierte Zähler und anonymisierte IDs/Operationen, keine Zellen, Spaltennamen, Nutzer- oder Organisationskennungen.

Externe Verarbeitung benötigt explizite Zustimmung, Organisationsfreigabe, konfiguriertes Modell/Preisstand und konservativ reserviertes gemeinsames Tagesbudget. Höchstens 8000 Eingabetokens als konservative Bytegrenze, 1200 Ausgabetokens, zehn Sekunden und ein Aufruf ohne Tools, Speicherung oder automatische Retries. Ein unabhängiger Verifier lehnt unbekannte/duplizierte Kandidaten und ungültige Spalten ab. Keine frei generierten Transformationsschritte und kein Modellcode werden ausgeführt. Ein unklarer externer Ausgang wird nicht automatisch erneut beauftragt; die Reservierung bleibt bestehen.

Ein Plan ist an Quellversion und Hash gebunden. Er darf nur eine vorhandene typisierte Vorschau anstoßen. Die Versionsübernahme benötigt weiterhin ausdrückliche Bestätigung und einen passenden Vorschauhash. Manuelle Bereinigung bleibt vollständig nutzbar. Live-KI ist ohne echten Anbieternachweis ausdrücklich **NICHT LIVE GETESTET**.

## Alternativen und Folgen

Ein allgemeiner SQL-Editor, frei erzeugte Bereinigungsskripte oder Netzfreigabe des bestehenden Dateiworkers hätten die Vertrauensgrenzen unnötig erweitert. Ein zusätzliches verteiltes Framework ist für diesen begrenzten Umfang nicht erforderlich. Die gemeinsame React-/ECharts-Infrastruktur bleibt erhalten; neue Visualisierungen nutzen dieselben semantischen Farben, Typografie, Tabellen und Dichteoptionen.

Weitere Quellen werden über den Quellenvertrag und denselben Snapshotablauf ergänzt. Weitere Analysten müssen typisierte Ergebnisverträge, reproduzierbare Berechnungen, Ressourcenbudgets, RLS und Nachweise erhalten. Clustering und Prognosen werden erst bei einem konkreten fachlichen Bedarf implementiert; keine leeren ML-Gerüste. Spätere Prozess-, Cloud-, Security- und Agent-Factory-Module werden mit dieser Entscheidung nicht vorweggenommen.

## Referenzen

- [Psycopg COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html), [Verbindungen und sichere Cancellation](https://www.psycopg.org/psycopg3/docs/api/connections.html)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [ECharts Heatmap-Vertrag](https://github.com/apache/echarts-doc/blob/master/en/option/series/heatmap.md)
- [Master Prompt](../requirements/MASTER_PROMPT_ORIGINAL.md), [Agentenhierarchie](../AGENT_HIERARCHY.md), [Abschlussauftrag](../prompts/M2_COMPLETION_SCOPE.md)
