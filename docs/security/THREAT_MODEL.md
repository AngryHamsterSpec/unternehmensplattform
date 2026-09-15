# Bedrohungsmodell

Status: **ENTWURF – NICHT IMPLEMENTIERT**. Stand: 09.09.2026. Verantwortungsrolle: Security-Architektur; konkrete Besetzung offen. Alle Kontrollen, Tests und Betriebsverfahren auf dieser Seite sind Anforderungen, keine nachgewiesenen Eigenschaften.

## Geltungsbereich und Sicherheitsziele

Phase 1 umfasst Anmeldung, Mandantenmitgliedschaft, Unternehmensszenarien, deterministische Bewertung mit versioniertem Kostenkatalog, unabhängige Verifikation, persistierten Kosten-/Leistungsvergleich und eine optionale KI-Erklärung. Ein modularer FastAPI-Monolith, eine React-SPA, ein Reverse Proxy, PostgreSQL und ein lokaler OIDC-Provider bilden den geplanten Entwicklungsbetrieb. Es gibt in Phase 1 keine Cloud-Schreibwerkzeuge, Scanner, Upload-Verarbeitung, autonome Kommunikation oder Agent Factory.

Die weiteren Module sind hier vorausgedacht, damit spätere Schnittstellen die Grenzen erhalten. Ihre Kontrollen werden vor Implementierung erneut modelliert und getestet. Redis, S3, eine verteilte Warteschlange und externer Traceexport sind keine Voraussetzung für Phase 1.

Sicherheitsziele sind: fremde Mandantendaten bleiben unzugänglich; Rollen werden serverseitig durchgesetzt; Entscheidungen bleiben reproduzierbar und von KI-Ausgaben unabhängig; externe Nebenwirkungen brauchen eine konkrete Autorisierung; sensible Inhalte verlassen nur einen ausdrücklich konfigurierten Provider-Port; Fehler führen zu einem nachvollziehbaren sicheren Zustand.

## Schutzgüter und Angreifer

| ID | Schutzgut | Primäres Schutzziel |
| --- | --- | --- |
| A-01 | Identitäten, Mitgliedschaften, Sitzungen, Berechtigungen | Integrität und Vertraulichkeit |
| A-02 | Unternehmensprofile, Anforderungen, Geschäfts- und Infrastrukturinformationen | Mandantentrennung und Vertraulichkeit |
| A-03 | Eingabesnapshots, Regelversionen, Kostenkataloge, Bewertungen und Verifier-Ergebnisse | Reproduzierbarkeit und Integrität |
| A-04 | Auditdaten, Genehmigungen, Belege und Herkunftsnachweise | Zuordnung und Nachvollziehbarkeit |
| A-05 | API-Schlüssel, OIDC-Client-Geheimnisse, Datenbankzugänge, Backups | Vertraulichkeit und kontrollierte Wiederherstellung |
| A-06 | CPU, Speicher, Datenbankkapazität, externe KI-Budgets | Verfügbarkeit und Kostenbegrenzung |
| A-07 | Spätere Datensätze, Wissensdokumente, Scannerziele und Cloudressourcen | Zweckbindung und Scope-Einhaltung |

Angreiferklassen: unauthentifizierte Internet-/Browsernutzer; eingeloggte Nutzer mit zu wenigen Rechten; böswillige Nutzer eines anderen Mandanten; kompromittierte Browser oder Sitzungen; manipulierte Dokumente, Scanner- oder Modellausgaben; kompromittierte Abhängigkeiten/Container; missbräuchliche Betreiberzugriffe. Ein kompromittierter Docker-Host, Datenbank-Superuser oder API-Prozess kann wesentliche Grenzen überwinden. Das ist ein verbleibendes Risiko und kein durch RLS gelöstes Problem.

Grenz-IDs TB-01 bis TB-10 sind in [TRUST_BOUNDARIES.md](TRUST_BOUNDARIES.md) definiert. STRIDE: S = Identitätstäuschung, T = Manipulation, R = Abstreitbarkeit, I = Informationsabfluss, D = Dienstverweigerung, E = Rechteausweitung. Prioritäten sind qualitative Architekturprioritäten vor Gegenmaßnahmen: kritisch = mandantenübergreifender Zugriff, Geheimnisabfluss oder unautorisierte externe Wirkung; hoch = wesentlicher Missbrauch eines Mandanten oder Dienstausfall; mittel = begrenzte Integritäts-/Informationsrisiken. Sie sind weder CVSS-Werte noch ein gemessener Restrisikonachweis.

