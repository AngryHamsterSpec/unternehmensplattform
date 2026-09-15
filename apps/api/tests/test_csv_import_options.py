"""Regressionen für echte Importursachen mit ausschließlich synthetischen Daten."""

import json

import pytest
from platform_app.data.csv_format import detect_format
from platform_app.data.engine import DataError
from platform_app.data.schemas import CsvOptions
from platform_app.data.stream_engine import build


def parse(tmp_path, content, **options):
    source = tmp_path / "source.csv"
    source.write_bytes(content)
    return build(
        source,
        tmp_path,
        ";",
        False,
        [],
        lambda *_: None,
        csv_options=CsvOptions.model_validate(options),
    )


@pytest.mark.parametrize("delimiter", [",", ";", "\t", "|"])
def test_auto_detects_wide_quoted_csv(tmp_path, delimiter):
    import csv
    import io

    out = io.StringIO(newline="")
    writer = csv.writer(out, delimiter=delimiter)
    writer.writerow([f"Spalte_{i:03d}_Beschreibung" for i in range(170)])
    writer.writerow(["Wert;mit,Zeichen"] * 170)
    _, _, profile, _ = parse(tmp_path, out.getvalue().encode())
    assert len(profile.columns) == 170 and profile.rows == 1
    assert profile.import_info.delimiter == delimiter
    assert profile.sample[0][0] == "Wert;mit,Zeichen"


def test_wrong_explicit_delimiter_has_actionable_message(tmp_path):
    with pytest.raises(DataError, match="wahrscheinlich Komma"):
        parse(tmp_path, b"Spalte_A,Spalte_B\n1,2\n", delimiter=";")


def test_large_valid_text_cell_is_preserved_and_editable(tmp_path):
    cell = "x" * 175026
    normalized, exported, profile, _ = parse(tmp_path, ("A,B\n1,kurz\n2," + cell + "\n").encode())
    assert profile.rows == 2
    assert json.loads(normalized.read_text().splitlines()[-1])[1] == cell
    assert cell.encode() in exported.read_bytes()
    next_dir = tmp_path / "next"
    next_dir.mkdir()
    from platform_app.data.schemas import Step

    changed, _, transformed, _ = build(
        normalized, next_dir, ",", True, [Step(operation="uppercase", column="B")], lambda *_: None
    )
    assert json.loads(changed.read_text().splitlines()[-1])[1] == cell.upper()
    assert transformed.rows == 2


def test_utf16_bom_and_excel_separator_line(tmp_path):
    _, _, profile, _ = parse(tmp_path, "\nsep=;\nName;Ort\nÄnne;Köln\n".encode("utf-16"))
    assert profile.sample == [["Änne", "Köln"]]
    assert profile.import_info.encoding == "utf-16"
    assert profile.import_info.skipped_lines == 2


def test_windows_encoding_must_be_selected_explicitly(tmp_path):
    content = "Name;Ort\nÄnne;Köln\n".encode("cp1252")
    source = tmp_path / "source.csv"
    source.write_bytes(content)
    with pytest.raises(DataError, match="Dateikodierung"):
        detect_format(source, CsvOptions())
    _, _, profile, _ = parse(tmp_path, content, encoding="cp1252")
    assert profile.sample == [["Änne", "Köln"]]


def test_headerless_file_keeps_first_record(tmp_path):
    _, _, profile, _ = parse(tmp_path, b"1,2\n3,4\n", has_header=False)
    assert [column.name for column in profile.columns] == ["Spalte_1", "Spalte_2"]
    assert profile.sample == [["1", "2"], ["3", "4"]]
    assert not profile.import_info.has_header


def test_ambiguous_auto_delimiter_requires_selection(tmp_path):
    with pytest.raises(DataError, match="Mehrere Trennzeichen"):
        parse(tmp_path, b"a,b;c\n1,2;3\n")


def test_bad_quotes_are_not_reported_as_utf8_error(tmp_path):
    with pytest.raises(DataError, match="CSV-Format"):
        parse(tmp_path, b'A,B\n"nicht geschlossen,2\n', delimiter=",")


def test_truncated_utf8_probe_is_not_a_false_encoding_error(tmp_path):
    content = ('A,B\n1,"' + "ö" * 150000 + '"\n').encode()
    _, _, profile, _ = parse(tmp_path, content)
    assert profile.rows == 1 and profile.import_info.delimiter == ","
