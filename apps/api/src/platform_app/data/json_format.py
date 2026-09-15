"""Begrenzter Adapter für flache JSON-Tabellen; Originalbytes bleiben separat erhalten."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from platform_app.data.engine import DataError

MAX_OBJECT = 4 * 1024 * 1024


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DataError("Ein JSON-Objekt enthält einen doppelten Schlüssel.")
        result[key] = value
    return result


def invalid_constant(value: str) -> None:
    raise DataError("JSON erlaubt weder NaN noch Infinity.")


DECODER = json.JSONDecoder(
    object_pairs_hook=unique_object,
    parse_int=str,
    parse_float=str,
    parse_constant=invalid_constant,
)


def objects(path: Path, lines: bool) -> Iterator[dict[str, Any]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            if lines:
                while line := stream.readline(MAX_OBJECT + 1):
                    if len(line.encode("utf8")) > MAX_OBJECT:
                        raise DataError("Ein JSON-Datensatz überschreitet 4 MiB.") from None
                    if not line.strip():
                        continue
                    value, end = DECODER.raw_decode(line.lstrip(" \t\r\n"))
                    if line.lstrip(" \t\r\n")[end:].strip():
                        raise DataError("Eine JSONL-Zeile muss genau ein Objekt enthalten.")
                    if not isinstance(value, dict):
                        raise DataError("JSONL benötigt ein flaches Objekt je Zeile.")
                    yield value
                return
            buffer = ""
            eof = False

            def read_more() -> None:
                nonlocal buffer, eof
                chunk = stream.read(65536)
                eof = not chunk
                buffer += chunk

            def whitespace() -> None:
                nonlocal buffer
                while True:
                    buffer = buffer.lstrip(" \t\r\n")
                    if buffer or eof:
                        return
                    read_more()

            whitespace()
            if not buffer.startswith("["):
                raise DataError("JSON benötigt ein Array flacher Objekte: [{...}, {...}].")
            buffer = buffer[1:]
            whitespace()
            if buffer.startswith("]"):
                buffer = buffer[1:]
            else:
                while True:
                    if not buffer.startswith("{"):
                        raise DataError("Jeder JSON-Tabelleneintrag muss ein flaches Objekt sein.")
                    while True:
                        try:
                            value, end = DECODER.raw_decode(buffer)
                            break
                        except json.JSONDecodeError:
                            if eof:
                                raise
                            if len(buffer) > MAX_OBJECT:
                                raise DataError("Ein JSON-Datensatz überschreitet 4 MiB.") from None
                            read_more()
                    if len(buffer[:end].encode("utf8")) > MAX_OBJECT:
                        raise DataError("Ein JSON-Datensatz überschreitet 4 MiB.") from None
                    yield value
                    buffer = buffer[end:]
                    whitespace()
                    if buffer.startswith("]"):
                        buffer = buffer[1:]
                        break
                    if not buffer.startswith(","):
                        raise DataError(
                            "Zwischen JSON-Objekten fehlt ein Komma oder das Arrayende."
                        )
                    buffer = buffer[1:]
                    whitespace()
            whitespace()
            if buffer:
                raise DataError("Nach dem JSON-Array stehen weitere Inhalte.")
    except UnicodeError:
        raise DataError("JSON benötigt gültiges UTF-8. Bitte die Dateikodierung prüfen.") from None
    except (json.JSONDecodeError, RecursionError):
        raise DataError("Die JSON-Struktur ist beschädigt oder zu tief verschachtelt.") from None


def tabular_rows(path: Path, lines: bool = False) -> Iterator[list[str]]:
    columns: list[str] | None = None
    for item in objects(path, lines):
        if columns is None:
            columns = list(item)
            if not columns:
                raise DataError("Das erste JSON-Objekt benötigt mindestens eine Spalte.")
            yield columns
        if set(item) - set(columns):
            raise DataError(
                "Ein JSON-Objekt enthält zusätzliche Spalten gegenüber dem ersten Objekt."
            )
        row = []
        for column in columns:
            value = item.get(column)
            if value is None:
                row.append("")
            elif isinstance(value, bool):
                row.append("true" if value else "false")
            elif isinstance(value, str):
                row.append(value)
            else:
                raise DataError("Verschachtelte JSON-Objekte und Arrays sind keine flachen Zellen.")
        yield row
