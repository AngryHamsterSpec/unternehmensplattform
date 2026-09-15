"""JSON-Adapter: vollständige Werte, Strukturen und gemeinsame Transformation."""

import json

import pytest
from platform_app.data.engine import DataError
from platform_app.data.json_format import tabular_rows
from platform_app.data.schemas import Step
from platform_app.data.stream_engine import build


def test_json_array_roundtrip_and_preview(tmp_path):
    source = tmp_path / "source.json"
    long = "x" * 175026
    source.write_text(
        '[{"Name":" Anna ","Wert":1.20,"Aktiv":true,"Notiz":'
        + json.dumps(long)
        + '},{"Aktiv":false,"Name":"Bob","Wert":null}]',
        encoding="utf-8-sig",
    )
    normalized, export, profile, _ = build(
        source, tmp_path, ";", False, [], lambda *a: None, source_format="json"
    )
    assert profile.rows == 2 and profile.source_format == "json"
    assert profile.columns[1].mean == "1.200000"
    assert list(tabular_rows(source))[2] == ["Bob", "", "false", ""]
    assert long in export.read_text(encoding="utf-8-sig")
    second = tmp_path / "preview"
    second.mkdir()
    result, _, derived, _ = build(
        normalized,
        second,
        ";",
        True,
        [Step(operation="trim", column="Name")],
        lambda *a: None,
        source_format="json",
    )
    assert derived.source_format == "json" and derived.sample[0][0] == "Anna"
    assert long in result.read_text(encoding="utf8")


@pytest.mark.parametrize(
    "content",
    [
        '[{"A":1,"A":2}]',
        '[{"A":[]}]',
        '[{"A":{}}]',
        '[{"A":NaN}]',
        '[{"A":1},{"B":2}]',
        '[{"A":1},]',
        '[{"A":1}] garbage',
        '{"A":1}',
        '[{"A":"unterbrochen}]',
    ],
)
def test_invalid_json_is_explicit(tmp_path, content):
    source = tmp_path / "input.json"
    source.write_text(content, encoding="utf8")
    with pytest.raises(DataError):
        list(tabular_rows(source))


def test_jsonl_and_reordered_keys(tmp_path):
    source = tmp_path / "input.jsonl"
    source.write_text('{"A":1,"B":"ä"}\n\n{"B":"ß","A":2}\n', encoding="utf8")
    assert list(tabular_rows(source, True)) == [["A", "B"], ["1", "ä"], ["2", "ß"]]


def test_json_record_limit_and_encoding(tmp_path):
    source = tmp_path / "input.jsonl"
    source.write_bytes(b'{"A":"' + b"x" * (4 * 1024 * 1024) + b'"}')
    with pytest.raises(DataError, match="4 MiB"):
        list(tabular_rows(source, True))
    source.write_bytes(b'[{"A":"\xff"}]')
    with pytest.raises(DataError, match="UTF-8"):
        list(tabular_rows(source))
