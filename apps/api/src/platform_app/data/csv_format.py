"""Begrenzte CSV-Formaterkennung; explizite Auswahl wird niemals still ersetzt."""

import codecs
import csv
import io
from dataclasses import dataclass
from pathlib import Path

from platform_app.data.engine import DataError
from platform_app.data.schemas import CsvOptions

PROBE_BYTES = 262144
DELIMITERS = {";": "Semikolon", ",": "Komma", "\t": "Tabulator", "|": "Senkrechter Strich"}


@dataclass(frozen=True)
class CsvFormat:
    delimiter: str
    encoding: str
    skip_lines: int


def detect_format(path: Path, options: CsvOptions) -> CsvFormat:
    with path.open("rb") as stream:
        raw = stream.read(PROBE_BYTES + 1)
    if not raw:
        raise DataError("Die Datei ist leer.")
    complete = len(raw) <= PROBE_BYTES
    raw = raw[:PROBE_BYTES]
    if raw.startswith(b"PK\x03\x04"):
        raise DataError(
            "Die Datei ist ein ZIP-/Excel-Format. Bitte als CSV exportieren; Umbenennen reicht nicht."
        )
    encoding = options.encoding
    if encoding == "auto":
        if raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
            raise DataError(
                "UTF-32 wird nicht unterstützt. Bitte die Datei als UTF-8-CSV speichern."
            )
        encoding = (
            "utf-16" if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)) else "utf-8-sig"
        )
    try:
        sample = codecs.getincrementaldecoder(encoding)(errors="strict").decode(raw, final=complete)
    except UnicodeError:
        raise DataError(
            "Die Dateikodierung passt nicht. Für ältere Excel-Dateien Windows-1252, für Unicode-Dateien UTF-8 oder UTF-16 wählen."
        ) from None
    if "\x00" in sample:
        raise DataError(
            "Die Datei enthält Nullzeichen. Bitte die Kodierung prüfen; UTF-16 benötigt eine passende Auswahl und BOM."
        )
    physical = sample.splitlines(keepends=True)
    skip = 0
    while skip < len(physical) and not physical[skip].strip():
        skip += 1
    if skip == len(physical):
        raise DataError("Es wurde keine CSV-Kopfzeile gefunden.")
    directive = physical[skip].strip()
    declared = (
        directive[-1]
        if len(directive) == 5 and directive[:4].lower() == "sep=" and directive[-1] in DELIMITERS
        else None
    )
    if declared:
        skip += 1
        if options.delimiter not in {"auto", declared}:
            raise DataError(
                "Die sep=-Zeile der Datei nennt ein anderes Trennzeichen. Bitte Automatisch wählen."
            )
    sample = "".join(physical[skip:])
    csv.field_size_limit(1048576)
    candidates = []
    multi_header = False
    for delimiter in DELIMITERS:
        reader = csv.reader(io.StringIO(sample, newline=""), delimiter=delimiter, strict=True)
        widths = []
        malformed = False
        try:
            for _ in range(33):
                row = next(reader, None)
                if row is None:
                    break
                if row:
                    widths.append(len(row))
        except csv.Error:
            # Ein abgeschnittener letzter Datensatz zählt nicht als Gegenbeweis.
            malformed = complete
        if widths:
            multi_header = multi_header or widths[0] > 1
            if not complete and len(widths) < 33 and len(widths) > 1:
                widths = widths[:-1]
            if not malformed and widths and all(w == widths[0] for w in widths):
                candidates.append((delimiter, widths[0]))
    wide = [d for d, width in candidates if width > 1]
    guessed = declared or (wide[0] if len(wide) == 1 else None)
    if options.delimiter != "auto":
        if guessed and guessed != options.delimiter:
            raise DataError(
                f"Gewählt: {DELIMITERS[options.delimiter]}. Die Datei verwendet wahrscheinlich {DELIMITERS[guessed]}. Bitte den Import mit Automatisch oder {DELIMITERS[guessed]} wiederholen."
            )
        return CsvFormat(options.delimiter, encoding, skip)
    if guessed:
        return CsvFormat(guessed, encoding, skip)
    if len(wide) > 1:
        raise DataError(
            "Mehrere Trennzeichen passen zur Datei. Bitte Komma, Semikolon, Tabulator oder senkrechten Strich ausdrücklich auswählen."
        )
    if multi_header or not candidates:
        raise DataError(
            "Das Trennzeichen konnte nicht zuverlässig erkannt werden. Bitte das Trennzeichen auswählen und die Spaltenanzahl sowie Anführungszeichen prüfen."
        )
    return CsvFormat(candidates[0][0], encoding, skip)
