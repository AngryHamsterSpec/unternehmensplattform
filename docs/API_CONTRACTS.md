# API-Verträge — Phase 1

Stand: 10.09.2026. Implementierter Vertrag unter /api/v1; Laufzeitnachweise im [Prüfbericht](testing/PHASE_1_REPORT.md). Die Pydantic-Domänenschemas und daraus generierten TypeScript-Typen liegen unter docs/contracts und apps/web/src/generated. Änderungen gegenüber dem Phase-0-Entwurf begründet [ADR 0002](adr/0002-phase1-runtime-and-contracts.md).

## Gemeinsame Regeln

JSON mit ISO-Datum/Zeit, UTC und Dezimalwerten als Strings. Unbekannt ist null. Der Server ermittelt Nutzer und Organisation aus der Sitzung; der Body kann diese nicht festlegen. Opaque Sessioncookies sind HttpOnly, SameSite=Lax und außerhalb der ausdrücklich lokalen HTTP-Demo Secure mit __Host-Präfix. Mutationen brauchen den X-CSRF-Token aus /me und die exakte freigegebene Origin.

Jeder Fehler hat eine deutsche Erklärung und eine request_id. Validierungsfehler geben Feldpfade und Fehlercodes ohne rohe Eingabewerte zurück. 401 bedeutet fehlende Sitzung, 403 fehlende Freigabe, 404 fehlendes oder mandantenfremdes Objekt, 409 Revisions-/Idempotenzkonflikt, 422 ungültige Eingabe, 429 Limit, 503 nicht verfügbare Abhängigkeit. Unerwartete Fehler liefern eine generische 500-Antwort.

Listen nutzen items und gegebenenfalls next_cursor; Standardschnitt 25, Maximum 100. Cursor enthalten Zeit und UUID, verleihen aber keine Rechte. JSON-Anfragen sind auf 256 KiB begrenzt; ausschließlich PUT-Uploadabschnitte dürfen bis 4 MiB enthalten. Alle API-Antworten erhalten no-store, nosniff und eine Korrelationskennung.

## Endpunkte

| Methode und Pfad | Inhalt / erforderliches Recht |
| --- | --- |
| GET /auth/login | OIDC-Codefluss beginnen |
| GET /auth/callback | State, Browserbindung, Code, Nonce und JWT prüfen |
| POST /auth/logout | aktuelle Sitzung widerrufen; CSRF erforderlich |
| GET /me | Nutzer, verfügbare Organisationen, aktive Organisation, Rollen, CSRF, Ablauf und KI-Verfügbarkeit |
| POST /session/organization | organization_id prüfen, Sitzung und CSRF rotieren |
| GET /organizations/current/members | eigene Mitgliedschaften; ORG_ADMIN |
| POST /organizations/current/members | vorhandene interne user_id und roles zuordnen; ORG_ADMIN |
| PATCH /organizations/current/members/{user_id} | roles, status, expected_revision; ORG_ADMIN |
| GET /demo-scenario | gekennzeichnete synthetische Eingaben; Leserecht |
| POST /scenarios | vollständiges Szenario erstellen; Analyst/Admin |
| GET /scenarios | paginierte Liste; Leserecht |
| GET /scenarios/{id} | aktueller Snapshot und Versionsreferenzen |
| POST /scenarios/{id}/versions | neue Version mit expected_current_version |
| GET /scenarios/{id}/versions/{version_no} | unveränderlicher historischer Snapshot |
| GET /decision-catalogs | aktuell nutzbare Regel-/Katalogversionen |
| POST /assessments | Bewertung berechnen und atomar speichern; Analyst/Admin, Idempotency-Key |
| GET /assessments | paginierte Ergebnisse, optional scenario_id |
| GET /assessments/compare?ids=a,b | ein bis fünf verschiedene sichtbare IDs |
| GET /assessments/{id} | gespeichertes Ergebnis |
| POST /assessments/{id}/explanations | externe Zustimmung, Providerfreigabe, Analyst/Admin, Idempotency-Key |
| GET /assessments/{id}/explanations | gespeicherte Zusatztexte und Aufrufzustände |
| GET /explanation-requests/{id} | berechtigt sichtbarer Aufruf; keine erneute Ausführung |
| GET /audit-events | paginierte mandanteneigene Auditereignisse; ORG_ADMIN |
| GET /health/live | Prozess erreichbar; keine Interna |
| GET /health/ready | DB, erwartete Migration und gültige OIDC-Metadaten erreichbar |

