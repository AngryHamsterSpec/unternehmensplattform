# Umgang mit Sicherheitsvorfällen

Status: **TEILWEISE IMPLEMENTIERT UND MIT SYNTHETISCHEN DATEN GEÜBT**. Stand: 11.09.2026. Lokaler DB-Ausfall/Wiederanlauf, Sessionwiderruf und Restore einschließlich Passwortrotation in einer getrennten Testinstanz sind geprüft. Es bestehen weiterhin keine besetzte Rufbereitschaft oder vereinbarte Reaktionszeit. Die weiteren organisatorischen Schritte bleiben Entwurf. [Ausführungsnachweise](../testing/PHASE_1_REPORT.md).

## Verantwortung und Aktivierung

Im Entwicklungsprojekt übernimmt der Projektverantwortliche die Koordination. Vor echtem Organisationsbetrieb sind folgende Funktionen mit Namen und einem vertraulichen Kontaktweg zu besetzen: Incident-Koordination, technischer Betrieb, Datenverantwortung, Kommunikationsverantwortung und Vertretung. Sicherheitsmeldungen mit Secrets oder echten Kundendaten gehören nicht in öffentliche Git-Issues. Ein privater Meldeweg ist vor Veröffentlichung einzurichten; solange er fehlt, darf die Dokumentation keinen funktionierenden Meldekanal behaupten.

Ein Vorfall ist beispielsweise bestätigter oder vermuteter Zugriff auf fremde Mandantendaten, Schlüssel-/Sessionverlust, manipulierte Bewertung, unautorisierte Werkzeugwirkung, offenes Lab oder unkontrollierter Daten-/Traceexport. Ein fehlgeschlagener Test ist zunächst ein Defekt; Hinweise auf bereits erfolgten Zugriff machen ihn zum Vorfallsverdacht.

| Schwere | Beispiele | Erste Entscheidung |
| --- | --- | --- |
| S1 – Kritisch | Mandantenübergriff, Zugangsschlüssel kompromittiert, unautorisierte externe Wirkung, kontrollierter Host/IdP | Betroffenen Zugriff bzw. Betrieb isolieren; zuständige Personen unmittelbar über den vereinbarten Weg einbeziehen |
| S2 – Hoch | Einzelmandant betroffen, anhaltende Ressourcen-/Kostenerschöpfung, Auditlücke bei Änderungen | Betroffene Funktion stoppen oder einschränken; Umfang und Datenintegrität prüfen |
| S3 – Begrenzt | Abgewiesener Angriff, isolierter Konfigurationsfehler ohne bekannte Wirkung | Beleg sichern, Ursache beheben, Regressionstest ergänzen |

Diese Kategorien sind technische Prioritäten. Gesetzliche Meldepflichten oder Fristen werden hier nicht behauptet; zuständige Verantwortliche bewerten sie anhand des konkreten Falls.

## Ablauf

1. **Erkennen und erfassen:** Incident-ID, Entdeckungszeit in UTC, Meldende, beobachtete Wirkung und betroffene Umgebung erfassen. Beobachtung, Vermutung und bestätigte Fakten getrennt halten. Keine Geheimnisse in Tickets kopieren.
2. **Eindämmen:** Aktive Sitzungen/Zugänge widerrufen, betroffene Endpunkte/Adapter deaktivieren, Egress begrenzen oder den Stack isolieren. Ein laufender Angriff hat Vorrang vor vollständiger Beweissicherung. Sonst vor Änderungen relevante minimierte Belege sichern. Datenbankvolumes nicht vorschnell löschen.
3. **Umfang feststellen:** Betroffene Tenants, Nutzer, Zeitfenster, Objekte, Builds und Provider-/Action-IDs anhand lokaler Logs und Audits bestimmen. Unbekannten Umfang offen lassen; fehlende Logs sind kein Beweis fehlender Wirkung.
4. **Ursache beseitigen:** Verwundbare Komponente reparieren/aktualisieren, Rechte reduzieren, betroffene Geheimnisse ersetzen und alte Werte widerrufen. Ein Git-Commit, der ein Secret entfernt, ersetzt keinen Widerruf.
5. **Wiederherstellen:** Aus vertrauenswürdigem Build mit überprüfter Konfiguration starten. Datenintegrität, Authentisierung und Mandantentrennung testen; gegebenenfalls Backup zuerst isoliert wiederherstellen. Erneut angewandte Löschanforderungen und Zugangssperren prüfen.
6. **Kommunizieren und abschließen:** Technisch verifizierte Fakten, betroffene Funktionen und nächste Schritte über autorisierte Kontaktwege bereitstellen. Der Projektverantwortliche entscheidet über Wiederaufnahme mit dokumentierter Restunsicherheit. Ursachenanalyse, Maßnahmen, Test-IDs und Verantwortliche festhalten.

## Konkrete Szenarien

