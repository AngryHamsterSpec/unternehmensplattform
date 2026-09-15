"""Registriert eine isolierte, synthetische PostgreSQL-Lesequelle für die lokale Demo."""

import json
import os
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def psql(script: str, database: str = "postgres") -> str:
    result = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-X",
            "-qAt",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "postgres",
            "-d",
            database,
        ],
        cwd=ROOT,
        input=script,
        text=True,
        encoding="utf8",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        # PostgreSQL kann fehlgeschlagene SQL-Texte einschließlich Zugangsdaten ausgeben.
        raise SystemExit(
            "Demoquelle konnte nicht eingerichtet werden. PostgreSQL und lokale Konfiguration prüfen; keine Zugangsdaten ausgegeben."
        )
    return result.stdout.strip()


def main() -> None:
    dotenv = dict(
        line.split("=", 1)
        for line in (ROOT / ".env").read_text("utf8").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    if os.environ.get("ENVIRONMENT", dotenv.get("ENVIRONMENT", "demo")) not in {
        "demo",
        "development",
        "test",
    }:
        raise SystemExit(
            "Diese Einrichtung ist ausschließlich für die lokale synthetische Demo bestimmt."
        )
    registry = ROOT / ".local/data-sources.json"
    configs = json.loads(registry.read_text("utf-8-sig")) if registry.exists() else []
    existing = next((c for c in configs if c["id"] == "synthetischer-vertrieb"), None)
    if existing:
        print("Demoquelle bereits registriert; Konfiguration und Daten bleiben unverändert.")
        return
    if psql(
        "SELECT 1 FROM pg_roles WHERE rolname='source_reader' UNION ALL SELECT 1 FROM pg_database WHERE datname='source_demo';"
    ):
        raise SystemExit(
            "Demo-Rolle oder Datenbank existiert bereits ohne Registry-Eintrag. Keine vorhandenen Daten oder Zugangsdaten werden überschrieben."
        )
    password = secrets.token_hex(32)
    psql(
        f"CREATE ROLE source_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD '{password}';\nCREATE DATABASE source_demo;\nREVOKE ALL ON DATABASE source_demo FROM PUBLIC;\nGRANT CONNECT ON DATABASE source_demo TO source_reader;\nALTER ROLE source_reader SET default_transaction_read_only=on;"
    )
    psql(
        """
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA demo;
CREATE TABLE demo.sales (kunde text, team text, umsatz numeric(16,2), kosten numeric(16,2), datum date, sichtbar boolean);
INSERT INTO demo.sales VALUES
(' Anna ', 'Nord', 100, 50, '2026-01-01', true),
(' Anna ', 'Nord', 100, 50, '2026-01-01', true),
('Ben', 'Süd', 200, 100, '2026-02-01', true),
('Clara', 'Nord', 9000, 4500, '2026-02-02', true),
('RLS-ausgeschlossen', 'Intern', 100000, 999, '2026-03-01', false);
ALTER TABLE demo.sales ENABLE ROW LEVEL SECURITY;
CREATE POLICY source_demo_visible ON demo.sales FOR SELECT TO source_reader USING (sichtbar);
GRANT USAGE ON SCHEMA demo TO source_reader;
GRANT SELECT ON demo.sales TO source_reader;
""",
        "source_demo",
    )
    configs.append(
        {
            "id": "synthetischer-vertrieb",
            "name": "Synthetischer Vertrieb",
            "organizations": [
                "10000000-0000-4000-8000-000000000001",
                "10000000-0000-4000-8000-000000000002",
            ],
            "host": "postgres",
            "database": "source_demo",
            "user": "source_reader",
            "password": password,
            "sslmode": "disable",
            "tables": ["demo.sales"],
        }
    )
    registry.write_text(json.dumps(configs, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(
        "Synthetische Demoquelle registriert: demo.sales, lesende Rolle und aktive Quellen-RLS. Bestehende Plattformdaten unverändert."
    )


if __name__ == "__main__":
    main()
