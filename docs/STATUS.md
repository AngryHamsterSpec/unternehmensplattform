# Projektstatus

Stand: **14.09.2026**. **M2 ist gemäß ausdrücklicher Nutzerentscheidung erledigt; der vereinbarte lokale Funktionsumfang ist IMPLEMENTIERT und integriert.** Datei-/Datenbankworkflow, Regeln, Vollanalysen, Berichte, assistierte Bereinigung und Versionsfreigabe sind geprüft. Browser, RLS und Betriebsgrenzen bestanden. **Der aktuelle Restore-Nachweis bleibt offen:** Der zugelassene letzte Lauf brach vor dem Backup beim Prüfsummenvergleich von `data_chunks` nach 180 Sekunden ab. Keine vollständige technische Restore-Abnahme wird behauptet. [Abschlussbericht](testing/M2_COMPLETION_REPORT.md). Dataset-Quote weiterhin **1000**. **Stopp nach M2; M3 wurde nicht begonnen.** Live-KI bleibt NICHT LIVE GETESTET; keine Produktivfreigabe.

Der Nutzer hat Phase 1 und anschließend ausdrücklich den nächsten M2-CSV-Arbeitsschritt aktiviert. Master Prompt und Phase-0-Entwurf bleiben die Grundlage. Eine zusätzliche menschliche Abnahme oder produktive Betriebsfreigabe wird nicht behauptet.

## Statusbegriffe

| Begriff | Bedeutung |
| --- | --- |
| IMPLEMENTIERT | konkreter Umfang vorhanden, relevante erfolgreiche Nachweise genannt |
| TEILWEISE IMPLEMENTIERT | benannter Teil vorhanden, verbleibende Lücken ausgewiesen |
| EXPERIMENTELL | Erprobung ohne reguläre Betriebszusage |
| NICHT IMPLEMENTIERT | geplant oder offen |
| BENÖTIGT EXTERNE ZUGANGSDATEN | externe Verbindung benötigt eigene Konfiguration |
| NICHT LIVE GETESTET | kein Nachweis gegen den realen externen Dienst |

## Lieferstand

| Bereich | Stand |
| --- | --- |
| Phase-0-Artefakte, Master Prompt, Projektverfassung | ausgearbeitet und erhalten |
| Vier Architekturpläne, Dezimal-TCO, harte Bedingungen, Sensitivität und unabhängiger Verifier | IMPLEMENTIERT; Domänen-, Regressions- und Propertytests bestanden |
| OIDC, Sessions, Organisationsrollen, CSRF | IMPLEMENTIERT; echter Keycloak-Login, Logout und negative Rechteprüfungen bestanden |
| Profilversionen, Bewertungen, Audit, PostgreSQL-RLS | IMPLEMENTIERT; sechs echte DB-Integrationstests, unveränderliche Historie, Idempotenz und Rollback geprüft |
| Deutsche Szenario-, Ergebnis-, Vergleichs- und Verwaltungsoberfläche | IMPLEMENTIERT; Build, sechs Frontendtests und drei Browserabläufe bestanden |
| Optionale OpenAI-Erklärung | Adapter implementiert; Vertrags-/Fehlerprüfungen mit Test-Double bestanden; NICHT LIVE GETESTET; BENÖTIGT EXTERNE ZUGANGSDATEN |
| Docker auf Windows/AMD64 mit Linux-Containern | IMPLEMENTIERT und gestartet; Ausfall, Wiederanlauf und Containergrenzen geprüft |
| Backup/Restore | IMPLEMENTIERT; beide Datenbanken in frischem getrenntem Volume wiederhergestellt; Hashes, RLS, Testpasswortrotation und fünf echte Browserprüfungen einschließlich historischer CSV-Version ohne erneutes Seeding bestanden |
| CI | ausführbarer GitHub-Actions-Workflow vorhanden; kein Remote-Lauf durchgeführt |
| Dokumentation | README/EXPLAIN/TESTING für alle sechs Backendmodule; API, ADRs und Nachweise gepflegt |
| M1 | IMPLEMENTIERT im begrenzten lokalen Demo-Umfang; unten genannte Betriebs-/Portabilitätsgrenzen bleiben offen |
| M2 / Modul C | IMPLEMENTIERT; gemäß Nutzerentscheidung erledigt. Vereinbarte Formate, Analysen, Regeln, Berichte, Bereinigung und Versionen lokal geprüft. Aktueller Restore-Nachweis wegen Prüfsummen-Timeout offen; optionaler KI-Adapter nur mit Test-Double geprüft |
| Spätere Module D–F/H–J | NICHT IMPLEMENTIERT |
| Veröffentlichung und produktiver Betrieb | nicht erfolgt |