| Ereignis | Eindämmung | Untersuchung / Freigabekriterium |
| --- | --- | --- |
| Fremde Mandantendaten sichtbar | Betroffene Lese-/Schreibfunktion sperren; bei breitem Scope Stack vom Zugang trennen | Runtime-Rolle, RLS-Policies, Tenantkontext/Pool-Reuse und Beziehungen prüfen; SEC-04/05/06 mit zwei realen DB-Tenants bestehen; Umfang historischer Zugriffe ermitteln |
| Session/IdP kompromittiert | Lokale Sitzungen widerrufen, betroffene Identitäten sperren; ggf. OIDC-Client/Signaturschlüssel nach Providerverfahren rotieren | Login-/Rollenänderungen und Issuerkonfiguration prüfen; alte Sessions/Callbacks tatsächlich unwirksam; SEC-01/02 bestehen |
| API-/DB-Schlüssel geleakt | Wert beim ausstellenden System widerrufen, Ersatz über Secretkanal verteilen; betroffenen Dienst begrenzen | Quelle in Log, Repo, CI oder Image finden; alte Werte nicht mehr wirksam; Scan und SEC-09/20/21 bestehen |
| Prompt Injection / Datenexport | Externe KI und betroffenen Wissens-/Toolpfad deaktivieren; Tenant-Providerfreigabe aussetzen | Übermittelten minimierten Payload und Provider-Request-IDs geschützt bestimmen; keine weitere Egresswirkung; SEC-10/21, später SEC-17 bestehen |
| Bewertung/Katalog manipuliert | Betroffene Version sperren und Ergebnisse als überprüfungsbedürftig markieren; nicht still überschreiben | Eingabe-/Regel-/Katalogversionen und Verifier neu prüfen; korrigierte Version mit Referenz auf Altversion; SEC-07/12 bestehen |
| Kosten-/Rate-Limit-Sturm | KI-Aufrufe und ggf. betroffene Nutzer begrenzen; ausstehende neue Aufträge stoppen | Reservierungen, Retryzahlen und reale Usage abgleichen; keine automatische Freigabe bei unklarem Providerstatus; SEC-11/22 bestehen |
| Später Lab erreichbar / Scan außerhalb Scope | Scanner stoppen, Labnetz isolieren, veröffentlichte Ports schließen | Tatsächliche Ziel-/Netzwerkbelege bestimmen; DNS/Redirect/Allowlist und Isolation testen; SEC-14/15 bestehen |
| Später unklare Cloudwirkung | Weitere Apply-Aufträge sperren; unsicheren Auftrag zur Statusklärung markieren | Providerstatus mit Action-/Idempotenz-ID feststellen; kein blindes Retry; SEC-15/16 bestehen |

Ein kontrolliertes Abschalten muss Fachdaten erhalten. `docker compose down -v`, rekursive Volumenlöschung oder destruktives Zurücksetzen sind keine Standardmaßnahme. Die vorhandenen lokalen Prüfskripte check_runtime.py und check_restore.py liegen unter scripts. Sie beschränken ihre Wirkung auf die Demo beziehungsweise ein neu erzeugtes Restore-Projekt; siehe README und Prüfbericht.

## Belege und Vertraulichkeit

Für jeden Vorfall werden Incident-ID, Zeitfenster, Build-/Imagekennung, betroffene Umgebung, pseudonyme Tenant-/Actor-IDs, Request-/Run-/Action-IDs, bestätigte Ereignisse, getroffene Maßnahmen und ihre Zeiten gespeichert. Belege werden minimal, zugriffsbeschränkt und mit Hash/Erfassungszeit dokumentiert. Rohdaten und Vollbackups nur sichern, wenn sie zur Klärung nötig sind und die Verantwortlichen den Zugriff festlegen.

Audit- und Logzugriffe bleiben tenant-/rollenbezogen. Incident-Berechtigungen werden zeitlich begrenzt und protokolliert. Provider-Support erhält nur ausdrücklich freigegebene Belege; das Dokument autorisiert keine automatischen Nachrichten oder Uploads. Sitzungs-/API-Geheimnisse werden auch bei Incident-Arbeit nicht in gewöhnliche Logs, Modellkontexte oder Chatverläufe kopiert.

## Geplante Übungen und Abschlusskriterien

Phase 1 soll mit synthetischen Daten nachweisen: Sitzung widerrufen und Wiederverwendung ablehnen; Test-Secret rotieren; KI-Providerzugriff vollständig abschalten; DB-Ausfall ohne inkonsistente Bewertung behandeln; Datenbank sichern und in separater Testumgebung wiederherstellen. Das Ausführungsprotokoll umfasst Ausgangslage, Dauer, Ergebnis und gefundene Lücken. Es darf kein RTO/RPO zugesagt werden, bevor die Dauer gemessen ist. Die späteren Lösch-/Backupregeln werden über SEC-19 ergänzt.

Abschluss eines Vorfalls erfordert festgestellte Eindämmung, überprüfte Ursache oder ausdrücklich dokumentierte verbleibende Unsicherheit, vertrauenswürdige Wiederherstellung, bestandene relevante Regressionstests und verantwortete Kommunikation. Ein bloßes Neustarten oder ein erfolgreicher Healthcheck genügt nicht.

Die Ursachenanalyse hält fest: Was geschah, welche Grenze versagte, wie der Fehler entdeckt wurde, welche Daten/Wirkungen betroffen waren, welche Maßnahme den Schaden begrenzte, welcher Test künftig schützt und wer die verbleibende Arbeit übernimmt. Schuldzuweisung ersetzt keine technische Ursache. Das [Bedrohungsmodell](THREAT_MODEL.md), die [Vertrauensgrenzen](TRUST_BOUNDARIES.md) und [Datenklassifikation](DATA_CLASSIFICATION.md) werden mit den neuen Erkenntnissen aktualisiert.