## Bedrohungsregister

| ID / STRIDE | Angriff, Akteur und betroffene Güter | Grenze / Priorität | Geplante Gegenmaßnahmen | Geplante Tests / Zielphase |
| --- | --- | --- | --- | --- |
| TM-01 / S,E | Angreifer fälscht OIDC-Callback, spielt Code wieder ein oder verbindet fremde E-Mail-Adresse mit lokalem Konto; A-01 | TB-02 / kritisch | Gepflegte OIDC-Bibliothek; Code Flow mit PKCE, State, Nonce, exaktem Issuer/Audience/Redirect; Identität über `(issuer, subject)`; keine Rollenzuteilung aus unbestätigten Claims | SEC-01 / 1 |
| TM-02 / S,I | Sitzungsdiebstahl, Fixation oder Weiternutzung nach Logout/Rollenentzug; A-01, A-02 | TB-01,02 / kritisch | Zufällige opake Session-ID, serverseitiger Hash, Rotation bei Login, HttpOnly/Secure, Ablauf und Widerruf; Berechtigungen bei jeder Aktion prüfen | SEC-02 / 1 |
| TM-03 / T,E | Fremde Website führt mit Session-Cookie Zustandsänderung aus; A-02, A-03 | TB-01 / hoch | CSRF-Token für Mutationen einschließlich Logout; Origin-Prüfung; sichere Methoden ändern keinen Zustand; enger CORS-Rahmen, SameSite ergänzend | SEC-03 / 1 |
| TM-04 / E,I | Viewer oder fremder Mandant ruft Schreib-/Detailendpunkt mit erratener ID auf; A-01–04 | TB-03,04 / kritisch | Serverseitige Aktionserlaubnis und Mitgliedschaft, Deny-by-default, objektspezifische Prüfung, identische Nichtgefunden-Antwort bei fremden Objekten | SEC-04,05 / 1 |
| TM-05 / I,T | Vergessener Filter, Pool-Reuse oder fehlerhafte RLS-Policy mischt Mandanten; A-02–04 | TB-04 / kritisch | RLS auf mandanteneigenen Tabellen, Runtime ohne Eigentum/BYPASSRLS, `USING` und `WITH CHECK`, transaktionslokaler Kontext; keine Anfrage ohne TenantContext | SEC-05 / 1 |
| TM-06 / T,I | Verknüpfung einer Bewertung mit Profil/Kostenposition eines fremden Mandanten; A-02, A-03 | TB-04 / kritisch | Zusammengesetzte Fremdschlüssel `(organization_id, parent_id)` und eindeutige Elternschlüssel; P1-Katalogkopien bleiben ebenfalls mandantengebunden | SEC-06 / 1 |
| TM-07 / T | Nutzer liefert negative Kosten, NaN, extreme Mengen oder manipulierte Gewichtung/Katalogversion; A-03 | TB-03,04 / hoch | Strikte DTOs, fachliche Grenzen und Decimal, keine vom Client übernommenen Resultate; unveränderlicher Eingabe-/Regel-/Katalogsnapshot, unabhängige Neuberechnung im Verifier | SEC-07 / 1 |
| TM-08 / I,E | Profilname oder KI-Markdown enthält Skript, Tracking-Bild oder aktiven Link; Fehler verrät Interna; A-01, A-02 | TB-01,06 / hoch | Kontextbezogene Ausgabe als Text, kein unbereinigtes HTML/Markdown, keine automatischen Fremdbilder, enge CSP und sichere Fehler; keine Tokens in URLs | SEC-08 / 1 |
| TM-09 / R,T,I | Nutzer bestreitet Änderung; Angreifer fälscht Actor/Tenant im Log oder schleust Zeilen/Secrets ein; A-04, A-05 | TB-03,04 / hoch | Auditkontext serverseitig; erlaubte strukturierte Felder; Audit und Fachänderung in einer Transaktion; Append-Rechte; kein Rohprompt-/Secret-Logging | SEC-09 / 1 |
| TM-10 / E,I,T | Direkte/indirekte Prompt Injection verlangt fremde Daten, neue Rollen oder geänderte Bewertung; Modell propagiert Anweisung an Agenten; A-02–05 | TB-05,06 / kritisch | Nicht vertrauenswürdige Inhalte bleiben Daten; minimaler strukturierter Kontext; Phase-1-Erklärer ohne Tools; keine Modellentscheidung als Berechtigung; deterministischer Verifier; Agenten kommunizieren über enge DTOs | SEC-10 / 1; SEC-17 / später |
| TM-11 / D | Prompt-/Toolschleifen, Retry-Sturm, übergroße Antworten oder Provider-Ausfall verbrauchen Budget; A-06 | TB-03,06 / hoch | Größen-, Laufzeit-, Parallelitäts- und Tokenlimits; begrenzte Retries nur für idempotente Aufrufe; Budgetreservierung; KI-Erklärung separat fehlbar | SEC-11 / 1 |
| TM-12 / T,D | Doppelter Request, Prozessabbruch oder gleichzeitige Änderung erzeugt widersprüchliche Vergleichsergebnisse; A-03, A-04 | TB-03,04 / hoch | Idempotenzschlüssel an Mandant/Actor/Payloadhash binden, DB-Transaktion, Versionierung, Integritätsbedingungen; KI-Ausfall rollt deterministische Bewertung nicht zurück | SEC-12 / 1 |
| TM-13 / T,E,D | Späterer Upload enthält Zip-Bombe, schädliches Makro, Parser-Exploit oder Pfadtraversal; A-05–07 | TB-07 / kritisch | Größen-/Entpack-/Typgrenzen, Quarantäne, generierte Pfade, kein Makro-/Formelausführen, Parser mit Ressourcenlimit; Original unveränderlich; Malware-Prüfhook ersetzt keine Isolation | SEC-13 / vor Data Intelligence |
| TM-14 / E,I | Scanner oder URL-Import wird für SSRF, DNS-Rebinding, Metadatenzugriff oder beliebige Internetziele genutzt; A-05, A-07 | TB-07,08 / kritisch | Explizites Scope-Manifest, Ziel-/Protokoll-/Port-Allowlist, IP-/DNS-/Redirect-Prüfung bei jeder Verbindung; kontrollierter Adapter; Lab ohne Internetroute und ohne Docker-Socket | SEC-14 / vor Security Lab |
| TM-15 / T,E,R | Genehmigung wird wiederverwendet, auf anderen Payload angewandt oder nach Rollen-/Zieländerung ausgeführt; A-04, A-07 | TB-05,08 / kritisch | Genehmigung an Ausführungsidentität, Antragsteller, Genehmiger, Tenant, Payloadhash, Scopeversion und Ablauf binden; Neubewertung und atomare Einmalverwendung vor Wirkung | SEC-15 / vor erster genehmigungspflichtiger Wirkung |
| TM-16 / E,T,D | Späterer Worker übernimmt manipulierten Tenantkontext, doppelte Lease oder abgelaufene Rechte; A-02–07 | TB-09 / kritisch | Jobdaten serverseitig erzeugen; Mitgliedschaft/Policy zur Ausführung erneut prüfen; begrenzte Leases, Claims und idempotente Adapter; keine pauschale RLS-Umgehung des Workers | SEC-16 / vor Hintergrundjobs |
| TM-17 / I,T | RAG-Dokument vergiftet Wissen, Citation oder ACL; Retrieval/Cache zeigt fremde Mandantendaten; A-02, A-07 | TB-05,07,09 / kritisch | Tenant- und ACL-Filter vor Retrieval, Herkunft und Version, Berechtigungsprüfung nach Retrieval, mandanten-/rechtebezogene Cachekeys, keine Anweisungsautorität von Quellen | SEC-17 / vor Support/RAG |
| TM-18 / E,T | Agent Factory aktiviert Werkzeugrechte oder Promptänderungen ohne Review; A-01, A-05, A-07 | TB-05,10 / kritisch | Unveränderliche Versionen, schema-/policygeprüfte Tool-Allowlist, Evaluation und menschliche Freigabe; keine Selbständerung von Systemprompt/Policy | SEC-18 / vor Agent Factory |
| TM-19 / I,D | Gelöschte Daten bleiben unbegrenzt in Exporten, Traces oder wieder eingespielten Backups; A-02, A-04, A-05 | TB-04,06,07 / hoch | Klassifikation, dokumentierte Lösch-/Aufbewahrungsjobs, minimierte Exporte; Wiederherstellung isoliert und Löschanforderungen erneut anwenden | SEC-19 / vor echten Organisationsdaten |
| TM-20 / E,I,T | Manipulierte Abhängigkeit, Container oder CI-Schritt extrahiert Secrets; A-01–07 | TB-10 / kritisch | Lockfiles, geprüfte Updates, Secret-/Dependency-/Containerscans, unprivilegierte Container, minimale Mounts, keine Produktionssecrets in PR-CI | SEC-20 / 1 |
| TM-21 / I | SDK-Defaults/Diagnostik exportieren sensible Traces oder der Provider erhält ungefiltertes Profil; A-02, A-05 | TB-06,10 / kritisch | Externe Traceexporte aus; expliziter Provider-Port, Egress-DTO mit Feld-Allowlist, Tenant-Policy und Betriebsfreigabe; Secrets nie Modellkontext; lokale Auditmetadaten | SEC-21 / 1 |
| TM-22 / D,I | Unbegrenzte APIs, freigegebene DB-/IdP-Adminports oder offenliegende Diagnosen führen zu Ausfall/Übernahme; A-01–06 | TB-01,02,04,10 / hoch | Request-/Query-/Listenlimits; getestete Rate-Limits; nur Proxy am Loopback veröffentlichen; Healthchecks ohne Fach-/Geheimnisdaten; Secretrotation und Wiederherstellung üben | SEC-22 / 1 |

