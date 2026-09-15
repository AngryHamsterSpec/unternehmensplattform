# M2 — Prüfbericht des ersten CSV-Ablaufs

Stand: 11.09.2026. Der CSV-Teil ist implementiert und lokal technisch geprüft. Das vollständige Modul C bleibt TEILWEISE IMPLEMENTIERT.

## Gegenstand

Import → persistenter Auftrag → Profiling → manuelle Pipeline → gespeicherte Vorschau → bestätigte Version → interaktive Werteverteilung → CSV-Export. Ursprüngliche M1-Daten bleiben erhalten; Migration 0002 ergänzt vier Tabellen mit FORCE RLS und zusammengesetzten Fremdschlüsseln. Kein externer KI-/Cloud-Aufruf.

## Tatsächlich ausgeführte Prüfungen

| Prüfung | Ergebnis |
| --- | --- |
| Backend in Linux / echtem PostgreSQL | 169 bestanden, 0 übersprungen, 11,24 Sekunden |
| CSV-Domänenfälle lokal | 35 bestanden |
| Strenge mypy-Prüfung | 40 Quelldateien ohne Fehler |
| Frontend Linux-Testimage | TypeScript/Vite, ESLint, Prettier und 9 Vitestfälle bestanden |
| Regulärer Browserlauf | 4 bestanden in 18,9 Sekunden; CSV/Version/Export und gespeicherte Vorschau nach Reload |
| Skriptprüfungen | 13 bestanden, einschließlich automatischer Worker-Wiederaufnahme bei Backupfehlern |

Die acht neuen PostgreSQL-Prüfungen verwenden echte Datenbanken. Die vorgelagerte Authentifizierung wird dort als Sessionfixture eingerichtet; der Browserlauf nutzt den echten OIDC-Codefluss.

## Korrekturen während der Prüfung

Ein Summenstartwert wurde für Decimal explizit gesetzt, damit die Typprüfung keine alternative Float-Arithmetik zulässt. Sehr große parametrisierte Testdaten erhielten kurze Testnamen, nachdem Windows die automatisch erzeugte Umgebungsvariable ablehnte. Ein JSX-Syntaxfehler in der ergänzten Vorschau-Auswahl wurde vor erfolgreichem Neubau behoben. Die lokale Demo wurde erst nach dem jeweiligen Build aktualisiert.

## Grenzen

Dies ist ein begrenzter lokaler CSV-Demonstrator. Auftragsabbruch und Dead-Letter-Verwaltung sind noch offen; PostgreSQL-Transaktionslocks ersetzen im begrenzten ersten Worker die Lease-Verwaltung. JSON, XLSX, Parquet, Datenbankquellen, S3, allgemeine Qualitätsregeln, weiterführende Statistik und KI-Vorschläge sind offen. Kein Remote-CI-Lauf, ARM- oder produktiver TLS-Nachweis. Bestehende Keycloak-Sicherheitseinordnungen bleiben gesondert dokumentiert.

Verträge und Entscheidungen: [M2-Auftrag](../prompts/PHASE_2_IMPLEMENTATION_PROMPT.md), [ADR 0005](../adr/0005-bounded-csv-data-workflow.md), [Datenmodul](../../apps/api/src/platform_app/data/README.md).

## Wiederherstellung und Betrieb

Der vollständige Restore vom 11.09.2026, 13:37 UTC hat beide Datenbanken in einem getrennten neuen Volume wiederhergestellt. Alle gesicherten Tabellenstände, darunter die vier neuen Datentabellen mit Original-/Ergebnisbytes, stimmen überein. FORCE RLS und Rotation des Testpassworts wurden erneut geprüft.

**Fünf Browserprüfungen bestanden** gegen restaurierten Keycloak, API, Web und Datenworker, ohne Migration oder erneutes Seeding. Dabei wurden eine historische Architekturentscheidung und CSV-Version 2 mit ihren ursprünglichen Hashes geöffnet und nach Neuladen wiedergefunden. Originalproxy und Originalworker wurden wieder gestartet.

Die anschließende Laufzeitprüfung vom 13:38 UTC bestätigt Datenworker UID 10001, 256 MiB, eine CPU, schreibgeschütztes Root-Dateisystem, ausschließlich internes Datennetz, keine veröffentlichten Ports und keine OIDC-/KI-/Auth-/Migrationszugänge. Datenbankausfall: Readiness 503, Liveness 200, Wiederanlauf erfolgreich; Übung 18,008 Sekunden. Nach der mehrstündigen Arbeitsunterbrechung liefen alle fünf Dienste weiterhin; API, PostgreSQL und Web meldeten healthy.

## Abschließender Sicherheitsscan

Trivy 0.74.0, Scannerfixture erfolgreich, letzter Report: 2026-09-11T20:43:32.796889+00:00. Geprüft wurden ausschließlich die Projektquellen und die vier benannten Projektimages. Der Datenworker verwendet das gleiche API-Image.

- 0 gefundene Geheimnisse.
- API- und Web-Image: keine gemeldeten Paket-Schwachstellen.
- 0 unbehandelte behebbare hohe/kritische Befunde.
- Zwei eng begrenzte Keycloak-Einordnungen, gültig bis 10.10.2026.
- Eine verbleibende hohe Keycloak-Java-Meldung ohne Herstellerfix: CVE-2026-22020.

Der erste Versuch des erneuten Scans wurde durch die automatische Freigabeprüfung wegen eines Nutzungslimits abgelehnt. Nach dem angegebenen Rücksetzzeitpunkt wurde der gleiche begrenzte Auftrag über die reguläre Freigabeprüfung erneut zugelassen und erfolgreich ausgeführt. Es wurde kein Freigabemechanismus umgangen.

## Letzter Anzeige-Build und Nachvollziehbarkeit

Nach dem vollständigen Browser-/Restore-Ablauf wurden ausschließlich die deutsche Dezimaldarstellung und die sichtbare Pipelineversion korrigiert. Der danach gebaute Frontend-Teststand hat Format-, Lint-, Typ-/Build- und neun Komponententests bestanden; der letzte Sicherheitsscan umfasst auch diesen Web-Build. Kein erneuter vollständiger Backend-/Restore-Lauf war für diese Anzeigeänderung erforderlich.

Die maschinenlesbaren Nachweise stehen in [m2-csv-evidence.json](m2-csv-evidence.json). Quelldateien und Dokumentation liegen lokal; kein Commit, Push oder Deployment in eine externe Umgebung wurde durchgeführt.

Die abschließende Browser-Sichtprüfung bestätigt den Mittelwert 180,25 und den sichtbaren Verfahrensstand csv-transform-1 im gespeicherten synthetischen Datensatz „Musterwerk · Datenqualität“. [Screenshot](../screenshots/m2-datenwerkstatt.png).