## Historische M2-Teilschritte

Die folgenden datierten Einträge beschreiben den damaligen Stand. Frühere offene M2-Funktionen sind durch den oben verlinkten Abschlussbericht fortgeschrieben; historische Messergebnisse und Betriebsgrenzen bleiben erhalten.

## Dateien bis 1 GiB (12.09.2026)

Am 12.09.2026 ausdrücklich beauftragt. Upload in 4-MiB-Abschnitten, PostgreSQL-Abschnittsspeicher, dateibasierte Verarbeitung, Worker-Leases/Fortschritt/Abbruch und gestreamte Downloads sind umgesetzt. 189 Backendtests und Typprüfung über 44 Quelldateien bestanden. Vollständiger 1-GiB-Import einschließlich Profiling und beider Download-Hashes bestanden; 10 Frontendtests erfolgreich. Fünf reguläre Browserabläufe, Runtime-Grenzen und Security-Gate bestanden. Vollständiger erneuter Restore-Abschluss bleibt offen; siehe [aktuellen Prüfbericht](testing/M2_LARGE_CSV_REPORT.md).

## Historische Nachweise des ersten M2-CSV-Ablaufs

- **169 Backendtests**, darunter 35 CSV-Domänenfälle und acht zusätzliche echte PostgreSQL-Prüfungen; keine übersprungenen DB-Tests.
- **9 Frontendtests**, vier reguläre Browserabläufe und fünf Browserprüfungen gegen den wiederhergestellten Stack bestanden.
- 40 Quelldateien streng typgeprüft, 83 Python-Dateien formatiert/lintgeprüft, 13 Skriptprüfungen bestanden; Frontend-Build und generierte Verträge geprüft.
- Workergrenzen, Datenbankausfall, Wiederanlauf, Originalbytes und historische CSV-Prüfsummen nach Restore nachgewiesen.
- Abschließender Projekt-/Imagescan erfolgreich: API und Web ohne Paketbefund; bekannte Keycloak-Grenzen bleiben bestehen.

Details und Grenzen: [M2-CSV-Prüfbericht](testing/M2_CSV_REPORT.md), [maschinenlesbare Nachweise](testing/m2-csv-evidence.json). Weitere Formate/Analysen und administrative Dead-Letter-Verwaltung bleiben offen; Auftragsabbruch wurde mit der 1-GiB-Erweiterung ergänzt.

## Historische M1-Nachweise

- **126 Backendtests bestanden**, keine übersprungenen DB-Tests im Linux-/PostgreSQL-Lauf.
- **6 Frontendtests**, **3 reguläre Chromium-Browserabläufe** und **4 Browserprüfungen gegen den wiederhergestellten Stack** bestanden; einschließlich XSS-Text, Header, Tastatur und 390-Pixel-Ansicht.
- Ruff für 70 Python-Dateien, strenge mypy-Prüfung im Linux-Testimage für 32 Quelldateien, ESLint, TypeScript und Build erfolgreich; generierte Verträge unverändert reproduziert.
- Zehn parallele Sessions, 300 Szenarien: p95 Einzelabruf **209,824 ms**, Liste **128,669 ms**, Bewertung **313,643 ms**. Referenzziele erreicht; keine allgemeine Skalierungszusage.
- Trivy-Scannerfixture erkannt; **0 Geheimnisse**, **0 unbehandelte behebbare hohe/kritische Befunde** nach zwei eng begrenzten befristeten Einordnungen.

Exakte Kommandos, Messumgebung, Fehlerkorrekturen und Grenzen: [Prüfbericht](testing/PHASE_1_REPORT.md). Maschinenlesbarer sanitiserter Nachweis: [phase1-evidence.json](testing/phase1-evidence.json).

Zwölf ergänzende Skriptprüfungen bestehen: neun zur befristeten Befundbewertung und drei zur sicheren Wiederaufnahme der Demo bei Restore-Fehlern.

## Verbleibende Grenzen

