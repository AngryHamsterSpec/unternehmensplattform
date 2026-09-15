"""SQLite-Snapshots: fachliche Werte, Quellschutz, Formatgrenzen und Abbruch."""

import json
import sqlite3
from contextlib import closing

import pytest
from platform_app.data.engine import DataError
from platform_app.data.schemas import ImportOptions, Step, UploadInput
from platform_app.data.sqlite_format import SQLiteSource
from platform_app.data.stream_engine import build
from pydantic import ValidationError


def database(tmp_path, sql='CREATE TABLE "Daten" ("Name" TEXT, "Wert")', values=None):
    path = tmp_path / "source.sqlite"
    with closing(sqlite3.connect(path)) as db:
        db.executescript(sql)
        if values is not None:
            db.executemany('INSERT INTO "Daten" VALUES (?, ?)', values)
        db.commit()
    return path


def read(path, table=None, heartbeat=lambda: None):
    return list(SQLiteSource(path, table, heartbeat).rows())


def test_snapshot_precision_profile_transform_export_and_original(tmp_path):
    source = database(tmp_path, values=[(" Anna ", 9007199254740993), ("=1+1", None), ("Öl", 1.25)])
    original = source.read_bytes()
    normalized, exported, profile, protected = build(
        source,
        tmp_path,
        ";",
        False,
        [Step(operation="trim", column="Name")],
        lambda *a: None,
        csv_options=ImportOptions(table_name="Daten"),
        source_format="sqlite",
    )
    assert profile.source_table == "Daten" and profile.source_format == "sqlite"
    assert profile.rows == 3 and profile.missing_cells == 1
    rows = [json.loads(line) for line in normalized.read_text(encoding="utf8").splitlines()]
    assert rows[1:] == [["Anna", "9007199254740993"], ["=1+1", ""], ["Öl", "1.25"]]
    assert protected == 1 and '"\'=1+1"' in exported.read_text(encoding="utf-8-sig")
    assert source.read_bytes() == original
    assert not source.with_name(source.name + "-journal").exists()


def test_exact_quoted_table_name_and_without_rowid_order(tmp_path):
    source = database(
        tmp_path,
        'CREATE TABLE "Vertrieb "" Süd" ("Key" TEXT PRIMARY KEY, "select" TEXT) WITHOUT ROWID; INSERT INTO "Vertrieb "" Süd" VALUES (\'b\', \'zwei\'), (\'a\', \'eins\');',
    )
    assert read(source, 'Vertrieb " Süd') == [["Key", "select"], ["a", "eins"], ["b", "zwei"]]


@pytest.mark.parametrize("selection", [None, "Fehlt", 'Daten"; DROP TABLE Daten; --'])
def test_multiple_tables_require_exact_selection_without_changing_source(tmp_path, selection):
    source = database(tmp_path, "CREATE TABLE Daten (Name); CREATE TABLE Zweite (Wert)")
    original = source.read_bytes()
    with pytest.raises(DataError, match="Tabellennamen"):
        read(source, selection)
    assert source.read_bytes() == original
    assert read(source, "Daten") == [["Name"]]


def test_views_and_triggers_are_never_executed(tmp_path):
    source = database(
        tmp_path,
        "CREATE TABLE Daten(Name); CREATE VIEW Fremd AS SELECT load_extension('not-allowed'); CREATE TRIGGER write_trigger AFTER INSERT ON Daten BEGIN DELETE FROM Daten; END;",
    )
    assert read(source) == [["Name"]]
    with pytest.raises(DataError, match="Tabellennamen"):
        read(source, "Fremd")


@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE Daten(Name TEXT, Wert AS (length(Name)))",
        "CREATE TABLE Daten(Name TEXT, Wert AS (length(Name)) STORED)",
    ],
)
def test_generated_columns_need_materialized_values(tmp_path, sql):
    with pytest.raises(DataError, match="Berechnete"):
        read(database(tmp_path, sql))


def test_virtual_tables_are_not_sources(tmp_path):
    source = database(tmp_path, "CREATE VIRTUAL TABLE Suche USING fts5(Inhalt)")
    with pytest.raises(DataError, match="gewöhnliche Datentabelle"):
        read(source)


@pytest.mark.parametrize("value", [b"binary", float("inf"), float("-inf")])
def test_non_tabular_values_fail_with_data_poor_message(tmp_path, value):
    source = database(tmp_path, values=[("private-value", value)])
    with pytest.raises(DataError, match="binäre Werte") as error:
        read(source)
    assert "private-value" not in str(error.value)


def test_oversized_record_rejected_before_python_materialization(tmp_path):
    source = database(tmp_path, values=[("x" * (4 * 1024 * 1024 + 1), 1)])
    with pytest.raises(DataError, match="Datensatzgrenzen"):
        read(source)


@pytest.mark.parametrize("mode", ["fake", "truncated", "wal", "corrupt"])
def test_bad_or_incomplete_snapshots_are_actionable(tmp_path, mode):
    source = database(tmp_path, values=[("Anna", 1)])
    data = source.read_bytes()
    if mode == "fake":
        data = b"Name;Wert\nAnna;1"
    elif mode == "truncated":
        data = data[:100]
    elif mode == "wal":
        data = data[:18] + b"\x02\x02" + data[20:]
    else:
        data = data[:100] + b"\xff" * (len(data) - 100)
    source.write_bytes(data)
    with pytest.raises(DataError, match="SQLite"):
        read(source)
    assert source.read_bytes() == data


def test_missing_file_is_not_created(tmp_path):
    source = tmp_path / "missing.db"
    with pytest.raises(DataError, match="SQLite"):
        read(source)
    assert not source.exists()


def test_worker_cancellation_is_preserved_and_source_closed(tmp_path, monkeypatch):
    source = database(tmp_path, values=[("Anna", i) for i in range(10003)])
    import platform_app.data.sqlite_format as adapter

    opened = []
    original_connect = sqlite3.connect

    def track(*args, **kwargs):
        db = original_connect(*args, **kwargs)
        opened.append(db)
        return db

    monkeypatch.setattr(adapter.sqlite3, "connect", track)
    started = False

    class Cancelled(Exception):
        pass

    def heartbeat():
        if started:
            raise Cancelled("lease lost")

    rows = SQLiteSource(source, None, heartbeat).rows()
    assert next(rows) == ["Name", "Wert"]
    started = True
    with pytest.raises(Cancelled, match="lease lost"):
        list(rows)
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened[0].execute("SELECT 1")


@pytest.mark.parametrize("extension", ["db", "sqlite", "SQLITE3"])
def test_upload_aliases_and_table_validation(extension):
    payload = UploadInput(
        name="Synthetisch", filename="test." + extension, total_bytes=8192, table_name="Daten"
    )
    assert payload.table_name == "Daten"
    with pytest.raises(ValidationError):
        ImportOptions(table_name="x\x00y")
