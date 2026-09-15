# Unternehmensplattform

Deutsche Arbeitskonsole für IT-Architekturentscheidungen und Datenqualität: Unternehmensszenarien bewerten, Kosten und Alternativen vergleichen sowie tabellarische Dateien und freigegebene Datenbankquellen prüfen, analysieren, nachvollziehbar bereinigen und versioniert exportieren.

**M1 und der vereinbarte M2-Funktionsumfang sind lokal implementiert und geprüft. M2 ist auf Nutzeranweisung erledigt; der aktuelle Restore-Nachweis bleibt wegen Timeout offen. M3 wurde nicht begonnen. [Abschlussbericht](docs/testing/M2_COMPLETION_REPORT.md), [Lieferstand und Betriebsgrenzen](docs/STATUS.md).** Alle Demo-Unternehmen und Katalogpreise sind synthetisch.

## Lokale Demo starten

Voraussetzungen: laufendes Docker Desktop mit Linux-Containern und Compose sowie Python ab 3.12 für die einmalige Einrichtung.

```sh
python scripts/setup_local.py
docker compose up --build -d --wait --wait-timeout 240
```

Öffne [die lokale Anwendung](http://localhost:8080). Die Konten admin, analyst, viewer und mandant-b verwenden das einmalig erzeugte zufällige Demo-Passwort aus .local/demo-zugang.txt. Diese Datei und .env sind von Git und vom Image-Build ausgeschlossen. Vorhandene Konfiguration wird nicht überschrieben. Die Demo bindet ausschließlich 127.0.0.1:8080.

Anmelden → Organisation wählen → neues Szenario → synthetisches Beispiel laden oder eigene Testwerte eingeben → speichern → Bewertung starten. Die gleiche Profilversion lässt sich mit Wirtschafts- und Leistungsgewichtung vergleichen. Fehlende Pflichtwerte liefern eine offene Datenlage; jede historische Bewertung bewahrt ihren ursprünglichen Stand.

```sh
docker compose ps
docker compose stop
docker compose up -d --wait
```

stop erhält die Volumes. down --volumes entfernt Daten und gehört ausschließlich in ausdrücklich wegwerfbare Testumgebungen.

## Was Phase 1 enthält

- OIDC mit PKCE, serverseitige Sessions, CSRF, Organisationsrollen und PostgreSQL-RLS.
- Versionierte Profile, Arbeitslasten und Infrastruktur-Assets mit Konflikterkennung.
- Getrennte Service-, Deployment- und Hostingachsen für SaaS, PaaS, IaaS und Hybrid.
- Harte Bedingungen, normierte Gewichte, Dezimal-TCO, Sensitivität und unabhängige Ergebnisprüfung.
- Deutsche Formular-, Ergebnis-, Vergleichs-, Mitglieder- und Auditansichten.
- Optionale KI-Erklärung mit minimierten Daten, Zustimmung, Tagesbudget und sicherem Ausfall.

Ein KI-Schlüssel ist für den Kernablauf nicht erforderlich. Live-KI bleibt deaktiviert, bis Modell, Schlüssel, geprüfte Preisversion und Organisationsfreigabe explizit konfiguriert sind. Der Adapter verändert die fachliche Bewertung nicht. Näheres: [Erklärungsmodul](apps/api/src/platform_app/explanations/README.md).

## Datenwerkstatt

Anmelden → Musterwerk IT wählen → Datenwerkstatt → Datei oder freigegebene PostgreSQL-Quelle importieren. Unterstützt: CSV, JSON/JSONL, XLSX, Parquet und SQLite-Snapshots. Unter Qualität & Statistik Vollanalysen und wiederverwendbare Regeln starten; Berichte und Diagramme exportieren. Manuelle oder assistierte Bereinigungspläne erzeugen zuerst eine Vorschau; erst die Bestätigung legt eine neue Version an. Originalbytes und Herkunft bleiben erhalten. Für die synthetische PostgreSQL-Quelle einmalig `python scripts/setup_data_source_demo.py` ausführen. [Umfang, Grenzen und Bedienung](apps/api/src/platform_app/data/README.md).

Eine aktuelle Ansicht der synthetischen Demo: [Datenwerkstatt](docs/screenshots/m2-datenwerkstatt.png).

## Entwicklung und Prüfung

Python-Abhängigkeiten sind in requirements.lock und requirements-test.lock mit Hashes gesperrt, die vollständige Auflösung in uv.lock. Frontend: Node 24, pnpm 11.19.0.

```sh
python -m venv .venv
# Die virtuelle Umgebung aktivieren.
python -m pip install --require-hashes -r apps/api/requirements-test.lock
# PYTHONPATH=apps/api/src setzen oder lokal mit --no-deps -e apps/api installieren.
python -m pip install --no-deps -e apps/api
pnpm --dir apps/web install --frozen-lockfile
python -m pytest apps/api/tests -p no:cacheprovider -q
pnpm --dir apps/web run lint
pnpm --dir apps/web run build
pnpm --dir apps/web run test
docker compose --profile test run --build --rm tests
pnpm --dir apps/web exec playwright install chromium
python scripts/run_e2e.py
python scripts/check_runtime.py
python scripts/check_restore.py --full-stack
python scripts/install_trivy.py
python scripts/check_security.py
```

Die DB-Tests verwenden echte PostgreSQL-Rollen; ihre Session-Fixture ersetzt nur den vorgelagerten Login. Der Browserworkflow meldet sich tatsächlich über Keycloak an. Der vollständige Restore-Test erstellt ein getrenntes Compose-Projekt mit frischem Volume, prüft dort echten OIDC-Login und historische Bewertungen und entfernt nur dieses Testprojekt anschließend. Dafür wird der lokale Originalproxy kurz pausiert und automatisch wieder gestartet. --isolated-browser ergänzt bei Bedarf die isolierte Windows-Testinstallation. Dumps bleiben vertraulich unter .local/backups. Vollständige Prüfbefehle und Ergebnisse: [Prüfbericht](docs/testing/PHASE_1_REPORT.md).

Bei beschädigten Paketdateien in synchronisierten Windows-Verzeichnissen kann python scripts/run_e2e.py --isolated die gesperrten Browser-Testabhängigkeiten in einem temporären Verzeichnis installieren. Der Bericht nennt diesen Pfad. Die Anwendung wird dabei weiterhin über den echten laufenden Docker-Stack geprüft.

Der Frontend-Prüflauf lässt sich außerdem vollständig unter Linux ausführen:

```sh
docker build -f infra/proxy/Dockerfile --target test -t unternehmensplattform-web-tests:0.1.0 .
```

Der lokale Image-Scan hat zwei begründete befristete Keycloak-Einordnungen und noch einen hohen Keycloak-Herstellerbefund. Das API-Image ist im aktuellen Scan ohne Paketbefund. [Sicherheitsgrenzen](SECURITY.md) und [ADR 0003](docs/adr/0003-phase1-security-and-performance.md) sind Teil des Lieferstands.

## Orientierung

[Projektverfassung](docs/PROJECT_CHARTER.md) · [Phase-1-Auftrag](docs/PHASE_1_SPEC.md) · [Architektur](docs/ARCHITECTURE.md) · [Umsetzungsentscheidungen](docs/adr/0002-phase1-runtime-and-contracts.md) · [API](docs/API_CONTRACTS.md) · [Bedrohungsmodell](docs/security/THREAT_MODEL.md)

Quellmodule: [Identität](apps/api/src/platform_app/identity/README.md), [Erfassung](apps/api/src/platform_app/intake/README.md), [Fachrechnung](apps/api/src/platform_app/decisions/README.md), [Bewertungen](apps/api/src/platform_app/assessments/README.md), [Erklärungen](apps/api/src/platform_app/explanations/README.md). Jedes Modul erläutert Datenfluss, Entscheidungen, Ausfälle, Erweiterungen und Tests.

Die Datenwerkstatt ergänzt jetzt einen vollständigen begrenzten CSV-Ablauf: Import, Qualitätsprofil, manuelle Vorschau, bestätigte Version und sicherer Export. [Datenmodul](apps/api/src/platform_app/data/README.md) und [M2-Prüfbericht](docs/testing/M2_CSV_REPORT.md) erklären Umfang und Grenzen. Weitere Datenformate, Prozessanalyse, Cloud-Adapter, Security Lab, Agent Factory und Support bleiben spätere Ausbauschritte.


CSV-Dateien dürfen jetzt bis **1 GiB** groß sein. Uploads erfolgen abschnittsweise mit Fortschritt; die Verarbeitung nutzt einen begrenzten Hintergrundworker und Datenträger. Versionen und sichere Exporte bleiben vollständig, Originale unverändert. [Funktionsgrenzen und Bedienung](apps/api/src/platform_app/data/README.md) · [1-GiB-Prüfbericht](docs/testing/M2_LARGE_CSV_REPORT.md).


### Moderne Datenvisualisierung

In **Datenwerkstatt → Datensatz öffnen → Visuelle Analyse** stehen Balken, Ring, Datenqualität, Histogramm, Linie und Streudiagramm bereit. Mit **Diagramm-Beispiel laden · 180 Zeilen** lässt sich eine synthetische Vertriebsanalyse importieren. Interaktiver und statischer Modus, Spaltenwahl, Wertefilter, Zoom, Tabelle sowie PNG-/SVG-Export sind eingebunden.

Vollständige Profilwerte und begrenzte Diagrammauswahl werden ausdrücklich bezeichnet. Auch bei der gespeicherten 1-GiB-Testdatei liefert die neue Diagramm-API höchstens 300 Zeilen. [Umfang und Nachweise](docs/testing/M2_VISUALIZATION_REPORT.md).
