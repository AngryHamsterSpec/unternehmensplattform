"""Synthetische Parquet-Dateien: Werte, Kompression, Grenzen und Fehler."""

from datetime import date, datetime
from decimal import Decimal

import polars as pl
import pytest
from platform_app.data.engine import DataError
from platform_app.data.parquet_format import tabular_rows
from platform_app.data.parquet_metadata import MAX_FOOTER, decode_footer, inspect_file
from platform_app.data.schemas import Step, UploadInput
from platform_app.data.stream_engine import build
from thrift.Thrift import TException


@pytest.mark.parametrize("compression", ["uncompressed", "snappy", "gzip", "zstd", "lz4"])
def test_roundtrip_types_order_and_preview(tmp_path, compression):
    source = tmp_path / "source.parquet"
    pl.DataFrame(
        {
            "Name": [" Anna ", "Bob", None],
            "Ganzzahl": [2**60 + 1, 2, None],
            "Betrag": [Decimal("123456789012345678.1200"), Decimal("1.2500"), None],
            "Aktiv": [True, False, None],
            "Datum": [date(2026, 9, 13), None, None],
            "Zeit": [datetime(2026, 9, 13, 12, 30), None, None],
        }
    ).write_parquet(source, compression=compression, row_group_size=1)
    original = source.read_bytes()
    result, _, profile, _ = build(
        source, tmp_path, ";", False, [], lambda *a: None, source_format="parquet"
    )
    assert profile.source_format == "parquet" and profile.rows == 3
    assert profile.sample[0][1] == str(2**60 + 1)
    assert profile.sample[0][2] == "123456789012345678.1200"
    assert profile.sample[0][3:5] == ["true", "2026-09-13"]
    assert profile.sample[2] == [""] * 6
    work = tmp_path / "preview"
    work.mkdir()
    _, exported, cleaned, _ = build(
        result,
        work,
        ";",
        True,
        [Step(operation="trim", column="Name")],
        lambda *a: None,
        source_format="parquet",
    )
    assert cleaned.sample[0][0] == "Anna"
    assert "123456789012345678.1200" in exported.read_text(encoding="utf-8-sig")
    assert source.read_bytes() == original


@pytest.mark.parametrize("values", [[[1, 2]], [{"nested": 1}], [b"bytes"]])
def test_unsupported_nested_or_binary(tmp_path, values):
    source = tmp_path / "source.parquet"
    pl.DataFrame({"A": values}).write_parquet(source)
    with pytest.raises(DataError, match="verschachtelt|Verschachtelt|Binäre"):
        list(tabular_rows(source))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_rejected(tmp_path, value):
    source = tmp_path / "source.parquet"
    pl.DataFrame({"A": [value]}).write_parquet(source)
    with pytest.raises(DataError, match="NaN"):
        list(tabular_rows(source))


def test_empty_table_keeps_schema(tmp_path):
    source = tmp_path / "source.parquet"
    pl.DataFrame(schema={"Name": pl.String, "Wert": pl.Int64}).write_parquet(source)
    assert list(tabular_rows(source)) == [["Name", "Wert"]]
    assert inspect_file(source, lambda: None)[0] == 0


def test_many_batches_preserve_every_row(tmp_path):
    source = tmp_path / "source.parquet"
    pl.DataFrame({"Wert": range(10003)}).write_parquet(source, row_group_size=1000)
    rows = list(tabular_rows(source))
    assert [int(row[0]) for row in rows[1:]] == list(range(10003))


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"csv,data",
        b"PAR1" + b"x" * 20 + (MAX_FOOTER + 1).to_bytes(4, "little") + b"PAR1",
        b"PARE" + b"x" * 20 + (5).to_bytes(4, "little") + b"PARE",
        b"PAR1" + b"bad-footer" + (10).to_bytes(4, "little") + b"PAR1",
    ],
    ids=["empty", "wrong-format", "large-footer", "encrypted", "invalid-thrift"],
)
def test_invalid_file(tmp_path, content):
    source = tmp_path / "source.parquet"
    source.write_bytes(content)
    with pytest.raises(DataError):
        list(tabular_rows(source))


def test_overlong_thrift_integer_is_bounded():
    with pytest.raises(TException, match="10 bytes"):
        decode_footer(b"\x15" + b"\x80" * 100, lambda: None)


def test_footer_limits_and_external_references(tmp_path, monkeypatch):
    source = tmp_path / "source.parquet"
    pl.DataFrame({"Name": ["Anna"]}).write_parquet(source)
    import platform_app.data.parquet_metadata as metadata

    with source.open("rb") as stream:
        stream.seek(-8, 2)
        size = int.from_bytes(stream.read(4), "little")
        stream.seek(-8 - size, 2)
        original = decode_footer(stream.read(size), lambda: None)
    import copy

    cases = [
        (lambda m: m[4][0][1][0].update({1: b"../../private"}), "Externe"),
        (lambda m: m[4][0].update({2: 100000000}), "Größenangaben"),
        (lambda m: m.update({3: 100}), "Zeilenanzahl"),
        (lambda m: m.update({8: {}}), "Verschlüsseltes"),
    ]
    for mutate, message in cases:
        changed = copy.deepcopy(original)
        mutate(changed)
        monkeypatch.setattr(metadata, "decode_footer", lambda *a, value=changed: value)
        with pytest.raises(DataError, match=message):
            list(tabular_rows(source))


def test_cancellation_and_upload_contract(tmp_path):
    source = tmp_path / "source.parquet"
    pl.DataFrame({"A": range(200)}).write_parquet(source)
    calls = 0

    def cancel():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError("Testabbruch")

    with pytest.raises(RuntimeError, match="Testabbruch"):
        list(tabular_rows(source, cancel))
    assert UploadInput(name="Test", filename="DATEI.PARQUET", total_bytes=100).total_bytes == 100


def test_pipeline_closes_reader_when_normalization_fails(tmp_path, monkeypatch):
    import platform_app.data.stream_engine as engine

    closed = []

    def source():
        try:
            yield ["A"]
            yield ["\x00"]
        finally:
            closed.append(True)

    held = source()
    monkeypatch.setattr(engine, "parquet_rows", lambda *args: held)
    with pytest.raises(DataError, match="unzulässige"):
        build(
            tmp_path / "unused", tmp_path, ";", False, [], lambda *a: None, source_format="parquet"
        )
    assert closed == [True]