## Nachweisplan

Jede Test-ID bezeichnet eine geplante Testsuite, keine bereits vorhandene Datei. Die Implementierung muss in ihrer Testdokumentation konkrete Testpfade und das letzte echte Ausführungsergebnis hinterlegen. Phase 1 benötigt SEC-01 bis SEC-12 und SEC-20 bis SEC-22. Die übrigen Suites sind Eintrittsbedingungen für ihre jeweilige Funktion; ihr Fehlen darf nicht als bestandene Prüfung gelten.

| Test-ID | Erwarteter Nachweis / Negativfall |
| --- | --- |
| SEC-01 | Gefälschter Issuer/Audience, fehlender/falscher State oder Nonce, falscher PKCE-Verifier und Callback-Replay werden abgewiesen; E-Mail-Gleichheit verknüpft keine Identitäten. |
| SEC-02 | Session vor Login wird rotiert; Logout, Idle-/Absolutablauf und Benutzerentzug sperren alte Cookies; DB speichert nur Session-Hash, Browser keine OIDC-Tokens. |
| SEC-03 | Jeder mutierende Endpunkt lehnt fehlenden/fremden CSRF-Token und unerlaubte Origin ab; authentisierte fachliche GETs verändern keine Fachdaten; notwendige Session-Aktivitätsbuchung und der explizite OIDC-Protokollfluss sind eng begrenzte Ausnahmen; fremde Origin erhält keine Credential-CORS-Freigabe. |
| SEC-04 | Aktionsmatrix für Rollen über API testen: Viewer liest, Analyst schreibt im berechtigten Mandanten; Rollen-/Tenantwerte im Body eskalieren nichts; Admin ist kein pauschaler Datenzugriff. |
| SEC-05 | Zwei echte PostgreSQL-Mandanten mit `platform_app`: SELECT/INSERT/UPDATE/DELETE, Listen/Counts, fehlender Kontext, Pool-Reuse, Commit/Rollback, Fehler und parallele Requests; keine fremden Zeilen. `platform_auth` hat keine Fachtabellenrechte; beide Rollen ohne DDL/BYPASSRLS/Eigentum. |
| SEC-06 | Jede tenantgebundene Elternbeziehung lehnt mandantenübergreifende Referenzen in der Datenbank ab; Constraintfehler verraten keine fremden Objektwerte. |
| SEC-07 | NaN/Infinity, negative/überhöhte Werte und fremde Ergebnisfelder ablehnen; identischer Snapshot erzeugt identischen Score; Verifier entdeckt manipulierte Summe/Version. |
| SEC-08 | Persistierte XSS-Payloads in Profil, Fehlern und KI-Text bleiben inert; kein fremder Bildabruf; kein Roh-HTML; Header und Fehlerantworten prüfen. |
| SEC-09 | Fachmutation ohne Auditcommit rollt zurück; Actor/Tenant kommen vom Server; Runtime kann Audit weder ändern noch löschen; Logs enthalten keine Test-Secrets, Tokens oder Rohprofile. |
| SEC-10 | Angriffsstrings im Freitext/Provideroutput ändern weder Mandant, Berechtigung, Katalog, Score noch Toolmenge; strukturwidrige/ungestützte Erklärung wird verworfen oder als nicht verfügbar gezeigt. |
| SEC-11 | Provider-Timeout, 429, 5xx, ungültiges JSON, überlange Ausgabe und Budgetüberschreitung: begrenzte Aufrufe, korrekt abgerechnete bzw. bei unklarem Ausgang weiterhin gehaltene Reservierung, unverändertes Basisergebnis. |
| SEC-12 | Replay mit gleichem Schlüssel/Hash liefert dieselbe Bewertung; anderer Payload mit gleichem Schlüssel kollidiert; Prozessabbruch und Parallelität hinterlassen keine halben Fachaggregate. Erklärung-Replay und Doppelklick starten keinen zweiten Provideraufruf; ein unklarer Ausgang bleibt INDETERMINATE. |
| SEC-13 | Größen-/Entpackgrenzen, falscher MIME-Typ, Traversal, Tabellenformeln, Makros und Parser-Timeout greifen; Originalversion unverändert und Quarantäne nicht öffentlich. |
| SEC-14 | Scopefremde Adresse, Redirect, IPv6-/IPv4-Sonderform, DNS-Wechsel, Link-local/Metadatenziel und unzulässiger Port abgewiesen; Testpakete können Labnetz nicht verlassen. |
| SEC-15 | Payload-/Scope-/Actorwechsel, abgelaufene/widerrufene Genehmigung, Rollenentzug und doppelte/parallele Ausführung erzeugen keine Wirkung; Genehmigung beweist keine fachliche Berechtigung. |
| SEC-16 | Leaseverlust, Workerabbruch, doppeltes Claim, Rollenentzug nach Enqueue und Cancel sicher behandeln; Wiederholung erzeugt keine zweite externe Wirkung. |
| SEC-17 | Fremde Dokumente auch über Vektorsuche, Citation-Auflösung, Cache und Folgeanfrage unsichtbar; injizierte Dokumentanweisung wird nicht Werkzeugrecht. |
| SEC-18 | Entwurf/abgelehnte Version/fehlende Evaluation nicht aktivierbar; Tools außerhalb Allowlist abgewiesen; alte Freigabe autorisiert keine neue Version. |
| SEC-19 | Löschlauf entfernt alle vorgesehenen Ableitungen; isolierter Restore setzt Löschsperren erneut um; Aufbewahrung und Legal-Hold sind ausdrücklich konfigurierte Betreiberentscheidungen. |
| SEC-20 | Commit-/Image-Scan erkennt Test-Secret und bekannte verwundbare Fixture; Container läuft ohne root, privilegierten Modus/Hostsocket; PR-CI hat keine Produktionssecrets. |
| SEC-21 | Netzwerk-/Adaptertest mit KI aus: null externe KI-/Tracecalls; KI an: nur freigegebene Felder an freigegebenen Provider; auch Fehler/Tracing/Retry exportieren keine Test-Secrets. |
| SEC-22 | Rate-/Body-/Querylimits liefern begrenzte Fehler; DB/IdP-Admin ist nicht öffentlich erreichbar; Wiederherstellung und Session-/Secretwiderruf werden mit Testdaten protokolliert. |

