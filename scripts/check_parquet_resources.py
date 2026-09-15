"""Synthetischer Linux-Container-Nachweis; separat unter 256 MiB und 1 CPU ausführen."""

import json
import resource
import tempfile
import time
from pathlib import Path

import polars as pl
from platform_app.data.stream_engine import build

start = time.monotonic()
with tempfile.TemporaryDirectory() as folder:
    directory = Path(folder)
    source = directory / "synthetisch.parquet"
    frame = pl.DataFrame({f"Wert_{i}": range(100003) for i in range(8)})
    frame.write_parquet(source, row_group_size=20000, compression="zstd")
    del frame
    _, _, profile, _ = build(
        source, directory, ";", False, [], lambda *a: None, source_format="parquet"
    )
    assert profile.rows == 100003 and len(profile.columns) == 8
    assert profile.columns[0].minimum == "0" and profile.columns[0].maximum == "100002"
    print(
        json.dumps(
            {
                "rows": profile.rows,
                "columns": len(profile.columns),
                "input_bytes": source.stat().st_size,
                "elapsed_seconds": round(time.monotonic() - start, 3),
                "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
            }
        )
    )
