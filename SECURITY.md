# Sicherheit

Phase 1 ist ein lokal begrenzter Demonstrator mit echten Rollen, OIDC, CSRF, PostgreSQL-RLS und unveränderlichen Fachständen. Tatsächlich ausgeführte Prüfungen und Grenzen stehen im [Prüfbericht](docs/testing/PHASE_1_REPORT.md). Produktivdaten und öffentlicher Betrieb sind nicht freigegeben.

Die Anwendung bindet nur 127.0.0.1:8080. Datenbank und Identitätsanbieter veröffentlichen keine eigenen Ports. Anwendung und Proxy laufen ohne root, ohne schreibbares Root-Dateisystem und ohne zusätzliche Linux-Capabilities. PostgreSQL senkt nach der Initialisierung seine Benutzerrechte ab.

## Prüfungen

```sh
python scripts/install_trivy.py
python -m unittest discover -s scripts -p test_security_policy.py
python scripts/check_security.py
python scripts/check_runtime.py
python scripts/check_restore.py --full-stack
```

Der Installer prüft das feste offizielle Trivy-Release gegen dessen SHA-256-Datei. Der Scan untersucht ausschließlich Projektquellen und die vier expliziten Demo-Images über lokale Archive. Eine synthetische Secret-/Schwachstellen-Fixture muss erkannt werden. Das spätere Security Lab ist damit nicht implementiert.

Rohberichte verbleiben unter .local/security. Das Gate unterscheidet echte offene Befunde, exakt begründete befristete Einordnungen und Meldungen ohne verfügbaren Herstellerfix. Details und Verantwortlichkeit: [ADR 0003](docs/adr/0003-phase1-security-and-performance.md). Die API-Basis ist nach [ADR 0004](docs/adr/0004-api-base-and-complete-restore.md) auf Alpine umgestellt; im aktuellen API-Scan gibt es keine Paket-Schwachstelle. Eine hohe Java-Runtime-Meldung im Keycloak-Image bleibt offen. Keine pauschalen CVE-Ausnahmen und keine produktive Sicherheitszusage.

## Vertraulichkeit und Meldungen

.env, Demo-Passwort, generierter OIDC-Realm und Datenbanksicherungen bleiben lokal und ausgeschlossen von Git und Build. Backups können Authentifizierungsdaten enthalten und müssen entsprechend geschützt werden. Logs enthalten keine Tokens, Rohprompts oder Datenbankparameter.

Ein privater Meldekanal für eine Veröffentlichung ist noch einzurichten. In dieser privaten Projektzusammenarbeit kann der Projektverantwortliche informiert werden; Geheimnisse gehören nicht in öffentliche Issues.

[Bedrohungsmodell](docs/security/THREAT_MODEL.md) · [Vertrauensgrenzen](docs/security/TRUST_BOUNDARIES.md) · [Datenklassifikation](docs/security/DATA_CLASSIFICATION.md) · [Vorfallbehandlung](docs/security/INCIDENT_RESPONSE.md)
