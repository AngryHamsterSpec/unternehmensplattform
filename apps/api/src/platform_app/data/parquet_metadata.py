"""Begrenzte Metadatenvorprüfung; Zellseiten dekodiert ausschließlich Polars."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from thrift.protocol.TCompactProtocol import TCompactProtocol  # type: ignore[import-untyped]
from thrift.Thrift import TType  # type: ignore[import-untyped]
from thrift.transport.TTransport import TMemoryBuffer  # type: ignore[import-untyped]

from platform_app.data.engine import DataError

MAX_FOOTER = 8 * 1024 * 1024
MAX_GROUP = 64 * 1024 * 1024
MAX_TOTAL = 8 * 1024 * 1024 * 1024


def decode_footer(value: bytes, heartbeat: Callable[[], None]) -> dict[int, Any]:
    transport = TMemoryBuffer(value)
    protocol = TCompactProtocol(
        transport, string_length_limit=MAX_FOOTER, container_length_limit=16384
    )
    remaining = 200000

    def read(kind: int, depth: int = 0) -> object:
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 16:
            raise DataError("Die Parquet-Metadaten sind zu komplex.")
        if remaining % 1000 == 0:
            heartbeat()
        if kind == TType.STRUCT:
            protocol.readStructBegin()
            fields: dict[int, object] = {}
            while True:
                _, field_kind, field_id = protocol.readFieldBegin()
                if field_kind == TType.STOP:
                    break
                if field_id in fields:
                    raise DataError("Die Parquet-Metadaten enthalten doppelte Felder.")
                fields[field_id] = read(field_kind, depth + 1)
                protocol.readFieldEnd()
            protocol.readStructEnd()
            return fields
        if kind in (TType.LIST, TType.SET):
            element, count = protocol.readListBegin()
            if not 0 <= count <= 16384:
                raise DataError("Eine Parquet-Metadatenliste ist zu groß.")
            result = [read(element, depth + 1) for _ in range(count)]
            protocol.readListEnd()
            return result
        readers = {
            TType.BOOL: protocol.readBool,
            TType.BYTE: protocol.readByte,
            TType.I16: protocol.readI16,
            TType.I32: protocol.readI32,
            TType.I64: protocol.readI64,
            TType.DOUBLE: protocol.readDouble,
            TType.STRING: protocol.readBinary,
        }
        if kind not in readers:
            raise DataError("Ein Parquet-Metadatentyp wird nicht unterstützt.")
        return cast(object, readers[kind]())

    result = cast(dict[int, Any], read(TType.STRUCT))
    if transport.read(1):
        raise DataError("Der Parquet-Metadatenfuß enthält unerwartete Restdaten.")
    return result


def inspect_file(path: Path, heartbeat: Callable[[], None]) -> tuple[int, list[str], list[int]]:
    with path.open("rb") as source:
        size = source.seek(0, 2)
        if size < 12:
            raise DataError("Die Datei ist keine vollständige Parquet-Datei.")
        source.seek(0)
        start = source.read(4)
        source.seek(-8, 2)
        footer = source.read(8)
        if start != b"PAR1" or footer[4:] != b"PAR1":
            raise DataError(
                "Parquet benötigt PAR1-Dateimarker; verschlüsselte Dateien werden nicht unterstützt."
            )
        length = int.from_bytes(footer[:4], "little")
        if not 1 <= length <= min(MAX_FOOTER, size - 12):
            raise DataError("Der Parquet-Metadatenfuß ist ungültig oder größer als 8 MiB.")
        data_end = size - 8 - length
        source.seek(data_end)
        meta = decode_footer(source.read(length), heartbeat)
    if 8 in meta or 9 in meta:
        raise DataError("Verschlüsseltes Parquet wird nicht unterstützt.")
    schema = meta[2]
    if not isinstance(schema, list) or not 2 <= len(schema) <= 257:
        raise DataError("Parquet benötigt ein flaches Schema mit 1 bis 256 Spalten.")
    if schema[0].get(5) != len(schema) - 1 or any(
        1 not in item or item.get(5, 0) or item.get(3) == 2 for item in schema[1:]
    ):
        raise DataError("Verschachtelte Parquet-Spalten benötigen vorherige Aufbereitung.")
    names = [item[4].decode("utf-8") for item in schema[1:]]
    groups = meta[4]
    if not isinstance(groups, list) or len(groups) > 4096:
        raise DataError("Die Parquet-Datei überschreitet 4.096 Zeilengruppen.")
    rows, expanded = 0, 0
    for group in groups:
        heartbeat()
        count, group_size = group[3], group[2]
        if type(count) is not int or count < 0 or type(group_size) is not int or group_size < 0:
            raise DataError("Parquet enthält ungültige Zeilen- oder Größenangaben.")
        columns = group[1]
        if len(columns) != len(names):
            raise DataError("Parquet-Zeilengruppe und Schema widersprechen sich.")
        total = 0
        for index, column in enumerate(columns):
            if column.get(1) or 8 in column or 9 in column:
                raise DataError(
                    "Externe oder verschlüsselte Parquet-Spalten werden nicht importiert."
                )
            details = column[3]
            uncompressed, compressed = details[6], details[7]
            if (
                type(uncompressed) is not int
                or type(compressed) is not int
                or min(uncompressed, compressed) < 0
            ):
                raise DataError("Ungültige Parquet-Spaltengröße.")
            if details[3] != [names[index].encode("utf-8")] or details[5] != count:
                raise DataError(
                    "Parquet-Spaltenpfad oder Werteanzahl passt nicht zum flachen Schema."
                )
            offsets = [details[9]]
            if 11 in details:
                offsets.append(details[11])
            if (
                any(type(offset) is not int or not 4 <= offset <= data_end for offset in offsets)
                or min(offsets) + compressed > data_end
            ):
                raise DataError("Eine Parquet-Spalte verweist außerhalb des Datenbereichs.")
            total += uncompressed
        if total != group_size:
            raise DataError("Parquet-Größenangaben der Zeilengruppe widersprechen sich.")
        if total > MAX_GROUP:
            raise DataError(
                "Eine Parquet-Zeilengruppe überschreitet 64 MiB entpackt. Bitte mit kleineren Row-Groups neu exportieren."
            )
        expanded += total
        rows += count
        if expanded > MAX_TOTAL:
            raise DataError("Die Parquet-Datei überschreitet 8 GiB deklarierte entpackte Daten.")
    if type(meta[3]) is not int or meta[3] != rows:
        raise DataError("Parquet-Zeilenanzahl und Zeilengruppen widersprechen sich.")
    return rows, names, [group[3] for group in groups]