## Restrisiken und Freigaben

- **RLS ist zusätzliche Absicherung, kein Schutz vor einem kompromittierten Anwendungsprozess.** Die Anwendung setzt ihren Tenantkontext selbst. Ein Angreifer mit ihrer beliebigen SQL-Ausführung kann diesen Kontext ändern. SQL-Injection-Vermeidung, geringste Privilegien und Prozessschutz bleiben erforderlich.
- Append-orientierte Auditdaten sind gegen normale Anwendungsrollen geschützt. Datenbank-/Hostadministratoren können sie verändern; externe manipulationserschwerende Sicherung wäre eine spätere, begründete Erweiterung.
- Prompt-Injection-Erkennung ist keine verlässliche Autorisierungsgrenze. Selbst erfolgreiche Modellmanipulation darf in Phase 1 nur eine verworfene oder unzuverlässige Erklärung bewirken, niemals Änderung der Fachentscheidung oder Zugriffserweiterung.
- Versionsgeprüfte Kostenkataloge liefern Schätzungen unter dokumentierten Annahmen. Sie sind keine Lieferantenangebote und begründen keine Garantie für Kosten oder Verfügbarkeit.
- Ein lokaler OIDC-Dienst erhöht Reproduzierbarkeit, bringt aber eigene Updates, Daten, Backups und Administratorzugänge mit. Sein Ausfall verhindert Neuanmeldungen; bestehende Sitzungen bleiben nur innerhalb ihrer lokalen Gültigkeit nutzbar.
- Vor Nutzung echter Organisationsdaten sind Betreiberverantwortung, Speicherort, Aufbewahrung, externer Provider, Zugriff auf Backups und Incident-Kontakte konkret festzulegen. Diese Dokumente behaupten keine rechtliche Konformität, Zertifizierung oder Produktionsreife.

