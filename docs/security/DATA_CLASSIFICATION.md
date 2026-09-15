# Datenklassifikation und Datenlebenszyklus

Status: **ENTWURF – NICHT IMPLEMENTIERT**. Stand: 09.09.2026. Dieses Dokument definiert technische Projektregeln. Es ist keine Datenschutzfreigabe oder rechtliche Konformitätsbewertung.

## Klassen und zulässige Verarbeitung

| Klasse | Beispiele | Speicherung / Zugriff | Externe KI / Diagnostik |
| --- | --- | --- | --- |
| K0 – Öffentlich / synthetisch | Veröffentlichte Dokumentation, erfundene Demoorganisation, klar markierter Beispielkatalog | Repository und Demo zulässig; Herkunft und synthetischen Charakter erhalten | Nur bei aktivierter Providerkonfiguration; keine Traces als unbeabsichtigter Nebenkanal |
| K1 – Intern | Interne Projektstruktur, nicht sensible Organisationsmetadaten | Tenantgebunden mit RBAC; keine öffentlichen Antworten oder unverlangten Exporte | Nur freigegebene DTO-Felder nach Tenant-Policy; Logs nur IDs und knappe technische Metadaten |
| K2 – Vertraulich | Unternehmensanforderungen, reale Budgets, Infrastruktur, Kontaktdaten, Bewertungen, Ticket-/Wissensinhalte | Standardklasse für reale Fachinhalte; Tenant/Objektberechtigung, geschützte Backups | Standardmäßig gesperrt; nur ausdrücklich freigegebener minimierter Ausschnitt und konfigurierter zulässiger Provider |
| K3 – Streng vertraulich / Geheimnis | Passwörter, Sessioncookies, API-Schlüssel, Client-Secrets, private Schlüssel, Produktionszugänge | Dedizierte Secretübergabe; kein Quellcode, keine Fach-DTOs, keine UI-Rückgabe; Token in DB nur Hash soweit möglich | Nie Modellkontext, Prompt, Trace oder normales Log |

Personenbezug, Sicherheitsrelevanz und Mandant sind zusätzliche Merkmale, keine austauschbaren Klassen. Ein pseudonymisierter Datensatz kann weiter personenbezogen sein. Abgeleitete Daten erben zunächst die höchste Klasse ihrer Quellen; ein automatischer „anonymisiert“-Schalter darf sie nicht herabstufen.

Die Plattform enthält Phase 1 ausschließlich synthetische Demo-/Testdaten. Benutzer dürfen keine echten Kundenangaben in Beispieldateien, Screenshots, Testfehlern oder Git-Issues hinterlegen. Vor realem Einsatz müssen Datenverantwortung und erlaubte Verarbeitung festgelegt werden.

## Felder und Zuständigkeiten

| Datenbereich | Mindestmetadaten | Fachliche Zuständigkeit | Phase |
| --- | --- | --- | --- |
| Unternehmensszenario | Tenant, Ersteller, Klassifikation, Version, Änderungszeit | Organisationsadministrator / berechtigter Analyst | 1 |
| Bewertung und Kostenvergleich | Tenant, Eingabesnapshot, Regel-/Katalogversion, Ersteller, Verifierstatus, Annahmen, Zeitpunkt | Berechtigter Analyst; Katalogpflege administrativ | 1 |
| Identität/Mitgliedschaft | Issuer/Subject, lokale ID, Status, Tenant/Rolle der Mitgliedschaft | Plattform- bzw. Organisationsadministration innerhalb ihrer Grenzen | 1 |
| Sitzung | Tokenhash, User-ID, Ablauf-/Widerrufszeiten | Identitätsmodul | 1 |
| Audit-/Agentlauf | Tenant, Actor, Ereignistyp, Ziel-ID, Request-/Run-ID, Status, erlaubte Metadaten | Betrieb und berechtigte Auditoren; Fachzugriff tenantgebunden | 1 |
| Dokument/Datensatz und Ableitungen | Tenant, Owner, ACL, Klasse, Quellhash, Version, Lineage, Status | Organisation / Datenverantwortliche | Später |
| Secret | Typ, Verantwortliche, berechtigter Dienst, Rotation und Widerrufsverfahren; Wert nicht im Fachmodell | Betrieb | 1 |

Mandant und Actor stammen aus bestätigtem Serverkontext. Ein Nutzer kann durch Eingabe eines `organization_id`- oder `classification`-Werts keine Zugehörigkeit ändern oder Inhalte ohne Berechtigung herunterstufen.

## Datenflüsse für Phase 1

1. Der Browser übermittelt begrenzte strukturierte Anforderungen über den Reverse Proxy. Er übermittelt keine Zugangsdaten der Unternehmensinfrastruktur.
2. Nach Identitäts-/Aktionsprüfung validiert das Intake-Modul Pflichtfelder, Wertebereiche und Einheiten und speichert eine Version im eigenen Mandanten.
3. Die Decision Engine liest den Snapshot und eine veröffentlichte mandanteneigene Katalogversion. Sie persistiert nachvollziehbare Scores, Rechenbestandteile, Annahmen und Verifierresultate. Änderungen am Profil ändern abgeschlossene Bewertungen nicht rückwirkend.
4. Die optionale Erklärung bekommt eine gesonderte Feld-Allowlist: pseudonyme Szenario-ID, erlaubte aggregierte Anforderungswerte, Kandidaten, berechnete Scores, Kosten und ausdrücklich deklarierte Unsicherheiten. Namen, Ansprechpartner, konkrete IPs/Hostnamen, Freitext, Originaldokumente und Geheimnisse sind standardmäßig ausgeschlossen.
5. Die UI zeigt das Ergebnis innerhalb desselben Mandanten. Sie lädt keine durch KI generierten externen Bilder oder Ressourcen. Fach-/Identitätsantworten erhalten eine private bzw. keine Cachefreigabe; sensible Antworten werden mit `Cache-Control: no-store` geplant.