Die Health-Routen sind in der lokalen Demo ohne Login erreichbar. /me setzt noch keine aktive Organisation voraus. Es gibt keine öffentliche Nutzer-/E-Mail-Suche: Zuordnung verlangt eine bereits provisionierte interne UUID.

Die Szenarioliste liefert pro Eintrag den aktuellen Snapshot und im Feld versions nur dessen Referenz. GET /scenarios/{id} liefert die vollständige Versionshistorie. So bleibt die Listenabfrage unabhängig von der Zahl historischer Versionen begrenzt.

## Fachliche DTOs

ScenarioInput: name, company_profile, workloads, infrastructure_assets, requirements. Bis zehn Arbeitslasten, eindeutige Schlüssel, explizite Ressourcenmengen, RTO/RPO in Sekunden und dezimale Budgets. Technisch valide unbekannte Werte bleiben im Snapshot und ergeben fachliche Unsicherheit. Neue Versionen ergänzen expected_current_version.

AssessmentCreate: scenario_version_id sowie optionale candidate_catalog_version, cost_catalog_version, rule_set_version; weight_profile ECONOMIC/PERFORMANCE/CUSTOM, custom_weights, horizon_months (1–120), valuation_date. Ausgelassene Versionen werden auf den aktuellen Serverstand festgelegt und im Resultat gespeichert. Freie Ergebnisfelder sind verboten.

AssessmentView enthält id, scenario_version_id, options, result_hash, created_at und den vollständigen AssessmentResult: status, candidates, evidence, verification, recommended_candidate_key, weights, sensitivity und Versions-/Snapshotnachweise gemäß Schema. Kandidaten tragen Constraints, getrennte Architekturachsen, Kriterien, Kostenzeilen, Unsicherheiten und Rang. Die Zustände sind VERIFIED, INCOMPLETE, NO_FEASIBLE_OPTION und VERIFICATION_FAILED. Unvollständige fachliche Eingaben ergeben eine gespeicherte Ressource ohne bestätigten Sieger.

ExplanationCreate: ausschließlich approve_external_processing=true. Der Server erzeugt die minimierte Providerprojektion selbst. provider/model/prices können nicht über diesen Body überschrieben werden.

## Atomizität und Wiederholung

Ein UUID-Idempotency-Key wird für Bewertungen und Zusatztexte je Nutzer/Organisation eindeutig gespeichert. Identischer kanonischer Inhalt liefert dieselbe Ressource (200), abweichender Inhalt 409. Neue Ressourcen liefern 201. Eine noch laufende Erklärung liefert bei Wiederholung oder Einzelabruf 202. Schlüssel werden nicht automatisch gelöscht.

Vor einer Fachmutation prüft eine kurze Transaktion die aktuellen Rechte unter Organisationslock. Berechnung und externe I/O finden außerhalb der Transaktion statt. Ergebnis, untergeordnete Datensätze und Audit werden zusammen committed.

Erklärungen speichern vor Anbieter-I/O eine Tagesbudgetreservierung. Providerfehler ergeben eine gespeicherte FAILED-Erklärung; das fachliche Ergebnis bleibt verfügbar. Eine ältere offene Reservierung erscheint nach 30 Sekunden als INDETERMINATE mit OUTCOME_UNKNOWN. Die Reservierung bleibt erhalten, und Wiederholen desselben Schlüssels sendet keine neue Anbieteranfrage. Ein bewusst neuer Auftrag braucht einen neuen Schlüssel, Zustimmung und freie Quote.

## Implementierte M2-CSV-Erweiterung (11.09.2026)

