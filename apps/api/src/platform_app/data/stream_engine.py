"""Dateibasierte CSV-Pipeline: exakte Aggregate ohne vollständige Tabelle im RAM."""

import csv
import json
import re
import sqlite3
from collections.abc import Callable, Generator, Iterator
from decimal import Decimal, localcontext
from itertools import chain
from pathlib import Path
from typing import Literal, TextIO

from platform_app.data.csv_format import CsvFormat, detect_format
from platform_app.data.engine import NUMBER, DataError, is_date
from platform_app.data.json_format import tabular_rows
from platform_app.data.parquet_format import tabular_rows as parquet_rows
from platform_app.data.schemas import (
    ColumnProfile,
    CsvImportInfo,
    CsvOptions,
    DataProfile,
    Frequency,
    ImportOptions,
    Step,
)
from platform_app.data.sqlite_format import SQLiteSource
from platform_app.data.xlsx_format import tabular_rows as xlsx_rows

MAX_COLUMNS = 256
MAX_CELL_CHARS = 1048576
MAX_RECORD_BYTES = 4 * 1024 * 1024
INVALID = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff]")
Progress = Callable[[int, str, int], None]


class BoundedLines:
    def __init__(self, stream: TextIO):
        self.stream = stream
        self.record_size = 0

    def __iter__(self) -> "BoundedLines":
        return self

    def __next__(self) -> str:
        line = self.stream.readline(MAX_RECORD_BYTES + 1)
        if not line:
            raise StopIteration
        self.record_size += len(line.encode("utf8"))
        if self.record_size > MAX_RECORD_BYTES:
            raise DataError("Ein CSV-Datensatz überschreitet 4 MiB.")
        return line


def encode_row(row: list[str]) -> str:
    if any(len(v) > MAX_CELL_CHARS or INVALID.search(v) for v in row):
        raise DataError("Eine Zelle enthält unzulässige Zeichen oder mehr als 1.048.576 Zeichen.")
    value = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
    if len(value.encode("utf8")) + 1 > MAX_RECORD_BYTES:
        raise DataError("Ein normalisierter Datensatz überschreitet 4 MiB.")
    return value


def source_rows(
    path: Path, delimiter: str, jsonl: bool, detected: CsvFormat | None = None
) -> Generator[list[str], None, None]:
    csv.field_size_limit(MAX_CELL_CHARS)
    try:
        with path.open(
            encoding=detected.encoding if detected else "utf-8-sig", newline=""
        ) as stream:
            for _ in range(detected.skip_lines if detected else 0):
                stream.readline(MAX_RECORD_BYTES + 1)
            lines = BoundedLines(stream)
            if jsonl:
                for line in lines:
                    lines.record_size = 0
                    value = json.loads(line)
                    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                        raise DataError("Das Datenformat der gespeicherten Version ist ungültig.")
                    yield value
            else:
                if delimiter not in {";", ",", "\t", "|"}:
                    raise DataError("Ungültiges Trennzeichen.")
                reader = csv.reader(lines, delimiter=delimiter, strict=True)
                for row in reader:
                    lines.record_size = 0
                    yield row
    except UnicodeError:
        raise DataError(
            "Die Dateikodierung passt nicht. Bitte den Import mit passender Kodierung wiederholen (z. B. Windows-1252 für ältere Excel-Dateien)."
        ) from None
    except csv.Error as error:
        if "field larger" in str(error):
            raise DataError(
                "Eine CSV-Zelle überschreitet 1.048.576 Zeichen. Die Datei muss nicht neu hochgeladen werden; die Zellgröße muss reduziert werden."
            ) from None
        raise DataError(
            "Das CSV-Format ist ungültig. Bitte Trennzeichen und die Schreibweise eingebetteter Anführungszeichen prüfen; Textfelder müssen korrekt zitiert sein."
        ) from None
    except json.JSONDecodeError:
        raise DataError("Das Format der gespeicherten Datenversion ist ungültig.") from None