Vor einem externen KI-Aufruf müssen globale Aktivierung, Tenant-Policy, erlaubte Datenklasse/Felder und Budget zusammenpassen. Ein API-Key allein ist keine fachliche Freigabe. Providerseitige Speicherung und Vertrags-/Regionseigenschaften werden vor Live-Nutzung separat überprüft; deaktivierte SDK-Traces beweisen keine Nichtverarbeitung durch den Provider.

## Protokollierung und Herkunft

Geplante Logs enthalten Zeit, Level, Eventcode, Request-/Job-/Run-ID, pseudonyme Actor-/Tenant-ID, Status und begrenzte Dauer-/Usagewerte. Keine Authorization-/Cookie-Header, Session- oder CSRF-Tokens, API-Schlüssel, Datenbank-URLs, Rohprofile, Rohprompts, Dokumenttexte oder vollständigen Providerantworten. Querystrings und Fehlerobjekte werden vor Logging gefiltert; kontrollierte Test-Secrets müssen in allen Fehlerszenarien unsichtbar bleiben. Diese Begrenzung folgt den Grundsätzen aus [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html).

Audit enthält erlaubte fachliche Metadaten und Referenzen auf autorisierte Inhalte, nicht deren vollständige Kopien. Actor und Tenant werden serverseitig hinzugefügt. Fachänderung und zugehöriger Auditdatensatz committen gemeinsam. Runtime darf Audit weder ändern noch löschen. Ein späterer Aufbewahrungsprozess arbeitet unter gesonderter Betriebsberechtigung.

Gespeichert werden begründete Ergebniszusammenfassungen, überprüfbare Belege und Werkzeugereignisse. Verborgene Chain-of-Thought wird weder angefordert noch gespeichert. Ein Trace-Identifier ist kein Zugangsschlüssel und darf selbst keine Personen-/Firmennamen kodieren. Externe Traceexporte bleiben aus; eine spätere Änderung benötigt erneute Datenflussprüfung.

## Aufbewahrung, Löschung und Backups

Die folgenden Werte sind **Vorschläge für Entwicklung und Demo**, keine gesetzlich abgeleiteten Fristen. Für echte Organisationen sind Zweck, Betreiberentscheidung und Konflikte zwischen Löschung/Nachweispflicht vor Einsatz schriftlich festzulegen.

| Daten | Geplanter Demo-Standard | Umsetzung / Nachweis |
| --- | --- | --- |
| OIDC-Login-Zwischenzustand | Maximal 10 Minuten, nach Verwendung entfernen | Einmalige State-/Nonce-/PKCE-Nutzung; SEC-01 |
| Sitzungen | 30 Minuten inaktiv, maximal 8 Stunden; abgelaufene Datensätze innerhalb 24 Stunden bereinigen | Serverseitige Gültigkeit unabhängig vom Cookie; SEC-02 |
| Technische Logs | 14 Tage | Begrenzte Rotation; nur redigierte Metadaten; SEC-09 |
| Audit-/Usage-Metadaten | 90 Tage im Demobetrieb | Berechtigter Aufbewahrungslauf; keine unkontrollierte Tabellenlöschung durch Runtime |
| Fachprofile/Bewertungen | Bis berechtigter Löschung oder vollständigem Demo-Reset | Referenz-/Auditkonsistenz und dokumentierte Löschsemantik |
| Backups | Noch kein laufender Backupdienst; vor echten Daten verbindliche Policy erforderlich | Verschlüsselung, getrennte Zugriffsdaten, Wiederherstellungstest; SEC-19/22 |
| Spätere Uploads/Exporte/Embeddings | Vor Aktivierung festzulegen | Rohdaten, Ableitungen, Cache und Objektversionen gemeinsam berücksichtigen |

Ein Account-Widerruf sperrt sofort den Zugriff, löscht aber nicht automatisch alle fachlichen Arbeitsergebnisse. Löschung eines Profils muss den Umgang mit historischen Bewertungssnapshots ausdrücklich einschließen. Die Anzeige „gelöscht“ darf nicht suggerieren, dass Kopien bereits aus Backups verschwunden sind. Noch nicht implementierte Lösch-/Aufbewahrungsjobs dürfen keine produktive Datenhaltungszusage begründen.

Backups enthalten Mandantendaten und haben mindestens deren Schutzklasse. Vor Nutzung realer Daten: verschlüsselte Ablage, getrennte Betriebszugänge, dokumentierte Wiederherstellung, Behandlung von Löschmarkierungen und gemessene RTO/RPO. Die im Intake abgefragten Kunden-RTO/RPO sind fachliche Anforderungen und keine SLA des Plattformbetriebs.

## Datenexport und spätere Erweiterungen

Spätere CSV-/Tabellenexporte müssen Formelinterpretation berücksichtigen; JSON-/HTML-/PDF-Ausgaben brauchen kontextbezogene Kodierung. Dateipfade und Downloadobjekte werden serverseitig erzeugt und bei jedem Zugriff autorisiert. Öffentliche dauerhaft gültige Download-URLs und agentengenerierte Ziele sind kein Standard.

Wissensdokumente benötigen Owner, Tenant, ACL, Quellenversion und Herkunft. Retrieval-Index, Embeddings, Chunks und Caches tragen dieselben Isolationsmerkmale. Parser-/Scannerbelege bleiben von KI-Interpretationen unterscheidbar. Externe Quelldaten können falsch oder manipuliert sein; interne Speicherung macht sie nicht vertrauenswürdig.