Die bisherigen Endpunkte bleiben erhalten. Alle Pfade dieser Tabelle sind relativ zu /api/v1. Leserecht umfasst Viewer; Schreiben benötigt Analyst/Admin und CSRF. Organisation/Urheber werden ausschließlich aus der Sitzung ermittelt.

| Methode und Pfad | Vertrag |
| --- | --- |
| POST /datasets | name, filename (.csv ohne Pfad), content_base64, delimiter; 202 JobView |
| GET /datasets | bis 100 Datensätze der Organisation als items; feste lokale Gesamtgrenze statt Pagination |
| GET /datasets/{id} | Herkunft, bis 20 Versionen, bis 50 jüngste Aufträge |
| GET /datasets/{id}/jobs/{job_id} | konkreter Auftragszustand mit Fehler oder unveränderlicher Vorschau |
| POST /datasets/{id}/previews | source_version und 1–10 typisierte steps; 202 JobView |
| POST /datasets/{id}/versions | preview_id, result_hash, expected_current_version; 201 VersionView; Wiederholung derselben Vorschau liefert dieselbe Version |
| GET /datasets/{id}/versions/{no}/rows?offset=0 | 25 Zeilen ab Offset, Spalten und Gesamtzahl |
| GET /datasets/{id}/versions/{no}/export | sichere CSV, Content-Disposition, X-Content-SHA256, X-Source-SHA256 und X-Protected-Cells |
| GET /datasets/{id}/original | unveränderte Originalbytes, Binärdownload mit .csv.txt-Endung |

Auftragszustände: QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED. JobView enthält zusätzlich progress (0–100), progress_message und processed_rows. Fehlerhafte CSV wird als FAILED gespeichert; ihre Originalbytes bleiben prüfbar. Eine neue Vorschau verändert keine Datenversion. Idempotenz bezieht sich auf die Bestätigung einer konkreten Vorschau; ein erneut gesendeter Import erstellt einen neuen Auftrag/Datensatz.

Spaltenoperationen: trim, fill_missing, lowercase, uppercase mit column; nur fill_missing hat value. drop_duplicates und drop_empty_rows haben keine Spaltenargumente. Extra-Felder und ausführbare Ausdrücke sind verboten.

Der historische Base64-Kompatibilitätsweg behält 128 KiB; die Oberfläche verwendet den neuen 1-GiB-Upload. Format-/Argumentfehler liefern 422, Größenfehler 413, veraltete Vorschau oder lokale Kapazitätsgrenzen 409. Export und Originaldownload werden datenarm auditiert. Die gespeicherten Profile enthalten csv-profile-1 und csv-transform-1 als Verfahrensstände.

[ADR 0005](adr/0005-bounded-csv-data-workflow.md) begründet die Grenzen; [M2-Prüfbericht](testing/M2_CSV_REPORT.md) enthält ausgeführte Nachweise.


## Erweiterung auf 1 GiB (12.09.2026)

| Methode und Pfad | Vertrag |
| --- | --- |
| POST /data-uploads | name, filename, total_bytes (1–1.073.741.824), delimiter; 201 UploadView |
| GET /data-uploads | offene Uploads der aktiven Organisation; items, höchstens drei |
| GET /data-uploads/{id} | Status OPEN/SEALED/CANCELLED, Metadaten, erwartete/empfangene Bytes, Abschnittszahl und Abschnittslimit |
| PUT /data-uploads/{id}/chunks/{ordinal} | Binärbody bis 4 MiB, fortlaufend ab 0; identische Wiederholung idempotent, anderer Inhalt 409 |
| POST /data-uploads/{id}/complete | vollständige Größe und SHA-256 prüfen, atomar versiegeln; 202 JobView, gleicher Abschluss liefert gleichen Auftrag |
| POST /data-uploads/{id}/cancel | offene Abschnitte entfernen und Upload abbrechen; wiederholbar |
| POST /datasets/{id}/jobs/{job_id}/cancel | wartenden/laufenden Auftrag abbrechen; terminale Ergebnisse bleiben unveränderlich |
| GET /datasets/{id}/versions/{no}/export-info | Export-Prüfsumme und Anzahl geschützter Zellen ohne Dateiübertragung |

