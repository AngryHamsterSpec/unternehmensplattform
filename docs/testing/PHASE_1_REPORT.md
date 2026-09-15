# Phase-1-Prüfbericht

Prüfzeitraum: **10.–11.09.2026**. Anwendung 0.1.0, lokaler Arbeitsstand ohne Git-Commit. **Der definierte lokale M1-Entscheidungsablauf ist implementiert und technisch geprüft.** Menschliche Abnahme und Produktionsfreigabe sind davon getrennt.

Der [maschinenlesbare Nachweis](phase1-evidence.json) enthält Messwerte, Imagekennungen, sanitiserte Befunde und Restore-Prüfsummen. Rohberichte und vertrauliche Dumps bleiben ausschließlich unter .local.

## Umgebung und Ergebnisse

Windows/AMD64, Intel Family 6 Model 181 Stepping 0, 14 in der Linux-VM sichtbare CPUs. Python lokal 3.12.14, Node lokal 24.19.0, pnpm 11.19.0; Docker Desktop 4.76.0, Engine 29.5.2, Compose 5.1.4. Container: Python 3.14.7 auf Alpine 3.24.1, Node 24.20.0, PostgreSQL 18.6, Keycloak 26.7.3, Nginx 1.30.4. Basisimages sind per Digest festgelegt; abgeleitete Images stehen in den Dockerfiles.

| Prüfung | Beobachtetes Ergebnis |
| --- | --- |
| Backend auf echtem PostgreSQL, letzter Lauf 11.09. | **126 bestanden**, 0 übersprungen, 6,02 s auf Alpine; darunter sechs DB-Integrationstests |
| Lokales Windows-Backend, Lauf 10.09. | 120 bestanden, sechs ausdrücklich DB-abhängige Fälle übersprungen |
| Ruff | Format und Lint für 70 Python-Dateien bestanden |
| mypy strict | keine Fehler in 32 Backend-Quelldateien im Linux-Testimage |
| Frontend im Linux-Testbuild | Format, ESLint, TypeScript, Vite-Build und **6 Vitest-Tests bestanden** |
| Chromium, echter OIDC, letzter Lauf 11.09. | **3 Browsertests bestanden**, 8,4 s |
| Scanner-Einordnung und Restore-Fehlerbehandlung | **12 Skripttests bestanden**: neun Policyfälle, drei Bereinigungs-/Wiederanlauffälle |
| Gesperrte direkte/transitive Projektabhängigkeiten | pip-audit 0 bekannte Lücken; pnpm audit 0 Meldungen aller Schweregrade |
| Trivy 0.74.0 | bekannte synthetische Secret-/axios-Fixture erkannt; Quellen und vier Images vollständig geprüft |
| HTTP-Leistung | beide Referenzziele erreicht; Details unten |
| Laufzeit-/Ausfallübung 11.09. | DB-Ausfall: Readiness 503, Liveness 200; Wiederanlauf erfolgreich; gesamte Übung 17,005 s |
| Backup/Restore 11.09. | beide DBs, frisches getrenntes Volume, Hashes, RLS, Testpasswortrotation und **4 echte Browserprüfungen am restaurierten Stack bestanden** |
| Generierte Verträge | erneute Generierung ergibt identische Dateien |
| GitHub Actions | Workflow vorhanden; **kein Remote-Lauf ausgeführt** |
| Live-KI, ARM, produktives TLS | **nicht ausgeführt** |

Die Starlette-/AnyIO-DeprecationWarning im TestClient bleibt eine Upstream-Warnung. Es wurde dafür keine Sicherheitsprüfung deaktiviert.

## Durchgängige Browserfälle

