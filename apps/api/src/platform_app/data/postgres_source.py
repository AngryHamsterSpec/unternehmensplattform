"""Betreiberregistrierte PostgreSQL-Quellen. Keine benutzergesteuerten DSNs oder SQL-Texte."""

import json
import os
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread
from typing import Any
from uuid import UUID

import psycopg
from psycopg import sql
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from platform_app.data.engine import DataError


class SourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    id: str = Field(pattern=r"^[a-z0-9-]{1,80}$")
    name: str = Field(min_length=1, max_length=160)
    organizations: list[UUID] = Field(min_length=1, max_length=100)
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(min_length=1, max_length=100)
    user: str = Field(min_length=1, max_length=100)
    password: SecretStr
    sslmode: str = "verify-full"
    sslrootcert: str = ""
    tables: list[str] = Field(min_length=1, max_length=100)


def sources(org: UUID) -> list[SourceConfig]:
    filename = os.environ.get("DATA_SOURCES_FILE")
    if not filename:
        return []
    path = Path(filename)
    try:
        if path.stat().st_size > 262144:
            raise ValueError()
        configs = [SourceConfig.model_validate(c) for c in json.loads(path.read_text("utf-8-sig"))]
        if len(configs) > 50 or len({c.id for c in configs}) != len(configs):
            raise ValueError()
        for c in configs:
            local_demo = (
                os.environ.get("ENVIRONMENT") in {"demo", "test", "development"}
                and c.host == "postgres"
                and c.database == "source_demo"
                and c.user == "source_reader"
            )
            if c.sslmode != "verify-full" and not (local_demo and c.sslmode == "disable"):
                raise ValueError()
            if c.database in {"platform", "keycloak", "postgres", "template0", "template1"}:
                raise ValueError()
            if any(
                len(t.split(".")) != 2
                or any(not n or len(n) > 100 or any(ord(ch) < 32 for ch in n) for n in t.split("."))
                for t in c.tables
            ):
                raise ValueError()
        return [c for c in configs if org in c.organizations]
    except (OSError, ValueError, TypeError):
        raise DataError(
            "Die registrierten Datenquellen sind nicht gültig konfiguriert. Bitte die Administration informieren."
        ) from None


def source_for(org: UUID, source_id: str, table: str) -> SourceConfig:
    config = next((c for c in sources(org) if c.id == source_id and table in c.tables), None)
    if config is None:
        raise DataError(
            "Diese Datenquelle oder Tabelle ist für die Organisation nicht freigegeben."
        )
    return config


@contextmanager
def keep_lease(
    db: psycopg.Connection[Any], heartbeat: Callable[[int, str], None]
) -> Generator[list[int], None, None]:
    stopped = Event()
    interrupted: list[Exception] = []
    received = [0]

    def monitor() -> None:
        while not stopped.wait(2):
            if not interrupted:
                try:
                    heartbeat(
                        min(70, 5 + int(65 * received[0] / 1073741824)),
                        "Konsistenter Datenbanksnapshot wird gelesen",
                    )
                except Exception as error:
                    interrupted.append(error)
            if interrupted:
                try:
                    db.cancel_safe(timeout=5)
                except psycopg.Error:
                    pass

    watcher = Thread(target=monitor, name="source-lease", daemon=True)
    watcher.start()
    try:
        yield received
    finally:
        stopped.set()
        watcher.join()
        if interrupted:
            raise interrupted[0]


