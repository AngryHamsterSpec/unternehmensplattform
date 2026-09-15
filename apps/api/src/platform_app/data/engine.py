"""Begrenztes CSV-Profiling und deklarative Transformationen ohne Fremdcode."""

import csv
import hashlib
import io
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext

from platform_app.data.schemas import ColumnProfile, DataProfile, Frequency, Step

MAX_BYTES = 131072
MAX_RESULT_BYTES = 524288
MAX_ROWS = 5000
MAX_COLUMNS = 40
MAX_CELLS = 50000
NUMBER = re.compile(r"-?(?:0|[1-9][0-9]{0,23})(?:\.[0-9]{1,12})?\Z")


class DataError(ValueError):
    """Kontrollierte datenarme Fehlermeldung für Nutzer."""


@dataclass(frozen=True)
class Table:
    columns: list[str]
    rows: list[list[str]]


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def valid_cell(value: str) -> bool:
    return len(value) <= 1000 and not any(
        (ord(c) < 32 and c not in "\t\r\n") or 0xD800 <= ord(c) <= 0xDFFF for c in value
    )


def validate(table: Table) -> None:
    if not 1 <= len(table.columns) <= MAX_COLUMNS:
        raise DataError("Die Datei benötigt 1 bis 40 Spalten.")
    if any(not c.strip() or len(c) > 100 or not valid_cell(c) for c in table.columns):
        raise DataError("Spaltennamen müssen nichtleer und höchstens 100 Zeichen lang sein.")
    if len(set(c.strip() for c in table.columns)) != len(table.columns):
        raise DataError(
            "Spaltennamen müssen auch nach Entfernen äußerer Leerzeichen eindeutig sein."
        )
    if len(table.rows) > MAX_ROWS or len(table.rows) * len(table.columns) > MAX_CELLS:
        raise DataError("Die Grenze von 5.000 Zeilen oder 50.000 Zellen ist überschritten.")
    for position, row in enumerate(table.rows, 2):
        if len(row) != len(table.columns):
            raise DataError(f"CSV-Datensatz {position} hat eine abweichende Spaltenanzahl.")
        if not all(valid_cell(value) for value in row):
            raise DataError(
                f"CSV-Datensatz {position} enthält unzulässige oder zu lange Zellwerte."
            )


def parse_csv(content: bytes, delimiter: str) -> Table:
    if not content or len(content) > MAX_BYTES:
        raise DataError("Die Originaldatei muss zwischen 1 Byte und 128 KiB groß sein.")
    if delimiter not in {",", ";", "\t"}:
        raise DataError("Ungültiges Trennzeichen.")
    try:
        reader = csv.reader(
            io.StringIO(content.decode("utf-8-sig"), newline=""), delimiter=delimiter, strict=True
        )
        columns = next(reader)
        rows = []
        for row in reader:
            # Leere physische Zeilen sind im CSV-Modell Leerzeilen, keine still entfernten Daten.
            rows.append(row if row else [""] * len(columns))
            if len(rows) > MAX_ROWS:
                raise DataError("Die Grenze von 5.000 Zeilen ist überschritten.")
        table = Table(columns, rows)
    except (UnicodeDecodeError, csv.Error, StopIteration):
        raise DataError("Die Datei ist keine gültige UTF-8-CSV mit Kopfzeile.") from None
    validate(table)
    return table


def encode_table(table: Table) -> bytes:
    validate(table)
    result = json.dumps(
        {"columns": table.columns, "rows": table.rows}, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    if len(result) > MAX_RESULT_BYTES:
        raise DataError("Die abgeleiteten Daten überschreiten 512 KiB.")
    return result


def decode_table(content: bytes) -> Table:
    data = json.loads(content)
    table = Table(data["columns"], data["rows"])
    validate(table)
    return table


def transform(table: Table, steps: list[Step]) -> Table:
    rows = [row.copy() for row in table.rows]
    started = time.monotonic()
    for step in steps:
        if time.monotonic() - started > 10:
            raise DataError("Die Verarbeitung hat ihr Zeitlimit überschritten.")
        if step.operation == "drop_duplicates":
            rows = [list(row) for row in dict.fromkeys(tuple(row) for row in rows)]
        elif step.operation == "drop_empty_rows":
            rows = [row for row in rows if any(v.strip() for v in row)]
        else:
            if step.column not in table.columns:
                raise DataError("Die gewählte Spalte ist in dieser Version nicht vorhanden.")
            index = table.columns.index(step.column)
            for row in rows:
                value = row[index]
                if step.operation == "trim":
                    row[index] = value.strip()
                elif step.operation == "fill_missing":
                    row[index] = value if value.strip() else (step.value or "")
                elif step.operation == "lowercase":
                    row[index] = value.lower()
                elif step.operation == "uppercase":
                    row[index] = value.upper()
        validate(Table(table.columns, rows))
    return Table(table.columns.copy(), rows)


def is_date(value: str) -> bool:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def profile(table: Table) -> DataProfile:
    columns = []
    total_missing = 0
    with localcontext() as context:
        context.prec = 50
        for index, name in enumerate(table.columns):
            values = [row[index] for row in table.rows if row[index].strip()]
            missing = len(table.rows) - len(values)
            total_missing += missing
            frequencies = Counter(values)
            column = ColumnProfile(
                name=name,
                inferred_type="text" if values else "empty",
                missing=missing,
                distinct=len(frequencies),
                top_values=[Frequency(value=v, count=n) for v, n in frequencies.most_common(8)],
            )
            if values and all(NUMBER.fullmatch(v) for v in values):
                numbers = sorted(Decimal(v) for v in values)
                column.inferred_type = "decimal"
                column.minimum, column.maximum = str(numbers[0]), str(numbers[-1])
                column.mean = str(
                    (sum(numbers, Decimal(0)) / len(numbers)).quantize(Decimal("0.000001"))
                )
                if len(numbers) >= 5:
                    q1, q3 = numbers[(len(numbers) - 1) // 4], numbers[3 * (len(numbers) - 1) // 4]
                    distance = (q3 - q1) * Decimal("1.5")
                    column.outliers = sum(v < q1 - distance or v > q3 + distance for v in numbers)
            elif values and all(v.lower() in {"true", "false"} for v in values):
                column.inferred_type = "boolean"
            elif values and all(is_date(v) for v in values):
                column.inferred_type = "date"
            columns.append(column)
        cells = len(table.rows) * len(table.columns)
        completeness = (Decimal(cells - total_missing) * 100 / cells) if cells else Decimal(0)
    return DataProfile(
        rows=len(table.rows),
        columns=columns,
        missing_cells=total_missing,
        duplicate_rows=len(table.rows) - len({tuple(row) for row in table.rows}),
        completeness_percent=str(completeness.quantize(Decimal("0.01"))),
        sample=table.rows[:25],
    )


def safe_export(table: Table) -> tuple[bytes, int]:
    protected = 0

    def safe(value: str) -> str:
        nonlocal protected
        stripped = value.lstrip()
        if value.startswith(("\t", "\r", "\n")) or stripped.startswith(
            ("=", "+", "-", "@", "＝", "＋", "－", "＠")
        ):
            protected += 1
            return "'" + value
        return value

    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow([safe(c) for c in table.columns])
    writer.writerows([safe(v) for v in row] for row in table.rows)
    return output.getvalue().encode("utf-8-sig"), protected
