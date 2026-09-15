"""Prüft Neustart und Backup beider Datenbanken in einem eigenen Compose-Projekt.

Schreibt vertrauliche Dumps nur nach .local/backups. Löscht ausschließlich das
in diesem Aufruf neu erzeugte Restore-Projekt samt dessen eigenen Volumes.
"""

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "unternehmensplattform"
TABLES = {
    "platform": [
        "organizations",
        "users",
        "organization_memberships",
        "membership_roles",
        "company_profiles",
        "company_profile_versions",
        "workloads",
        "infrastructure_assets",
        "cost_catalog_versions",
        "assessments",
        "architecture_candidates",
        "cost_estimate_lines",
        "agent_runs",
        "audit_events",
        "explanation_requests",
        "provider_budget_days",
        "datasets",
        "data_blobs",
        "data_objects",
        "data_chunks",
        "data_jobs",
        "data_versions",
        "data_tasks",
        "data_rule_sets",
    ],
    "keycloak": ["realm", "user_entity", "client"],
}


def command(project, *args, input_data=None, input_path=None, timeout=180, output=None):
    with input_path.open("rb") if input_path is not None else nullcontext(None) as source:
        result = subprocess.run(
            ["docker", "compose", "-p", project, *args],
            cwd=ROOT,
            input=input_data,
            stdin=source,
            stdout=output if output is not None else subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    if result.returncode:
        # pg_restore-Fehler können COPY-Werte enthalten: keine Rohdaten ausgeben.
        raise RuntimeError("Docker-Betriebsprüfung fehlgeschlagen: " + args[0])
    return result.stdout


def file_hash(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def sql(project, database, statement):
    return (
        command(
            project,
            "exec",
            "-T",
            "postgres",
            "psql",
            "-XAt",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "postgres",
            "-d",
            database,
            "-c",
            statement,
        )
        .decode()
        .strip()
    )


def snapshot(project):
    result = {}
    for database, tables in TABLES.items():
        result[database] = {}
        for table in tables:  # Feste interne Bezeichner, keine Nutzereingaben.
            value = sql(
                project,
                database,
                "SET timezone='UTC'; SELECT json_build_object('count', count(*), 'digest', "
                "md5(COALESCE(string_agg(md5(row_to_json(t)::text), '' ORDER BY md5(row_to_json(t)::text)),''))) "
                f"FROM {table} t;",
            )
            result[database][table] = json.loads(value.splitlines()[-1])
    return result


def rotate_test_secret(project):
    # Ausschließlich die frisch wiederhergestellte, anschließend entfernte
    # Testinstanz. Das Passwort der laufenden Demo bleibt unverändert.
    config = json.loads(command(project, "config", "--format", "json"))
    old = config["services"]["postgres"]["environment"]["PLATFORM_APP_PASSWORD"]
    fresh = secrets.token_hex(32)
    sql(project, "platform", "ALTER ROLE platform_app PASSWORD '" + fresh + "'")

    def connect(password):
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-p",
                project,
                "exec",
                "-T",
                "-e",
                "PGPASSWORD=" + password,
                "postgres",
                "psql",
                "-h",
                "postgres",
                "-U",
                "platform_app",
                "-d",
                "platform",
                "-XAt",
                "-c",
                "SELECT 1",
            ],
            cwd=ROOT,
            capture_output=True,
            timeout=20,
            check=False,
        )
        return result.returncode, result.stdout.strip()

    old_status, _ = connect(old)
    new_status, output = connect(fresh)
    if old_status == 0 or new_status != 0 or output != b"1":
        raise RuntimeError("Test-Secretrotation oder Widerruf des alten Werts fehlgeschlagen.")
    return {"old_secret_rejected": True, "new_secret_accepted": True}