Alle Upload-Endpunkte erfordern Schreibrechte. PUT und POST erfordern CSRF; Fremdobjekte liefern 404. Uploadgröße über 1 GiB scheitert bei Metadatenvalidierung mit 422, zu großer Einzelrequest mit 413. Die Gesamtprüfung liest abschnittsweise außerhalb einer langen Schreibtransaktion; der Proxy erlaubt dafür 180 Sekunden. Downloads verwenden StreamingResponse mit Content-Length und SHA-256. JSONL-Seiten lesen indizierte Abschnitte; der Offset ist nicht auf 5.000 begrenzt.

Neue Profile verwenden csv-profile-stream-2 und csv-transform-stream-2. statistics_note erklärt Anzeigekürzung und nicht berechnete Ausreißer. Häufigkeiten, verschiedene Werte, Duplikate, Fehlwerte und Dezimalaggregate beziehen sich auf sämtliche Zeilen. [ADR 0006](adr/0006-gib-csv-streaming.md).


## Diagrammdaten (12.09.2026)

GET /datasets/{id}/versions/{no}/chart-sample?x=0&y=1 liefert ChartSample: version_no, content_hash, total_rows, columns (zwei ausgewählte Spalten), rows (row_number ab 1 und values), method (complete oder systematic-chunks-v1), truncated_cells. x/y sind nullbasierte Spaltenindizes 0–255; nicht vorhandene Spalten liefern 422. Höchstens 300 Zeilen, zwölf normalisierte Abschnitte, 512 Zeichen je Wert. Alle vorhandenen Session-/Mandantenregeln gelten; Viewer dürfen lesen, fremde Versionen liefern 404. Details in [ADR 0007](adr/0007-interaktive-datenvisualisierung.md).

Der Datensatzdetailabruf schützt den Zusammenhang von Kopfversion, Versionsliste und Auftragsstand mit einer geteilten Datensatzsperre während der kurzen Lesetransaktion.

## CSV-Leseoptionen und Wiederaufnahme (Migration 0004)

Neue Uploads akzeptieren delimiter (auto, Komma, Semikolon, Tabulator, |), encoding (auto, utf-8-sig, utf-16, cp1252) und has_header. Standard: auto/auto/true. JobView führt import_options, DataProfile optional import_info mit tatsächlich erkanntem Format. Alte Profile bleiben lesbar.

POST /datasets/{id}/retry-import mit ImportOptions (CSV-Optionen und optionale XLSX-Blattnummer; auch {}): 202 für neuen oder identischen aktiven Import; 409 bei anderen aktiven Optionen oder vorhandener Version. Writer, CSRF, Mandantenschutz und Quoten werden serverseitig geprüft. Originalbytes und bisherige Jobs bleiben erhalten.

## JSON-/JSONL-Tabellen

UploadInput akzeptiert zusätzlich .json und .jsonl. Der Server speichert das Format unveränderlich im Originalblob; es wird nicht aus Agenten- oder Zelltext übernommen. DataProfile.source_format ist csv, json oder jsonl, bei historischen Profilen standardmäßig csv. CSV-Leseoptionen beeinflussen JSON nicht. JSON benötigt UTF-8 und flache Objekte mit stabiler erster Spaltenmenge. Alle bisherigen Vorschau-, Bestätigungs-, Diagramm- und Exportendpunkte gelten auch dafür. Details: [ADR 0009](adr/0009-json-tabellenimport.md).

## XLSX und gemeinsamer Importvertrag

UploadInput und POST /datasets/{id}/retry-import verwenden ImportOptions: vorhandene CSV-Optionen plus worksheet (1–100, Standard 1). UploadView und JobView.import_options enthalten die Auswahl; alte gespeicherte Optionen ergänzen den Standard. Die Dateiendungen csv/json/jsonl/xlsx werden unabhängig von Großschreibung angenommen und serverseitig normalisiert.