## Technische Quellen

Geprüft am 09.09.2026. Die konkreten Limits und Rollen dieses Modells sind Projektentscheidungen.

- PostgreSQL dokumentiert RLS-Bypass durch Superuser/BYPASSRLS und gewöhnlich Tabellenbesitzer sowie Besonderheiten von Integritätsprüfungen: [Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html). Daraus folgen getrennte Runtime-/Migrationsrollen, `FORCE ROW LEVEL SECURITY` und Tests direkter Datenbankzugriffe.
- Identitätsprüfung und Tokenvalidierung: [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html). OAuth-Sicherheitsgrundlage einschließlich PKCE und Redirect-Schutz: [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html).
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) und [CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) stützen die Kombination aus sicheren Sitzungen und einem gesonderten CSRF-Schutz.
- [OWASP LLM Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) beschreibt unter anderem indirekte Injektionen, Werkzeugmissbrauch und mehrschichtige Begrenzung. Der werkzeuglose Erklärer ist die daraus abgeleitete projektspezifische Anfangsentscheidung.
- [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html) behandelt Allowlisting, Redirect- und DNS-Risiken; die spätere Labfreigabe braucht zusätzlich einen realen Netzwerktest.

## M2: geprüfte CSV-Grenzen

| Risiko | Durchsetzung im ersten CSV-Ablauf |
| --- | --- |
| Dateipfad-/Fremdobjektzugriff | Dateiname bleibt Metadatum; UUID-Verweise, RLS und zusammengesetzte Mandanten-FKs |
| Ressourcenverbrauch durch Eingaben | 128 KiB, begrenzte Zeilen/Spalten/Zellen/Schritte und Quoten; Worker-CPU/RAM-/Transaktionsgrenzen |
| Ausführung von Text oder Tabellenformeln | keine Ausdrücke/SQL/Python/Shell; React-Textdarstellung; CSV-Quoting und Apostrophschutz auch für Header |
| Änderung nach Vorschau | gespeicherter Hash, Vorschau-ID und erwartete Version; serialisierte Bestätigung und unveränderliche Originale |
| Rechteentzug während der Wartezeit | frische DB-Mitgliedschafts-/Rollenprüfung vor Verarbeitung und Bestätigung |
| Worker-Abbruch | atomarer Rollback und erneute Verarbeitung; keine halben freigegebenen Ergebnisse |
| Backup ohne Dateibytes | PostgreSQL-Blobadapter im selben Dump; Restore vergleicht Bytes, Jobs und Versionen |