def build(
    source: Path,
    directory: Path,
    delimiter: str,
    jsonl: bool,
    steps: list[Step],
    progress: Progress,
    csv_options: CsvOptions | ImportOptions | None = None,
    source_format: Literal["csv", "json", "jsonl", "xlsx", "parquet", "sqlite"] = "csv",
) -> tuple[Path, Path, DataProfile, int]:
    reader: Iterator[list[str]] | None = None
    db = sqlite3.connect(directory / "analysis.sqlite")
    try:
        db.execute("PRAGMA cache_size=-8192")
        db.execute("PRAGMA temp_store=FILE")
        db.execute("PRAGMA journal_mode=OFF")
        db.create_function("nonempty", 1, lambda value: int(bool(str(value).strip())))

        def sqlite_heartbeat() -> int:
            progress(-1, "", 0)
            return 0

        db.set_progress_handler(sqlite_heartbeat, 10000)
        db.execute("CREATE TABLE rows(seq INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        for i, step in enumerate(steps):
            if step.operation == "drop_duplicates":
                db.execute(f"CREATE TABLE seen_{i}(value TEXT PRIMARY KEY) WITHOUT ROWID")
        options = (
            ImportOptions.model_validate(csv_options.model_dump())
            if csv_options
            else ImportOptions.model_validate({"delimiter": delimiter, "encoding": "utf-8-sig"})
        )
        detected = detect_format(source, options) if not jsonl and source_format == "csv" else None
        sqlite_source = None
        if not jsonl and source_format == "sqlite":
            sqlite_source = SQLiteSource(source, options.table_name, lambda: progress(-1, "", 0))
            values = sqlite_source.rows()
        elif not jsonl and source_format == "parquet":
            values = parquet_rows(source, lambda: progress(-1, "", 0))
        elif not jsonl and source_format == "xlsx":
            values = xlsx_rows(source, options.worksheet, lambda: progress(-1, "", 0))
        elif not jsonl and source_format in {"json", "jsonl"}:
            values = tabular_rows(source, lines=source_format == "jsonl")
        else:
            values = source_rows(
                source, detected.delimiter if detected else delimiter, jsonl, detected
            )
        reader = values
        first = next(values, [])
        if not jsonl and source_format in {"csv", "xlsx"} and not options.has_header:
            columns = [f"Spalte_{i + 1}" for i in range(len(first))]
            values = chain([first], values)
        else:
            columns = first
        if not 1 <= len(columns) <= MAX_COLUMNS:
            raise DataError("Die Datei benötigt 1 bis 256 Spalten.")
        if any(not c.strip() or len(c) > 100 or INVALID.search(c) for c in columns):
            raise DataError(
                "Eine Kopfzelle ist leer, enthält Steuerzeichen oder mehr als 100 Zeichen. Trennzeichen prüfen; bei Dateien ohne Kopfzeile die Option „Erste Zeile enthält Spaltennamen“ ausschalten."
            )
        if len({c.strip() for c in columns}) != len(columns):
            raise DataError(
                "Spaltennamen müssen auch nach Entfernen äußerer Leerzeichen eindeutig sein."
            )
        for step in steps:
            if step.column is not None and step.column not in columns:
                raise DataError("Die gewählte Spalte ist in dieser Version nicht vorhanden.")
        count = 0
        for position, row in enumerate(values, 2):
            if not row:
                row = [""] * len(columns)
            if len(row) != len(columns):
                raise DataError(
                    f"CSV-Datensatz {position} enthält {len(row)} statt {len(columns)} Spalten. Bitte Trennzeichen, fehlende Felder oder eingebettete Anführungszeichen prüfen."
                )
            encode_row(row)
            skip = False
            for i, step in enumerate(steps):
                if step.operation == "drop_empty_rows":
                    if not any(v.strip() for v in row):
                        skip = True
                        break
                elif step.operation == "drop_duplicates":
                    cursor = db.execute(
                        f"INSERT OR IGNORE INTO seen_{i}(value) VALUES(?)", (encode_row(row),)
                    )
                    if not cursor.rowcount:
                        skip = True
                        break
                else:
                    index = columns.index(step.column or "")
                    value = row[index]
                    if step.operation == "trim":
                        row[index] = value.strip()
                    elif step.operation == "fill_missing":
                        row[index] = value if value.strip() else (step.value or "")
                    elif step.operation == "lowercase":
                        row[index] = value.lower()
                    elif step.operation == "uppercase":
                        row[index] = value.upper()
                    encode_row(row)
            if not skip:
                db.execute("INSERT INTO rows(value) VALUES(?)", (encode_row(row),))
                count += 1
            if position % 1000 == 0:
                db.commit()
                progress(35, "Tabelle wird geprüft und zeilenweise verarbeitet", position - 1)
        db.commit()
        progress(55, "Qualitätsprofil wird berechnet", count)
        result = calculate_profile(db, columns, count, progress)
        result.source_format = source_format
        if sqlite_source:
            result.source_table = sqlite_source.table_name
        if source_format == "xlsx" and not jsonl:
            result.source_worksheet = options.worksheet
        if detected:
            result.import_info = CsvImportInfo(
                delimiter=detected.delimiter,
                encoding=detected.encoding,
                has_header=options.has_header,
                skipped_lines=detected.skip_lines,
            )
        normalized, exported = directory / "rows.jsonl", directory / "export.csv"
        protected = 0

        def safe(value: str) -> str:
            nonlocal protected
            if value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(
                ("=", "+", "-", "@", "＝", "＋", "－", "＠")
            ):
                protected += 1
                return "'" + value
            return value

        with (
            normalized.open("wb") as output,
            exported.open("w", encoding="utf-8-sig", newline="") as csv_output,
        ):
            output.write((encode_row(columns) + "\n").encode("utf8"))
            writer = csv.writer(
                csv_output, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n"
            )
            writer.writerow([safe(c) for c in columns])
            for position, (encoded,) in enumerate(
                db.execute("SELECT value FROM rows ORDER BY seq"), 1
            ):
                output.write((encoded + "\n").encode("utf8"))
                writer.writerow([safe(v) for v in json.loads(encoded)])
                if position % 1000 == 0:
                    progress(75, "Datenversion und sicherer Export werden erstellt", position)
        return normalized, exported, result, protected
    finally:
        try:
            if isinstance(reader, Generator):
                reader.close()
        finally:
            db.close()


def calculate_profile(
    db: sqlite3.Connection, columns: list[str], count: int, progress: Progress
) -> DataProfile:
    missing = [0] * len(columns)
    numeric = [True] * len(columns)
    boolean = [True] * len(columns)
    dates = [True] * len(columns)
    totals = [Decimal(0) for _ in columns]
    minimum: list[Decimal | None] = [None] * len(columns)
    maximum: list[Decimal | None] = [None] * len(columns)
    samples: list[list[str]] = []
    sample_bytes = 0
    with localcontext() as context:
        context.prec = 60
        for position, (encoded,) in enumerate(db.execute("SELECT value FROM rows ORDER BY seq"), 1):
            row = json.loads(encoded)
            if len(samples) < 25:
                sample = [v[:512] for v in row]
                size = len(json.dumps(sample).encode("utf8"))
                if sample_bytes + size <= 262144:
                    samples.append(sample)
                    sample_bytes += size
            for i, value in enumerate(row):
                if not value.strip():
                    missing[i] += 1
                    continue
                if numeric[i]:
                    if NUMBER.fullmatch(value):
                        number = Decimal(value)
                        totals[i] += number
                        previous_min, previous_max = minimum[i], maximum[i]
                        minimum[i] = number if previous_min is None else min(previous_min, number)
                        maximum[i] = number if previous_max is None else max(previous_max, number)
                    else:
                        numeric[i] = False
                if boolean[i]:
                    boolean[i] = value.lower() in {"true", "false"}
                if dates[i]:
                    dates[i] = is_date(value)
            if position % 1000 == 0:
                progress(55, "Dezimalwerte und Fehlwerte werden berechnet", position)
        # Eine gemeinsame dateibasierte Aggregation statt zweier vollständiger
        # JSON-Scans je Spalte. Originalwerte und Reihenfolge bei Gleichstand bleiben exakt.
        progress(60, "Häufigkeiten aller Spalten werden gemeinsam berechnet", count)
        db.execute(
            "CREATE TABLE frequencies AS SELECT j.key AS col,j.value AS value,"
            "count(*) AS n,min(r.seq) AS first_seq FROM rows AS r,json_each(r.value) AS j "
            "WHERE nonempty(j.value) GROUP BY j.key,j.value"
        )
        db.execute("CREATE INDEX frequencies_col ON frequencies(col)")
        profiles = []
        for i, name in enumerate(columns):
            progress(65, f"Spalte {i + 1} von {len(columns)} wird ausgewertet", count)
            distinct = db.execute("SELECT count(*) FROM frequencies WHERE col=?", (i,)).fetchone()[
                0
            ]
            top = db.execute(
                "SELECT value,n FROM frequencies WHERE col=? ORDER BY n DESC,first_seq LIMIT 8",
                (i,),
            ).fetchall()
            column = ColumnProfile(
                name=name,
                inferred_type="text",
                missing=missing[i],
                distinct=distinct,
                top_values=[Frequency(value=v[:512], count=n) for v, n in top],
            )
            present = count - missing[i]
            if not present:
                column.inferred_type = "empty"
            elif numeric[i]:
                column.inferred_type = "decimal"
                column.minimum, column.maximum = str(minimum[i]), str(maximum[i])
                column.mean = str((totals[i] / present).quantize(Decimal("0.000001")))
            elif boolean[i]:
                column.inferred_type = "boolean"
            elif dates[i]:
                column.inferred_type = "date"
            profiles.append(column)
        db.execute("DROP TABLE frequencies")
        distinct_rows = db.execute(
            "SELECT count(*) FROM (SELECT value FROM rows GROUP BY value)"
        ).fetchone()[0]
        cells = count * len(columns)
        completeness = Decimal(cells - sum(missing)) * 100 / cells if cells else Decimal(0)
    return DataProfile(
        rows=count,
        columns=profiles,
        missing_cells=sum(missing),
        duplicate_rows=count - distinct_rows,
        completeness_percent=str(completeness.quantize(Decimal("0.01"))),
        sample=samples,
        profiling_version="csv-profile-stream-3",
        pipeline_version="csv-transform-stream-2",
        statistics_note="Kennzahlen und Häufigkeiten beziehen sich auf alle Zeilen. Ausreißer werden in diesem Verfahren nicht berechnet. Vorschau und Häufigkeitsbeschriftungen sind auf 512 Zeichen je Wert gekürzt.",
    )