Die Imageinventur enthält noch **eine hohe Meldung ohne verfügbaren Herstellerfix** im Keycloak-Java-Runtime-Paket (CVE-2026-22020). Die zuvor 60 hohen/kritischen API-Meldungen wurden durch den geprüften Wechsel auf das offizielle Alpine-Python-Image beseitigt; dessen Scan enthält keine Paket-Schwachstellen. Zwei weitere Keycloak-Meldungen wurden genau begrenzt bewertet; diese Einordnungen laufen am **10.10.2026** aus. Sie ersetzen keine allgemeine Sicherheitsfreigabe. [ADR 0003](adr/0003-phase1-security-and-performance.md) erklärt Scope, Gründe und Wartungsverantwortung.

ARM, produktiver TLS-Betrieb, echte Unternehmensdaten, Live-KI und ein Remote-CI-Lauf bleiben ungeprüft beziehungsweise nicht freigegeben. Der vollständige Restore-Nachweis umfasst beide Datenbanken, echten OIDC-Login am wiederhergestellten IdP, historische Bewertung, Rechteprüfungen und Wiederaufnahme der Originaldemo. [ADR 0004](adr/0004-api-base-and-complete-restore.md) dokumentiert Basisimage und Ablauf.

Docker Desktop 4.76.0 zeigte auf diesem Windows-Rechner wiederholt einen Startfehler durch alte leere Socket-Dateien. Eine reversible Sicherung ausschließlich dieser Laufzeitverzeichnisse stellte den Betrieb wieder her. Das ist ein bekannter Hostfehler, keine zugesagte dauerhafte Docker-Reparatur. Image- und Datenvolumes wurden dabei nicht zurückgesetzt.

Der aktuelle M2-Nachweis steht im [CSV-Prüfbericht](testing/M2_CSV_REPORT.md); der vorherige Phase-1-Bericht bleibt als historischer Nachweis erhalten.

Der Branch ist weiterhin der ursprüngliche master ohne Commit; alle Projektquellen liegen lokal. Es wurde nichts gepusht oder veröffentlicht.


## Implementierter Umfang: moderne Diagramme

Am 12.09.2026 ausdrücklich beauftragt. Apache ECharts 6.1.0 mit Balken, Ring, Datenqualität, Histogramm, Linie und Streudiagramm; interaktive und statische Ansicht, Filter, Zoom, Tabelle, SVG/PNG. API-Auswahl begrenzt und versionstreu. 14 Frontendtests, fünf gezielte PostgreSQL-Fälle, strenge Typprüfung über 45 Dateien und ein echter Browserablauf mit allen Diagrammtypen, Bildexporten und Versionswechsel bestanden. npm-Laufzeitaudit ohne gemeldete Befunde. [Visualisierungsbericht](testing/M2_VISUALIZATION_REPORT.md).

Auf ausdrücklichen Nutzerwunsch werden hier kurze relevante Prüfungen ausgeführt; der bestandene 1-GiB-Lasttest und die vollständigen langen Betriebsabläufe werden nicht wiederholt.

## Aktuelle CSV-Reparatur

Migration 0004 und robuste CSV-Leseoptionen sind lokal aktiviert. Gezielte Unit-, PostgreSQL-, Typ-, Build- und Frontendprüfungen bestanden. Alle fünf beanstandeten Originalimporte sind erfolgreich veröffentlicht; vollständiger Originalhash/Export, große Bearbeitungsvorschau und gezielter OIDC-Browserablauf bestanden. Abschlussstand im [CSV-Reparaturbericht](testing/M2_CSV_RECOVERY_REPORT.md). M2 bleibt insgesamt TEILWEISE IMPLEMENTIERT.

## M2-Fortsetzung: JSON/JSONL

IMPLEMENTIERT im Umfang flacher UTF-8-Tabellen: Abschnittsupload, begrenzter Reader, Profiling, Vorschau, bestätigte Version, Diagramme und CSV-Export. Zwölf neue Formatfälle, zwei echte PostgreSQL-Abläufe, 47 Quelldateien typgeprüft, 14 Frontendtests, Builds, Lint/Format, Quellscan und kombinierter OIDC-Browserfall bestanden. [Nachweis und Grenzen](testing/M2_JSON_REPORT.md).

Nächste M2-Ausbauschritte: Datenbankquellen, weitergehende Statistiken/Qualitätsregeln und beaufsichtigte KI-Transformationsvorschläge. Agenten erhalten weiterhin typisierte Verträge und minimale Toolrechte; Freigaben und Berechnungen bleiben deterministisch. Keine neue Live-KI wird für diese Datenadapter behauptet.

## Produktdesign und XLSX (12.09.2026)

