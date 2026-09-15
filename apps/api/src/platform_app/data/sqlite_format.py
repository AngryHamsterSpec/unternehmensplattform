"""Unveränderlicher SQLite-Snapshot: genau eine gewöhnliche Tabelle, nur lesend."""

import math
import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from platform_app.data.engine import DataError

MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_SCHEMA_OBJECTS = 1000


def identifier(value: str) -> str:
    """Nur Namen aus dem geprüften Schema; keine SQL-Fragmente aus Eingaben."""
    return '"' + value.replace('"', '""') + '"'


def cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str | int):
        return str(value)
    if isinstance(value, float) and math.isfinite(value):
        return str(value)
    raise DataError(
        "SQLite enthält binäre Werte oder unendliche Zahlen. Bitte die Tabelle vor dem Import aufbereiten."
    )


@dataclass
class SQLiteSource:
    path: Path
    requested_table: str | None
    heartbeat: Callable[[], None]
    table_name: str | None = None

    def rows(self) -> Iterator[list[str]]:
        connection: sqlite3.Connection | None = None
        interrupted: Exception | None = None

        def progress() -> int:
            nonlocal interrupted
            try:
                self.heartbeat()
                return 0
            except Exception as error:
                interrupted = error
                return 1

        try:
            with self.path.open("rb") as source:
                header = source.read(100)
            if len(header) != 100 or header[:16] != b"SQLite format 3\x00":
                raise DataError("Die Datei ist kein unverschlüsselter SQLite-3-Snapshot.")
            if header[18:20] != b"\x01\x01":
                raise DataError(
                    "Der SQLite-Snapshot verwendet WAL oder ein unbekanntes Journalformat. Bitte eine vollständige Sicherung im DELETE-Journalmodus exportieren; die einzelne Datei kann sonst unvollständig sein."
                )
            self.heartbeat()
            connection = sqlite3.connect(
                self.path.resolve().as_uri() + "?mode=ro&immutable=1",
                uri=True,
                timeout=0,
                cached_statements=0,
            )
            connection.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
            connection.setconfig(sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False)
            connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_RECORD_BYTES)
            connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 65536)
            connection.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 256)
            connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
            connection.setlimit(sqlite3.SQLITE_LIMIT_VDBE_OP, 25000)
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA mmap_size=0")
            connection.execute("PRAGMA cache_size=-4096")
            connection.execute("PRAGMA temp_store=FILE")
            connection.set_progress_handler(progress, 1000)
            objects = connection.execute("PRAGMA main.table_list").fetchmany(MAX_SCHEMA_OBJECTS + 1)
            if len(objects) > MAX_SCHEMA_OBJECTS:
                raise DataError(
                    "SQLite enthält mehr als 1.000 Schemaobjekte. Bitte eine Tabelle separat exportieren."
                )
            tables = {
                row[1]: row
                for row in objects
                if row[0] == "main" and row[2] == "table" and not row[1].startswith("sqlite_")
            }
            if not tables:
                raise DataError(
                    "SQLite enthält keine gewöhnliche Datentabelle. Views und virtuelle Tabellen bitte vorab als Tabelle exportieren."
                )
            selected = self.requested_table
            if selected is None and len(tables) == 1:
                selected = next(iter(tables))
            if selected not in tables:
                names = ", ".join(sorted(tables)[:8])[:600]
                raise DataError(
                    "Bitte einen vorhandenen SQLite-Tabellennamen angeben und den Import aus der gespeicherten Datei wiederholen. Tabellen (Auswahl): "
                    + names
                )
            assert selected is not None
            if not 1 <= len(selected) <= 100 or any(ord(c) < 32 for c in selected):
                raise DataError(
                    "Der SQLite-Tabellenname muss 1 bis 100 Zeichen ohne Steuerzeichen enthalten."
                )
            metadata = connection.execute(
                "PRAGMA main.table_xinfo(" + identifier(selected) + ")"
            ).fetchall()
            if not 1 <= len(metadata) <= 256:
                raise DataError("Die SQLite-Tabelle benötigt 1 bis 256 Spalten.")
            if any(column[6] != 0 for column in metadata):
                raise DataError(
                    "Berechnete oder versteckte SQLite-Spalten bitte vorab als gewöhnliche Werte exportieren."
                )
            columns = [column[1] for column in metadata]
            rowid = next(
                (
                    name
                    for name in ("rowid", "_rowid_", "oid")
                    if name not in {c.casefold() for c in columns}
                ),
                None,
            )
            if not tables[selected][4] and rowid:
                order = identifier(rowid)
            elif tables[selected][4]:
                order = ",".join(
                    identifier(c[1]) for c in sorted(metadata, key=lambda c: c[5]) if c[5]
                )
            else:
                raise DataError(
                    "Alle SQLite-Zeilenkennungen sind durch Spalten verdeckt. Bitte die Tabelle als CSV exportieren."
                )

            def authorize(
                action: int,
                name: str | None,
                column: str | None,
                database: str | None,
                origin: str | None,
            ) -> int:
                if action == sqlite3.SQLITE_SELECT:
                    return sqlite3.SQLITE_OK
                if (
                    action == sqlite3.SQLITE_READ
                    and name == selected
                    and database == "main"
                    and origin is None
                ):
                    return sqlite3.SQLITE_OK
                return sqlite3.SQLITE_DENY

            connection.set_authorizer(authorize)
            query = (
                "SELECT "
                + ",".join(identifier(c) for c in columns)
                + " FROM main."
                + identifier(selected)
                + " ORDER BY "
                + order
            )
            cursor = connection.execute(query)
            self.table_name = selected
            yield columns
            for number, row in enumerate(cursor, 1):
                if number % 1000 == 0:
                    self.heartbeat()
                yield [cell(value) for value in row]
        except (sqlite3.Error, OSError, UnicodeError, MemoryError):
            if interrupted is not None:
                raise interrupted from None
            raise DataError(
                "Der SQLite-Snapshot ist beschädigt oder überschreitet die Struktur-/Datensatzgrenzen. Bitte die gewünschte Tabelle als vollständigen SQLite-Snapshot oder CSV neu exportieren."
            ) from None
        finally:
            if connection is not None:
                connection.close()