DataProfile.source_format umfasst xlsx; source_worksheet ist eine Blattnummer oder null. Auch abgeleitete Versionen behalten die ursprüngliche Blattnummer. Fehler durch Blattwahl, Formelzellen oder ZIP/XML-Struktur erscheinen als nachvollziehbarer fehlgeschlagener Importauftrag. Das Original bleibt zur Wiederaufnahme erhalten. [ADR 0011](adr/0011-xlsx-tabellenadapter.md).

## Parquet

UploadInput akzeptiert .parquet (Groß-/Kleinschreibung gleichwertig); DataProfile.source_format enthält parquet und bleibt in Ableitungen erhalten. Es gibt keine weiteren Leseoptionen: das Dateischema bestimmt die Spaltennamen. CSV-/XLSX-Leseoptionen verändern Parquet nicht. Originalblob und Importauftrag speichern das Format unveränderlich. Alle bestehenden Upload-, Vorschau-, Bestätigungs-, Diagramm- und CSV-Exportverträge gelten. Fehler im Containerformat werden als datenarme deutsche Importfehler ausgewiesen. [ADR 0012](adr/0012-parquet-tabellenadapter.md).

## M2-Erweiterung vom 14.09.2026

Alle Pfade unter `/api/v1`, mit bestehender Sitzung, RLS und CSRF bei Änderungen. Schreibaktionen erfordern Organisationsadministration oder Analystenrolle. Anlegen von Analyse-, Quellen- und Planaufträgen sowie Wiederholungen erfordert einen UUID-Header `Idempotency-Key`. Gleicher Schlüssel/gleicher Auftrag liefert dieselbe ID; abweichender Auftrag ergibt 409.

| Vertrag | Zweck |
| --- | --- |
| GET `/data-sources` | Mandantenfreigegebene Quellenkennungen/Namen/Tabellen und Live-KI-Verfügbarkeit; keine Verbindungsgeheimnisse |
| POST `/data-sources/import` | `source_id`, `table`, `name`; persistenter SOURCE-Auftrag, 202 |
| GET/POST `/data-rule-sets` | Unveränderliche Regelsätze mit Name, Regeln und optionalem `replaces_id`; Anlegen 201 |
| POST `/datasets/{id}/analyses` | Version, höchstens acht numerische Spalten, optionale Zeitaggregation, Regelsatz oder Einzelregeln; 202 |
| GET `/data-tasks` | Metadatenliste, Filter `dataset_id`/`kind`, `limit` 1–100, `before` als mandantengeprüfte Cursor-ID; `next_cursor` |
| GET `/data-tasks/{id}` | Einzelauftrag einschließlich typisiertem Resultat und Eingabesnapshot |
| POST `/data-tasks/{id}/cancel` | Abbruch aktiver Aufgaben; abgeschlossene Aufgabe bleibt unverändert |
| POST `/data-tasks/{id}/retry` | Neuer SOURCE-/ANALYSIS-Auftrag mit Bezug auf fehlgeschlagenen/abgebrochenen Vorgänger; keine automatische KI-Wiederholung |
| GET `/data-tasks/{id}/report?format=html` | Integritätsgeprüfter Bericht mit Downloadheader; alternativ `json` |
| POST `/datasets/{id}/plans` | `version_no`, `mode: rules/openai`, `approve_external_processing`; begrenzte persistente Planung, 201 |
| POST `/data-tasks/{id}/preview` | Geprüften aktuellen Plan an vorhandene Vorschau übergeben; inhaltlich gleiche offene/fertige Vorschau desselben Erstellers wiederverwenden, 202 |

Die verbindlichen Schemafelder stehen in [domain.schema.json](contracts/domain.schema.json). Aufträge binden Ersteller/Organisation/Version und SHA-256. Status: QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED. Ergebnisarten sind AnalysisResult, SourceResult und PlanResult. Analytische Zahlen werden als Dezimalstrings übertragen. Berichte unterscheiden Datenbefund, Methodik und Unsicherheit. Die explizite Bestätigung über den vorhandenen Versionsendpunkt bleibt unverändert.