Gemeinsame IT-Kompass-Gestaltung mit semantischen Tokens, lokaler IBM Plex Sans, einheitlichen Tabellen/Formularen/Diagrammen und Dichtewahl implementiert. Datenkatalog mit Filter und Nachladen. XLSX-Import mit Blattwahl verwendet dieselbe nachvollziehbare Datenpipeline. Keine neue Live-KI; M2 bleibt insgesamt TEILWEISE IMPLEMENTIERT. 53 gezielte Backend- und vier PostgreSQL-Fälle, 48 typgeprüfte Quelldateien, 14 Frontendtests und fünf OIDC-Browserabläufe bestanden; Quellscan und pip-audit ohne Befund. [Aktueller Prüfbericht](testing/M2_PRODUCT_XLSX_REPORT.md).

Mobiler Abschluss am 13.09.2026: breite Tabellen mit internem Scrollen; Produktionsbuild und gezielter 390px-/Tastatur-/XSS-Browserfall bestanden. Aktueller Webstand lokal aktiv, API/PostgreSQL/Web gesund, Datenworker und IdP laufen.

## M2-Fortsetzung: Parquet (13.09.2026)

IMPLEMENTIERT für einzelne flache Dateien: Upload, Profil, Bereinigungsvorschau, bestätigte Version und CSV-Export; Original unverändert. 62 gezielte Unitfälle, echter PostgreSQL-Ablauf, 50 typgeprüfte Quelldateien, 14 Frontendtests und eigener OIDC-Browserablauf bestanden. 100.003 synthetische Zeilen unter 256 MiB/1 CPU verarbeitet, Spitzen-RSS 101,32 MiB. Quellscan und pip-audit ohne Befund. [Nachweis und Grenzen](testing/M2_PARQUET_REPORT.md). M2 bleibt insgesamt TEILWEISE IMPLEMENTIERT.

## Vertieftes Enterprise-Design (13.09.2026)

IMPLEMENTIERT und lokal aktiv: eigene mineralische/graphitgrüne Gestaltung, gruppierte responsive Navigation, Bestandsübersichten, Datenstandfilter, aufklappbarer Import und direkter Zugang zur Bereinigung. Finaler Frontendbuild, Typen/Format/Lint und 16 Komponententests bestanden; sechs relevante Browserfälle im ersten beziehungsweise gezielten Abschlusslauf erfolgreich. [Prüfbericht mit genauer Abgrenzung](testing/M2_ENTERPRISE_DESIGN_REPORT.md). Keine Backend-/Abhängigkeitsänderung. M2 bleibt TEILWEISE IMPLEMENTIERT; als Nächstes Datenbankquellen und weitere Qualitäts-/Agentenfunktionen.

**Aktuelle Dataset-Quote:** Der Nutzer hat `dataset_limit_per_organization` zentral konfigurierbar gemacht und den Default auf **1000** erhöht. Importpfade verwenden `check_dataset_quota(db)`. Diese beabsichtigten manuellen Änderungen bleiben erhalten; die frühere feste 100er-Grenze ist kein offener Fehler. Die historischen Excel-/Parquet-Abschlussprüfungen erfolgten im synthetischen Testmandanten B. Eine langfristig isolierte Testumgebung bleibt sinnvoll.

## M2-Fortsetzung: SQLite-Snapshots (13.09.2026)

IMPLEMENTIERT und lokal aktiv: Snapshot-Upload, Tabellenwahl/Korrektur ohne erneuten Upload, Profil, Bereinigungsvorschau, bestätigte Version, Herkunft und CSV-Export. 48 gezielte Linux-Backendfälle einschließlich echtem PostgreSQL-/RLS-/Rollenablauf, 51 typgeprüfte Quelldateien, 16 Frontendtests und ein vollständiger OIDC-Browserfall bestanden. Quellscan ohne gemeldete Befunde. Wirksame Dataset-Quote im aktualisierten API-Container: **1000**. [Prüfbericht und Grenzen](testing/M2_SQLITE_REPORT.md).

M2 bleibt TEILWEISE IMPLEMENTIERT. Als Nächstes direkte Netzwerk-Datenbankquellen mit eigenem Secret-/Verbindungs-/Snapshotvertrag, weitere Qualitätsregeln/Statistik und beaufsichtigte Agentenvorschläge. SQLite ist ein Snapshot-Adapter und keine Liveverbindung; keine neue Live-KI.