Die Pipeline überträgt keine Daten an externe Anbieter. Originaldownloads werden als .csv.txt angeboten; der Standardexport schützt Formelpräfixe. Vollständige Lösch-/Aufbewahrungs- und Dead-Letter-Verwaltung bleiben außerhalb dieses Demo-Ausbaus.


## Erweiterte Grenzen für 1-GiB-CSV

Abschnittsrequests sind einzeln auf 4 MiB begrenzt; Upload-Metadaten erlauben bis 1 GiB. Dateiabschnitte sind mandantengebunden, gehasht, geordnet und nach Versiegelung unveränderlich. Drei offene Uploads, eine 20-GiB-Dateiquote, begrenzte Zellen/Datensätze und CPU/RAM-Grenzen begrenzen Ressourcenverbrauch. SQLite-Arbeitsdateien und Sortierungen liegen auf einem separaten Volume.

Lange Berechnung hält keine Organisationssperre. Regelmäßige Leases prüfen Schreibrechte; Publikation prüft Token, Ablauf, Status und Rechte erneut. CANCELLED verhindert die Veröffentlichung eines alten Arbeiters. Seitenzugriffe und Downloads materialisieren keine ganze große Tabelle. Rohdaten verlassen den lokalen Stack nicht. Harte Prozessabbrüche können temporäre Reste hinterlassen; deren administrative Bereinigung und langfristige Aufbewahrung bleiben weitere Betriebsarbeit.

