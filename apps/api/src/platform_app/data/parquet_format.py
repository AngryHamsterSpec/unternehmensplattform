"""Parquet in geordneten Batches; keine vollständige Tabelle im Python-RAM."""

from collections.abc import Callable, Iterator
from pathlib import Path

from thrift.Thrift import TException  # type: ignore[import-untyped]

from platform_app.data.engine import DataError
from platform_app.data.parquet_metadata import inspect_file


def tabular_rows(path: Path, heartbeat: Callable[[], None] = lambda: None) -> Iterator[list[str]]:
    # Native Bibliothek erst für diesen Adapter laden. CSV/JSON/XLSX bleiben unabhängig.
    import polars as pl

    try:
        expected_rows, columns, groups = inspect_file(path, heartbeat)
        scan = pl.scan_parquet(
            path,
            parallel="none",
            low_memory=True,
            use_statistics=False,
            hive_partitioning=False,
            glob=False,
            cache=False,
            credential_provider=None,
        )
        schema = scan.collect_schema()
        if schema.names() != columns:
            raise DataError("Parquet-Metadaten und gelesenes Schema widersprechen sich.")
        for dtype in schema.dtypes():
            if not (
                dtype.is_numeric()
                or dtype.is_temporal()
                or dtype in (pl.String, pl.Boolean, pl.Null, pl.Categorical)
                or isinstance(dtype, pl.Enum)
            ):
                raise DataError(
                    "Binäre oder verschachtelte Parquet-Spalten benötigen vorherige Aufbereitung."
                )
        yield columns
        count = 0
        offset = 0
        for group_rows in groups:
            heartbeat()
            # Eine geprüfte Gruppe pro synchronem Aufruf; kein laufender Hintergrundproduzent.
            frame = scan.slice(offset, group_rows).collect(engine="streaming")
            offset += group_rows
            if frame.height != group_rows:
                raise DataError("Eine Parquet-Zeilengruppe wurde nicht vollständig gelesen.")
            for batch in frame.iter_slices(n_rows=64):
                heartbeat()
                for name, dtype in schema.items():
                    if (
                        dtype.is_float()
                        and batch.select(
                            (pl.col(name).is_not_null() & ~pl.col(name).is_finite()).any()
                        ).item()
                    ):
                        raise DataError(
                            "Parquet enthält NaN oder unendliche Zahlen. Bitte vor dem Import bereinigen."
                        )
                strings = batch.select(pl.all().cast(pl.String, strict=True).fill_null(""))
                for row in strings.iter_rows():
                    count += 1
                    yield list(row)
            if group_rows:
                del batch, strings
            del frame
        if count != expected_rows:
            raise DataError("Die gelesene Parquet-Zeilenanzahl entspricht nicht den Metadaten.")
    except DataError:
        raise
    except (
        TException,
        pl.exceptions.PolarsError,
        pl.exceptions.PanicException,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        AttributeError,
        EOFError,
        AssertionError,
        OverflowError,
    ):
        raise DataError(
            "Die Parquet-Struktur ist beschädigt oder nicht unterstützt. Bitte als einzelne flache Parquet- oder CSV-Datei neu exportieren."
        ) from None