def check_restored_browser(project, isolated):
    sample = json.loads(
        sql(
            project,
            "platform",
            "SELECT json_build_object('id', id, 'hash', result_hash) FROM assessments "
            "WHERE organization_id='10000000-0000-4000-8000-000000000001' AND status='VERIFIED' "
            "ORDER BY created_at, id LIMIT 1;",
        )
    )
    data_sample = json.loads(
        sql(
            project,
            "platform",
            "SELECT json_build_object('id', dataset_id, 'hash', content_hash, 'version', version_no) "
            "FROM data_versions WHERE organization_id='10000000-0000-4000-8000-000000000001' "
            "AND version_no=2 ORDER BY created_at, id LIMIT 1;",
        )
    )
    analysis_sample = json.loads(
        sql(
            project,
            "platform",
            "SELECT json_build_object('id', id, 'hash', result_hash, "
            "'dataset_id', dataset_id, 'version', version_no) FROM data_tasks "
            "WHERE organization_id='10000000-0000-4000-8000-000000000001' "
            "AND kind='ANALYSIS' AND status='SUCCEEDED' ORDER BY created_at DESC, id LIMIT 1;",
        )
    )
    # Ohne Migrations-/Seedlauf: Die Anmeldung muss die restaurierten Identitäten
    # und der Ergebnisabruf den unveränderten historischen Snapshot verwenden.
    command(
        project,
        "up",
        "-d",
        "--no-deps",
        "--wait",
        "--wait-timeout",
        "240",
        "keycloak",
        "api",
        "web",
        "data-worker",
        "intelligence-worker",
        timeout=300,
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_e2e.py"),
            "--grep",
            "Wiederhergestellte",
            *(["--isolated"] if isolated else []),
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "E2E_BASE_URL": "http://localhost:8080",
            "RESTORE_ASSESSMENT_ID": sample["id"],
            "RESTORE_ASSESSMENT_HASH": sample["hash"],
            "RESTORE_DATASET_ID": data_sample["id"],
            "RESTORE_DATA_HASH": data_sample["hash"],
            "RESTORE_ANALYSIS_ID": analysis_sample["id"],
            "RESTORE_ANALYSIS_HASH": analysis_sample["hash"],
            "RESTORE_ANALYSIS_DATASET_ID": analysis_sample["dataset_id"],
            "RESTORE_ANALYSIS_VERSION": str(analysis_sample["version"]),
        },
        capture_output=True,
        timeout=600,
        check=False,
    )
    # Browserfehler können eingegebene Werte enthalten: nur die Zahl erfolgreicher
    # Tests übernehmen, niemals rohe Browserlogs als Betriebsprotokoll ausgeben.
    match = re.search(r"(\d+) passed", result.stdout.decode(errors="replace"))
    if result.returncode or match is None or int(match[1]) != 1:
        raise RuntimeError("Browserabnahme gegen den restaurierten Stack fehlgeschlagen.")
    return {
        "passed": 1,
        "restored_dataset_id": data_sample["id"],
        "restored_dataset_hash": data_sample["hash"],
        "restored_analysis_id": analysis_sample["id"],
        "restored_analysis_hash": analysis_sample["hash"],
        "restored_analysis_dataset_id": analysis_sample["dataset_id"],
        "restored_analysis_version": analysis_sample["version"],
        "real_oidc": True,
        "restored_assessment_id": sample["id"],
        "restored_result_hash": sample["hash"],
        "migration_or_reseed": False,
    }


def cleanup(project, source_paused):
    # Auch bei einem Fehler während der Testbereinigung den Originalproxy starten.
    try:
        command(project, "down", "--volumes", "--remove-orphans")
    finally:
        if source_paused:
            command(
                SOURCE,
                "up",
                "-d",
                "--no-deps",
                "--wait",
                "--wait-timeout",
                "120",
                "web",
                timeout=150,
            )


@contextmanager
def paused_worker():
    try:
        command(SOURCE, "stop", "data-worker", "intelligence-worker")
        yield
    finally:
        command(SOURCE, "up", "-d", "--no-deps", "--wait", "data-worker", "intelligence-worker")


def main():
    # Scopeprüfung vor jeder Betriebsänderung; die innere Prüfung bleibt bestehen.
    config = json.loads(command(SOURCE, "config", "--format", "json"))
    environment = config["services"]["api"]["environment"]
    if (
        environment.get("ENVIRONMENT") not in {"demo", "test"}
        or environment.get("PUBLIC_ORIGIN") != "http://localhost:8080"
    ):
        raise RuntimeError("Restore-Übung ist nur für die lokale synthetische Demo freigegeben.")
    with paused_worker():
        run_restore()