## JSON-Tabellenadapter (M2)

Unvertrauenswürdige JSON-/JSONL-Dateien können doppelte Schlüssel, tiefe Verschachtelung oder sehr große Objekte enthalten. Der Adapter begrenzt einzelne Datensätze, verwirft doppelte Schlüssel und Nichtstandardzahlen, akzeptiert nur flache Zellen und verändert keine Originalbytes. Workerressourcen, Mandantenprüfung, CSRF und explizite Versionsbestätigung gelten unverändert. Zelltexte erteilen keine Agenten-/Toolrechte.

## XLSX-Adapter (12.09.2026)

Zusätzliche Angriffsfläche: komprimierte Archive, sehr große zentrale Verzeichnisse, XML-Entitäten, große Shared-String-/Styletabellen, Zelladresslücken und Formelcachewerte. Vor ZipFile-Konstruktion begrenzt der Adapter das zentrale Verzeichnis. Er prüft Pfade, Duplikate, Verschlüsselung, entpackte Größen und Kompressionsverhältnis. SAX liest in 64-KiB-Abschnitten mit Tiefen-/Token-/Zell-/Zeilengrenzen; DTD und Entitäten sind unzulässig. Metadaten erhalten eigene Speichergrenzen. DefusedXML bleibt zusätzlich für openpyxl aktiv.

Keine Makros, externen Arbeitsmappen, eingebetteten Objekte oder Formelwerte. Vorhandene Ressourcenlimits, Lease-/Abbruchprüfung, RLS, CSRF, Originalhash und explizite Bestätigung gelten unverändert. Grenzen des Readers stehen in ADR 0011; sehr große textreiche Excel-Arbeitsmappen müssen als CSV exportiert werden. Keine Aussage, dass eine ZIP-Größenprüfung allein beliebige Arbeitsmappen sicher macht.

## Parquet (13.09.2026)

Komprimierte Zellseiten und Metadaten können Ressourcen erschöpfen oder auf externe Dateien verweisen. Der Adapter prüft den höchstens 8 MiB großen Thrift-Footer vor dem nativen Reader; Struktur-, Seitenpositions-, Größen-, Zeilen- und Schemaangaben müssen konsistent sein. Verschlüsselung und externe Column-Chunks werden abgewiesen. Der Reader erhält ausschließlich den intern materialisierten lokalen Originalpfad; Glob, Hive-Partitionserkennung, Cloud-Credentialprovider und Statistik-Pruning sind deaktiviert.

Polars wird exakt gebunden, erst beim Parquet-Auftrag geladen und auf einen Thread begrenzt. Deklarierte Größen sind keine Garantie für nativen Speicherverbrauch; Containerlimits und bestehende Lease-/Wiederanlaufregeln bleiben erforderlich. NaN/Infinity, binäre und verschachtelte Werte werden nicht still in unvollständige Tabellen umgewandelt. Abbruchpunkte liegen zwischen synchronen Gruppen und Umwandlungsabschnitten. Keine neuen Agentenrechte oder ungeprüften Toolausdrücke.

## SQLite-Snapshots (13.09.2026)