1. Echter Keycloak-Login als Analyst, Organisation auswählen, synthetisches Szenario speichern und neu laden; Wirtschafts- und Leistungsbewertung derselben Profilversion; gespeicherte Ergebnisse vergleichen; RAM-Angabe in einer neuen Version entfernen; keine erfundene Empfehlung; altes Ergebnis bleibt erhalten. Direkte fremde Szenario-/Bewertungs-IDs liefern keinen Inhalt. Logout verhindert erneuten Zugriff.
2. Viewer kann lesen und sieht keine Schreib- oder Administrationsaktionen. Serverseitige Ablehnung wird zusätzlich gegen echte PostgreSQL-Rollen geprüft.
3. Persistierter HTML-/Skript-Testtext bleibt nach Reload Text. Es entstehen weder Bilder noch Dialoge oder Anfragen zur Test-Fremddomain. CSP, nosniff, Frame-Schutz, API-no-store und gesperrter IdP-Adminpfad werden geprüft. Tastatursprung fokussiert den Hauptinhalt. Szenario und Ergebnis passen bei 390 × 844 Pixeln ohne seitenweiten horizontalen Überlauf.

Ein vierter Fall wird im vollständigen Restorelauf aktiviert: Nach echtem Login am restaurierten IdP muss eine bereits vor dem Backup gespeicherte Bewertung denselben Hash und ihre bestätigte Empfehlung zeigen, auch nach Reload. Der Teststack startet ohne Migration oder Demo-Seeding.

Eine visuelle Desktop-/Mobilprüfung der deutschen Ergebnisansicht wurde ergänzend durchgeführt. Sie ersetzt keinen vollständigen Barrierefreiheitsaudit. Provider-Ausgaben werden als Text gerendert; die Browserstrecke verwendet keinen Live-KI-Aufruf.

## Leistung

Erster vollständiger HTTP-Lauf am 10.09.: Einzelabrufe p95 734,933 ms, Listen 1.356,822 ms, Bewertungen 1.461,090 ms. Das Leseziel war verfehlt.

Nach gebündelten DB-Abfragen und angepasster Poolgröße: 100 Einzelabrufe, zehn Listenabrufe mit je 25 Einträgen und zehn Bewertungen, zehn parallele reguläre Sessions einer synthetischen Adminidentität in Testmandant B. Nach dem Basisimage-Wechsel 300 gespeicherte Szenarien; erneut gemessen am 11.09. um 08:24 UTC:

| Operation | p95 | Maximum | Ziel |
| --- | --- | --- | --- |
| Szenario lesen | 209,824 ms | 238,911 ms | unter 500 ms |
| Liste lesen | 128,669 ms | 128,669 ms | unter 500 ms |
| Bewertung erstellen | 313,643 ms | 313,643 ms | unter 2.000 ms |

Der vorherige bereits erfolgreiche Lauf bei 200 Szenarien erreichte p95 433,852 / 338,812 / 807,785 ms. Die Messungen erfüllen das Referenzziel; sie isolieren nicht den Einfluss einzelner Laufzeit- oder Hostfaktoren.

Gemessen wurde Nginx → HTTP → API → PostgreSQL, nicht nur eine Funktion. Die API hatte ein Speicherlimit von 768 MiB, PostgreSQL 1 GiB, Keycloak 1 GiB, Nginx 128 MiB. Die Sessions gehören einer Testidentität, nicht zehn unterschiedlichen Menschen. Der Test erzeugt pro Lauf weitere 100 ausdrücklich synthetische Szenarien; er darf nur in der lokalen Demo laufen. Diese begrenzte Stichprobe ist keine Langzeit-, Spitzenlast- oder Cloud-SLA-Zusage.

Separat: Domänenbenchmark mit zehn Arbeitslasten und vier Plänen einschließlich Verifier, 100 Messungen nach fünf Aufwärmläufen: Median 32,789 ms, p95 49,910 ms, Maximum 62,343 ms. Python 3.12.14 unter Windows, ohne HTTP und DB.

## Sicherheit und Betrieb

Trivy-Bericht vom 11.09. um 08:25 UTC: **0 Geheimnisse**, zwei verbleibende behebbare hohe/kritische Komponentenmeldungen mit exakt begründeter befristeter Einordnung, **0 unbehandelte behebbare hohe/kritische Befunde**. Gegenüber ursprünglich 42 wurden 40 Komponentenmeldungen durch Updates beziehungsweise Entfernung entbehrlicher Werkzeuge beseitigt. Quellenprüfung und getrennte Lockfile-Audits sind ohne Befund.

