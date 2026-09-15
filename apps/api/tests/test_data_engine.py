"""CSV-Randfälle, reproduzierbare Pipeline und sichere Exporte."""

import csv
import io

import pytest
from platform_app.data.engine import (
    DataError,
    Table,
    decode_table,
    digest,
    encode_table,
    parse_csv,
    profile,
    safe_export,
    transform,
)
from platform_app.data.schemas import ImportInput, Step
from pydantic import ValidationError


def test_original_bom_multiline_and_roundtrip():
    source = b'\xef\xbb\xbfName;Notiz\r\nAlice;"zwei\r\nZeilen"\r\n'
    before = digest(source)
    table = parse_csv(source, ";")
    assert table.rows == [["Alice", "zwei\r\nZeilen"]]
    assert decode_table(encode_table(table)) == table
    assert digest(source) == before


@pytest.mark.parametrize(
    "source",
    [
        b"",
        b"\xff;a\n",
        b"a;a\n1;2",
        b"a; a \n1;2",
        b"a;b\n1",
        b'a;b\n"offen',
        b"a\n\x00",
        b"a\n" + b"x" * 1001,
        b"a" * 131073,
    ],
    ids=[
        "empty",
        "encoding",
        "duplicate-header",
        "ambiguous-header",
        "ragged",
        "quote",
        "control",
        "cell-limit",
        "file-limit",
    ],
)
def test_reject_malformed_and_oversized(source):
    with pytest.raises(DataError):
        parse_csv(source, ";")


def test_limits_columns_rows_cells_and_derived_size():
    for table in (
        Table(["x"] * 41, []),
        Table(["a"], [["x"]] * 5001),
        Table([str(i) for i in range(40)], [["x"] * 40] * 1251),
    ):
        with pytest.raises(DataError):
            encode_table(table)
    with pytest.raises(DataError, match="512 KiB"):
        encode_table(Table(["a"], [["x" * 1000]] * 600))


def test_profile_is_conservative_and_explains_missing_duplicates():
    table = parse_csv(
        b"id;Betrag;Datum;Deutsch\n1;10;2026-01-01;1,2\n2;20;2026-01-02;3,4\n2;20;2026-01-02;3,4\n3; ;ungueltig;\n",
        ";",
    )
    result = profile(table)
    assert result.rows == 4 and result.duplicate_rows == 1
    assert result.missing_cells == 2 and result.completeness_percent == "87.50"
    assert result.columns[1].mean == "16.666667"
    assert result.columns[2].inferred_type == "text"
    assert result.columns[3].inferred_type == "text"
    assert profile(Table(["a"], [])).completeness_percent == "0.00"


def test_deterministic_steps_preserve_original_and_count_changes():
    table = Table(["Name", "Ort"], [[" Anna ", ""], ["Anna", "Berlin"], [" ", " "]])
    result = transform(
        table,
        [
            Step(operation="trim", column="Name"),
            Step(operation="drop_empty_rows"),
            Step(operation="fill_missing", column="Ort", value="Berlin"),
            Step(operation="drop_duplicates"),
        ],
    )
    assert result.rows == [["Anna", "Berlin"]]
    assert table.rows[0] == [" Anna ", ""]
    assert digest(encode_table(result)) == digest(
        encode_table(
            transform(
                table,
                [
                    Step(operation="trim", column="Name"),
                    Step(operation="drop_empty_rows"),
                    Step(operation="fill_missing", column="Ort", value="Berlin"),
                    Step(operation="drop_duplicates"),
                ],
            )
        )
    )


def test_nonexistent_column_and_unicode_expansion_are_bounded():
    with pytest.raises(DataError):
        transform(Table(["a"], [["x"]]), [Step(operation="trim", column="b")])
    with pytest.raises(DataError):
        transform(Table(["a"], [["ß" * 1000]]), [Step(operation="uppercase", column="a")])


@pytest.mark.parametrize(
    "value", ["=1+1", "+cmd", "-2", "@SUM(A1)", "  =1", "\tvalue", "\rvalue", "\nvalue", "＝1"]
)
def test_csv_formulas_are_text_in_headers_and_values(value):
    table = Table([value], [[value], ["normal"]])
    data, count = safe_export(table)
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig")), delimiter=";"))
    assert count == 2 and rows == [["'" + value], ["'" + value], ["normal"]]
    assert table.rows[0][0] == value


@pytest.mark.parametrize(
    "step",
    [
        {"operation": "python", "value": "print(1)"},
        {"operation": "trim", "column": "a", "value": "x"},
        {"operation": "drop_duplicates", "column": "a"},
        {"operation": "fill_missing", "column": "a"},
        {"operation": "trim", "column": "a", "sql": "SELECT 1"},
    ],
)
def test_transform_contract_has_no_executable_escape(step):
    with pytest.raises(ValidationError):
        Step.model_validate(step)


@pytest.mark.parametrize("name", ["../file.csv", "C:\\file.csv", "bad\nfile.csv", "file.xlsx"])
def test_upload_filename_is_metadata_not_a_path(name):
    with pytest.raises(ValidationError):
        ImportInput(name="Test", filename=name, content_base64="YQ==")


def test_mixed_empty_dates_and_outliers():
    p = profile(
        Table(
            ["Zahl", "Datum", "Flag", "Leer"],
            [[str(n), "2026-01-01", "true", ""] for n in [1, 2, 3, 4, 100]],
        )
    )
    assert p.columns[0].outliers == 1
    assert [c.inferred_type for c in p.columns] == ["decimal", "date", "boolean", "empty"]


@pytest.mark.parametrize("value", ["\x00", "\ud800"])
def test_invalid_unicode_is_rejected_before_database(value):
    with pytest.raises(ValidationError):
        Step(operation="fill_missing", column="a", value=value)