def run_restore():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full-stack",
        action="store_true",
        help="Zusätzlich echten Login und Browserabläufe gegen den restaurierten Stack prüfen.",
    )
    parser.add_argument(
        "--isolated-browser",
        action="store_true",
        help="Browserabhängigkeiten außerhalb synchronisierter Verzeichnisse installieren.",
    )
    args = parser.parse_args()
    config = json.loads(command(SOURCE, "config", "--format", "json"))
    env = config["services"]["api"]["environment"]
    if (
        env.get("ENVIRONMENT") not in {"demo", "test"}
        or env.get("PUBLIC_ORIGIN") != "http://localhost:8080"
    ):
        raise RuntimeError("Restore-Übung ist nur für die lokale synthetische Demo freigegeben.")
    project = "phase1-restore-" + uuid4().hex
    assert project.startswith("phase1-restore-") and project != SOURCE
    directory = ROOT / ".local/backups" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory.mkdir(parents=True, exist_ok=False)
    os.chmod(directory, 0o700)
    print(
        "Restore-Prüfung: Datenbanken sichern und fachliche Stände vergleichen.",
        flush=True,
    )
    before = snapshot(SOURCE)
    if not before["platform"]["assessments"]["count"]:
        raise RuntimeError(
            "Zuerst DB-Integration und Browserworkflow mit gespeicherter Bewertung ausführen."
        )
    dumps = {}
    for database in TABLES:
        path = directory / (database + ".pgdump")
        with path.open("xb") as output:
            os.chmod(path, 0o600)
            command(
                SOURCE,
                "exec",
                "-T",
                "postgres",
                "pg_dump",
                "-U",
                "postgres",
                "-Fc",
                database,
                output=output,
            )
        dumps[database] = path
    command(SOURCE, "restart", "api", "web")
    command(SOURCE, "up", "-d", "--wait", "--wait-timeout", "180", "api", "web", timeout=240)
    after = snapshot(SOURCE)
    if before["platform"] != after["platform"]:
        raise RuntimeError("Fachliche Daten unterscheiden sich nach Neustart.")
    source_paused = False
    report = {}
    try:
        command(
            project,
            "up",
            "-d",
            "--wait",
            "--wait-timeout",
            "180",
            "postgres",
            timeout=240,
        )
        for database, path in dumps.items():
            command(
                project,
                "exec",
                "-T",
                "postgres",
                "pg_restore",
                "-U",
                "postgres",
                "--clean",
                "--if-exists",
                "--exit-on-error",
                "-d",
                database,
                input_path=path,
            )
        if before != snapshot(project):
            raise RuntimeError("Restore-Prüfsummen oder Datensatzanzahlen unterscheiden sich.")
        protected = sql(
            project,
            "platform",
            "SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace "
            "AND relkind='r' AND relname!='alembic_version' AND (NOT relrowsecurity OR NOT relforcerowsecurity);",
        )
        if protected != "0":
            raise RuntimeError("RLS fehlt nach Restore.")
        invisible = sql(
            project,
            "platform",
            "SET ROLE platform_app; SELECT count(*) FROM company_profiles;",
        )
        if invisible.splitlines()[-1] != "0":
            raise RuntimeError("Daten sind ohne Mandantenkontext sichtbar.")
        browser = None
        if args.full_stack:
            print(
                "Restore-Prüfung: Originalproxy kurz pausieren; echten restaurierten Stack prüfen.",
                flush=True,
            )
            source_paused = True
            command(SOURCE, "stop", "web")
            browser = check_restored_browser(project, args.isolated_browser)
        report = {
            "checked_at": datetime.now(UTC).isoformat(),
            "status": "PASSED",
            "fresh_postgres_volume": True,
            "api_web_restart": True,
            "database_snapshots": before,
            "rls_restored": True,
            "restored_browser": browser,
            "test_secret_rotation": rotate_test_secret(project),
            "dump_sha256": {name: file_hash(path) for name, path in dumps.items()},
            "scope": "Lokaler Demo-Stack; voller OIDC-/Browsernachweis nur bei restored_browser.",
        }
    finally:
        cleanup(project, source_paused)
    report["original_proxy_restored"] = True
    (directory / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        "Neustart, frisches Restore-Volume, Prüfsummen und RLS erfolgreich. Bericht: "
        + str(directory / "result.json")
    )


if __name__ == "__main__":
    main()