Der geprüfte API-Wechsel von Debian Bookworm auf Alpine beseitigt zusätzlich alle zuvor 60 hohen/kritischen API-Meldungen. Ein Vergleichskandidat auf Debian Trixie hatte noch 54. Das endgültige API-Image hat im aktuellen Scan keine Paket-Schwachstellen. Es verbleibt **eine hohe Meldung ohne Herstellerfix**, CVE-2026-22020 im Java-Runtime-Paket von Keycloak. Diese bleibt zur weiteren Betriebshärtung offen; die genaue Version steht im Nachweis. Der lokale Demonstrator verarbeitet ausschließlich synthetische Daten und ist kein öffentlicher Dienst.

Die Keycloak-Einordnungen gelten nur für den exakten Digest, Paket und Dateipfad bis 10.10.2026; Netty zusätzlich nur bei bestätigtem lokalem HTTP-Profil. Ablauf oder unbekannte Konfiguration blockieren erneut. Details, Herstellerquellen und Wartungsrolle: [ADR 0003](../adr/0003-phase1-security-and-performance.md).

Laufzeitprüfung: API UID 10001, Proxy UID 101, Keycloak UID 1000; PostgreSQL-Prozess unter postgres. Keine privilegierten Container oder Hostsocket-Mounts. API/Proxy haben schreibgeschützte Root-Dateisysteme. Nur 127.0.0.1:8080 ist veröffentlicht. Keycloak und PostgreSQL besitzen weiterhin die für ihren Betrieb schreibbaren Bereiche.

Vollständiger Restore am 11.09. um 08:27 UTC: vollständige Dumps von platform und keycloak in einem eigenen Compose-Projekt und neuen Volume eingespielt. Hashes und Anzahlen von 16 fachlich relevanten Plattformtabellen und drei IdP-Kerntabellen stimmen überein; alle 19 Plattformtabellen behalten FORCE RLS. Die App-Rolle sieht ohne Mandantenkontext null Szenarien. API-/Web-Neustart bewahrt fachliche Daten. Zusätzlich wird ausschließlich im neuen Testprojekt das App-DB-Passwort rotiert: alter TCP-Zugang abgewiesen, neuer angenommen. Das Testprojekt wird anschließend entfernt; das Originalvolume bleibt bestehen.

Zusätzlich wurden API, Proxy und Keycloak direkt gegen die restaurierten Datenbanken gestartet. Vier Browserfälle bestätigten dort echten OIDC-Login, Fachabläufe, Rechte und den Hash eines historischen Ergebnisses. Der Originalproxy war nur für diese Phase pausiert und wurde nach Bereinigung automatisch wieder gestartet. Der Erfolgsbericht entsteht erst danach. Damit ist der zuvor offene vollständige OIDC-Restore-Nachweis geschlossen. [ADR 0004](../adr/0004-api-base-and-complete-restore.md).

## Zuordnung der Sicherheitsfälle

| Testbereich | Konkrete Nachweise |
| --- | --- |
| SEC-01/02/03 | OIDC-/JWT-/State-/Nonce-/PKCE-, Cookie-, Session- und CSRF-Negativfälle; echter Login, Logout, Organisationswechsel; Rollenwiderruf für bestehende Sitzung |
| SEC-04/05/06 | echte Rollen und FORCE RLS, fehlender Tenantkontext, Fremdmandant, zusammengesetzte FK; Liste, Einzelobjekt und Vergleich |
| SEC-07 | Domain-/Propertytests für ungültige Mengen, Gewichte, Versionen und unabhängige Nachrechnung |
| SEC-08 | gespeicherter XSS-Text, keine Fremdbilder/-anfragen, sichere Header und Fehlermeldungen |
| SEC-09/12 | unveränderliche Historie, atomarer Audit-/Fachrollback, Versionskonflikt, idempotente Bewertung und konkurrierende Erklärungsanfragen |
| SEC-10/11/21 | minimierter Provider-Port, keine Tools/Retry, Schema-/Evidenzprüfung, Budgetreservierung und Providerfehler; ausdrücklich Test-Double |
| SEC-20 | Scanner erkennt bekannte Fixture; Projekt-/Imageinventur; tatsächlich unprivilegierte Laufzeit und keine Hostsocket-Freigabe |
| SEC-22 | Body-/Rate-/Querygrenzen, interne DB/IdP-Ports, DB-Ausfall, Wiederanlauf, Restore und Testpasswortrotation |