Zusätzliche Risiken sind manipulierte Schemata, SQL-Bezeichner, Views/virtuelle Tabellen, berechnete Ausdrücke, große Datensätze und unvollständige WAL-Hauptdateien. Quellen werden unveränderlich und nur lesend geöffnet, mit defensiver Konfiguration und deaktiviertem trusted_schema. Die eigentliche Abfrage darf über den Authorizer nur die zuvor gewählte gewöhnliche Tabelle lesen; keine Erweiterungen oder frei formulierten SQL-Befehle. Namen werden mit dem Schema abgeglichen und als Bezeichner zitiert. Berechnete/versteckte Spalten und virtuelle Tabellen sind ausgeschlossen.

Längen-/Spalten-/VM-/Cachegrenzen ergänzen den bestehenden begrenzten Worker. Fortschrittscallbacks erhalten Abbruch und Lease, Verbindungen werden auch bei Fehlern geschlossen. WAL-/verschlüsselte/beschädigte Dateien werden zurückgewiesen; die Nutzer müssen dennoch konsistente Sicherungen bereitstellen. Die Quelle ist kein Netzwerkadapter. RLS, Quoten, Audit, Originalhash und ausdrückliche Versionsbestätigung gelten unverändert. [ADR 0013](../adr/0013-sqlite-datenbanksnapshots.md).

## M2-Erweiterung vom 14.09.2026

| Grenze/Bedrohung | Durchsetzung | Nachweis |
| --- | --- | --- |
| Freie DSNs/SQL und interne Netzabfragen | Betreiberregistrierung mit Organisations-/Tabellenliste; Parameter/Identifier-Quoting; Plattform-/Identitätsdatenbanken gesperrt; eigener Quellenworker | Registry-Negativfälle, echte PostgreSQL-Quelle |
| Überprivilegierte Quelle / verlorene Quellen-RLS | Keine Superuser-/BYPASSRLS-/CREATEROLE-Verbindung; Read-only/Repeatable-read; Quellen-RLS gilt auch bei COPY | Synthetische gesperrte Zeile fehlt im Originalsnapshot |
| Speicher-/Zeiterschöpfung, blockierte Quelle | Zeilenprüfung vor COPY, 1 GiB, 256 MiB/1 CPU, Platten-/Zeitgrenzen, sichere Cancellation, Lease und maximal drei Versuche | Grenz-/Monitor-/Wiederanlauftests; finale Runtimeprüfung gesondert |
| Rechteentzug / verlorene Lease / konkurrierender Abschluss | Erneute Rollen-/Lease-/Konfigurationsprüfung vor atomarer Veröffentlichung; unveränderliche Abschlusszustände | Reale PostgreSQL-Integration |
| Prompt Injection / Modell als Berechtigungsquelle | Keine Rohwerte/Namen im Prompt, erlaubte IDs, striktes Schema und unabhängiger Verifier; keine Tools | Minimierung und adversariale Kandidaten mit Test-Double |
| Kosten durch Wiederholung / unklarer Anbieterzustand | Explizite Zustimmung, gemeinsames konservativ reserviertes Tagesbudget, Idempotenz, zehn Sekunden, keine automatischen KI-Retries | Budget-/Zustimmungs-/Timeoutfälle mit Test-Double |
| Falsche Übernahme / Überschreiben von Originalen | Plan an Versionshash, Vorschau, anschließende ausdrückliche Bestätigung; unveränderliche Datenversionen | Legacy-/Stream-Planablauf mit Originalvergleich |
| Mandantenübergriff / Bericht-XSS / große Listen | FORCE RLS, mandantengeprüfte Cursor/IDs, escaped HTML mit CSP, Metadatenlisten statt sämtlicher Berichte | RLS-/Export-/Escapingfälle; finale Browserabnahme offen |

Die Betreiberregistrierung und externe Quelladministration bleiben Vertrauensgrenzen. Egress sollte produktiv auf freigegebene Ziele beschränkt werden; Registry und TLS-Material gehören in geschützte Mounts. Plattformbackups enthalten erfasste Snapshots, nicht die externen Datenbanken. Live-KI, Produktivtransport und konkrete externe Quellumgebungen werden ohne eigenen Nachweis nicht als geprüft behauptet. [Architektur und Grenzen](../adr/0014-datenanalyse-quellen-und-gepruefte-plaene.md).