def snapshot(
    config: SourceConfig, table: str, path: Path, heartbeat: Callable[[int, str], None]
) -> dict[str, object]:
    if table not in config.tables:
        raise DataError("Die Tabelle ist nicht freigegeben.")
    schema, name = table.split(".")
    try:
        with psycopg.connect(
            host=config.host,
            port=config.port,
            dbname=config.database,
            user=config.user,
            password=config.password.get_secret_value(),
            sslmode=config.sslmode,
            sslrootcert=config.sslrootcert,
            connect_timeout=5,
            keepalives_idle=10,
            keepalives_interval=2,
            keepalives_count=3,
            tcp_user_timeout=10000,
            options="-c default_transaction_read_only=on -c statement_timeout=900000 -c lock_timeout=5000 -c idle_in_transaction_session_timeout=30000 -c timezone=UTC -c datestyle=ISO,YMD",
        ) as db:
            db.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
            db.read_only = True
            with db.cursor() as cur, keep_lease(db, heartbeat) as received:
                cur.execute(
                    "SELECT rolsuper, rolbypassrls, rolcreaterole FROM pg_catalog.pg_roles WHERE rolname=current_user"
                )
                if cur.fetchone() != (False, False, False):
                    raise DataError(
                        "Die Datenquelle benötigt eine Rolle ohne Superuser-, RLS-Bypass- oder Rollenverwaltungsrechte."
                    )
                cur.execute(
                    sql.SQL("LOCK TABLE {} IN ACCESS SHARE MODE").format(
                        sql.Identifier(schema, name)
                    )
                )
                cur.execute(
                    "SELECT c.relkind FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relname=%s",
                    (schema, name),
                )
                relation = cur.fetchone()
                if relation is None or relation[0] not in {"r", "p"}:
                    raise DataError(
                        "Die Quelle benötigt eine freigegebene gewöhnliche Tabelle; Views und Fremdtabellen sind nicht zugelassen."
                    )
                cur.execute(
                    "SELECT a.attname, pg_catalog.format_type(a.atttypid,a.atttypmod), t.typnamespace='pg_catalog'::regnamespace FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_type t ON t.oid=a.atttypid WHERE a.attrelid=%s::regclass AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum",
                    (sql.Identifier(schema, name).as_string(db),),
                )
                columns = cur.fetchall()
                if not 1 <= len(columns) <= 256 or any(
                    not builtin or len(column) > 100 for column, _, builtin in columns
                ):
                    raise DataError(
                        "Die Tabelle benötigt 1–256 Spalten mit PostgreSQL-Standardtypen und Namen bis 100 Zeichen."
                    )
                # COPY liefert ganze Zeilen. Vorab im selben Snapshot prüfen, damit eine
                # einzelne riesige Quellzelle den Worker nicht vor seiner Byteprüfung füllt.
                sizes = [
                    sql.SQL("coalesce(octet_length({}::text),0)::bigint").format(
                        sql.Identifier(c[0])
                    )
                    for c in columns
                ]
                oversized = sql.SQL("SELECT EXISTS(SELECT 1 FROM {} WHERE ({}) > 4194000)").format(
                    sql.Identifier(schema, name),
                    sql.SQL(" + ").join(sql.SQL("({} * 2 + 3)").format(s) for s in sizes),
                )
                cur.execute(oversized)
                oversized_row = cur.fetchone()
                if oversized_row and oversized_row[0]:
                    raise DataError(
                        "Eine Quellzeile ist für den begrenzten CSV-Snapshot zu groß (maximal 4 MiB einschließlich Maskierung)."
                    )
                # COPY respektiert RLS-Leserechte der Quellenrolle; keine Superuser-Zugangsdaten verwenden.
                query = sql.SQL(
                    "COPY (SELECT {} FROM {}) TO STDOUT WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')"
                ).format(
                    sql.SQL(",").join(sql.Identifier(c[0]) for c in columns),
                    sql.Identifier(schema, name),
                )
                total = 0
                with cur.copy(query) as copy, path.open("wb") as output:
                    for block in copy:
                        total += len(block)
                        received[0] = total
                        if total > 1073741824:
                            raise DataError(
                                "Der Datenbanksnapshot überschreitet 1 GiB. Bitte eine kleinere Quelltabelle bereitstellen."
                            )
                        output.write(block)
        return {
            "source_id": config.id,
            "table": table,
            "captured_at": datetime.now(UTC).isoformat(),
            "isolation": "repeatable read, read only",
            "columns": [{"name": c[0], "database_type": c[1]} for c in columns],
            "bytes": total,
        }
    except psycopg.Error:
        raise DataError(
            "Die PostgreSQL-Quelle ist nicht erreichbar, wurde verändert oder die Leserechte/Transportprüfung sind fehlgeschlagen. Zugang und Tabellenfreigabe prüfen."
        ) from None