Die Zuordnung beschreibt ausgeführte Fälle im M1-Scope, keine pauschale Absicherung aller späteren Plattformmodule.

## Review aus sechs Perspektiven

Dies ist die geforderte Selbstprüfung, kein behauptetes unabhängiges Audit.

| Perspektive | Befund und Behandlung |
| --- | --- |
| Architektur | Modularer Monolith und unabhängiger Verifier beibehalten; gebündelte Listenabfrage mit explizitem Vertrag und DB-Regression eingeführt. |
| Sicherheit | Image-Werkzeuge und Alpine-Komponenten bereinigt; enge befristete Einordnungen geprüft; offene Herstellerbefunde sichtbar dokumentiert. |
| Daten | Ursprungsstände unverändert, Herkunftshashes und FK/RLS wirksam; Rollback und frischer Restore geprüft. |
| Qualität | Echter OIDC-/DB-Ablauf ergänzt die Unitprüfungen; fehlender mobiler Textumbruch entdeckt und behoben; keine DB-/Browser-Mocks als Abnahmenachweis. |
| Betrieb | Readiness enthält DB/Migration/IdP; Ausfall und Wiederanlauf getestet; Nginx-Tempverzeichnisse korrigiert; Socket-Startproblem von Docker Desktop als Hostgrenze festgehalten. |
| Wartbarkeit | Deutsche Moduldateien, ADRs, gesperrte Abhängigkeiten, reproduzierbare Typverträge und ausführbare CI gepflegt. |

## Wiederholbare Prüfbefehle

```sh
python -m ruff check --config apps/api/pyproject.toml apps/api/src apps/api/tests scripts
python -m ruff format --check --config apps/api/pyproject.toml apps/api/src apps/api/tests scripts
python -m mypy --config-file apps/api/pyproject.toml apps/api/src/platform_app
python -m pytest apps/api/tests -p no:cacheprovider -q
python -m unittest discover -s scripts -p "test_*.py"
python scripts/generate_contracts.py
python scripts/check_docs.py
pnpm --dir apps/web run format:check
pnpm --dir apps/web run lint
pnpm --dir apps/web run build
pnpm --dir apps/web run test
python -m pip_audit --disable-pip --no-deps -r apps/api/requirements.lock
pnpm --dir apps/web audit --audit-level moderate
docker compose --profile test run --build --rm tests
python scripts/run_e2e.py
python scripts/check_runtime.py
python scripts/check_restore.py --full-stack
python scripts/install_trivy.py
python scripts/check_security.py
python scripts/benchmark_http.py
```

Für den Restore mit isolierten Browserabhängigkeiten: python scripts/check_restore.py --full-stack --isolated-browser. Der lokale Windows-mypy-Aufruf wurde beim letzten Wiederholungslauf durch die Anwendungssteuerung blockiert; die strenge Prüfung wurde erfolgreich im Linux-Testimage ausgeführt, ohne die Windows-Schutzrichtlinie zu ändern.

Bei OneDrive-Paketlesefehlern: python scripts/run_e2e.py --isolated. Der letzte erfolgreiche Browserlauf nutzte diese isolierte Kopie der unveränderten Tests und Lockfiles; er griff auf den echten lokalen Stack zu. Alternativer Linux-Frontendprüflauf:

```sh
docker build -f infra/proxy/Dockerfile --target test -t unternehmensplattform-web-tests:0.1.0 .
```

Die CI führt Prüfkommandos aus und bricht bei Fehlern ab. Ein tatsächlicher GitHub-Actions-Lauf, ein frischer zweiter Rechner, ARM, Live-KI und produktives TLS wurden nicht geprüft.
