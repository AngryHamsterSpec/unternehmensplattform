"""Große CSV-Pipeline: vollständige Daten, exakte Statistik und begrenzte Datensätze."""

import json

import pytest
from platform_app.data.engine import DataError
from platform_app.data.schemas import Step, UploadInput
from platform_app.data.stream_engine import build


def run(tmp_path, content, steps=None):
    source = tmp_path / "input.csv"
    source.write_bytes(content)
    return build(source, tmp_path, ";", False, steps or [], lambda *_: None)


def test_more_than_old_byte_row_cell_and_column_limits(tmp_path):
    columns = [f"C{i}" for i in range(64)]
    row = ["1"] * 64
    content = (";".join(columns) + "\n" + (";".join(row) + "\n") * 6000).encode()
    normalized, exported, profile, protected = run(tmp_path, content)
    assert len(content) > 131072
    assert profile.rows == 6000 and len(profile.columns) == 64
    assert profile.duplicate_rows == 5999
    assert profile.columns[0].mean == "1.000000"
    assert profile.columns[0].top_values[0].count == 6000
    assert len(normalized.read_text().splitlines()) == 6001
    assert exported.stat().st_size > len(content)
    assert protected == 0


def test_exact_statistics_and_transform_order(tmp_path):
    _, exported, profile, protected = run(
        tmp_path,
        b"Name;Betrag\n Anna ;0.1\nAnna;0.2\n=1+2;\n;\n",
        [Step(operation="trim", column="Name"), Step(operation="drop_empty_rows")],
    )
    assert profile.rows == 3 and profile.missing_cells == 1
    assert profile.columns[1].mean == "0.150000"
    assert profile.columns[0].distinct == 2
    assert profile.columns[0].top_values[0].count == 2
    assert protected == 1 and b"'=1+2" in exported.read_bytes()


def test_duplicates_at_each_pipeline_position(tmp_path):
    normalized, _, profile, _ = run(
        tmp_path,
        b"Name\n A \nA\n A \n",
        [Step(operation="drop_duplicates"), Step(operation="trim", column="Name")],
    )
    assert profile.rows == 2 and profile.duplicate_rows == 1
    assert json.loads(normalized.read_text().splitlines()[1]) == ["A"]


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"a;b\n1\n",
        b"a;a\n1;2\n",
        b"a\n\xff",
        b"a\n\x00\n",
        b"a\n" + b"x" * 1048577 + b"\n",
        b"a\n" + b"x" * (4 * 1024 * 1024 + 1),
        (";".join(f"C{i}" for i in range(257)) + "\n").encode(),
    ],
    ids=["empty", "width", "headers", "encoding", "control", "cell", "record", "columns"],
)
def test_invalid_csv_is_rejected_without_returning_cells(tmp_path, content):
    with pytest.raises(DataError):
        run(tmp_path, content)


def test_embedded_newlines_quotes_bom_and_jsonl_roundtrip(tmp_path):
    normalized, _, result, _ = run(
        tmp_path, b'\xef\xbb\xbfA;B\r\n"eins\n"zwei"";3\r\n'.replace(b'\n"zwei"', b'\n""zwei""')
    )
    output = tmp_path / "second"
    output.mkdir()
    _, _, again, _ = build(normalized, output, ";", True, [], lambda *_: None)
    assert again.rows == result.rows == 1
    assert again.sample == result.sample


def test_one_gib_declared_limit():
    assert (
        UploadInput(name="Test", filename="test.csv", total_bytes=1073741824).total_bytes
        == 1073741824
    )
    with pytest.raises(ValueError):
        UploadInput(name="Test", filename="test.csv", total_bytes=1073741825)
