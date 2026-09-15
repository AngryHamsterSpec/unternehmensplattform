"""Verträge des begrenzten CSV-Ablaufs; keine ausführbaren Ausdrücke."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*")
    @classmethod
    def postgres_text(cls, value: object) -> object:
        if isinstance(value, str) and any(c == "\x00" or 0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError("Ungültiges Unicode-Zeichen.")
        return value


class CsvOptions(StrictModel):
    delimiter: Literal["auto", ",", ";", "\t", "|"] = "auto"
    encoding: Literal["auto", "utf-8-sig", "utf-16", "cp1252"] = "auto"
    has_header: bool = True


class ImportOptions(CsvOptions):
    worksheet: int = Field(default=1, ge=1, le=100)
    table_name: str | None = Field(default=None, min_length=1, max_length=100)


class CsvImportInfo(BaseModel):
    delimiter: str
    encoding: str
    has_header: bool
    skipped_lines: int = 0
    reader_version: str = "csv-reader-2"


class ImportInput(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    filename: str = Field(min_length=1, max_length=160, pattern=r"^[^/\\\x00-\x1f]+\.csv$")
    content_base64: str = Field(min_length=1, max_length=174764)
    delimiter: Literal[",", ";", "\t"] = ";"


class Step(StrictModel):
    operation: Literal[
        "trim", "fill_missing", "lowercase", "uppercase", "drop_duplicates", "drop_empty_rows"
    ]
    column: str | None = Field(default=None, max_length=100)
    value: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def valid_arguments(self) -> "Step":
        if self.operation in {"drop_duplicates", "drop_empty_rows"}:
            if self.column is not None or self.value is not None:
                raise ValueError("Diese Operation hat keine Spaltenargumente.")
        elif not self.column:
            raise ValueError("Eine Spalte ist erforderlich.")
        if (self.operation == "fill_missing") != (self.value is not None):
            raise ValueError("Nur Fehlwertersetzung benötigt einen Ersatzwert.")
        return self


class PreviewInput(StrictModel):
    source_version: int = Field(ge=1)
    steps: list[Step] = Field(min_length=1, max_length=10)


class CommitInput(StrictModel):
    preview_id: UUID
    result_hash: str = Field(pattern="^[0-9a-f]{64}$")
    expected_current_version: int = Field(ge=1)


class Frequency(BaseModel):
    value: str
    count: int


class ColumnProfile(BaseModel):
    name: str
    inferred_type: Literal["empty", "decimal", "boolean", "date", "text"]
    missing: int
    distinct: int
    top_values: list[Frequency]
    minimum: str | None = None
    maximum: str | None = None
    mean: str | None = None
    outliers: int | None = None


class DataProfile(BaseModel):
    database_source: dict[str, Any] | None = None
    rows: int
    columns: list[ColumnProfile]
    missing_cells: int
    duplicate_rows: int
    completeness_percent: str
    sample: list[list[str]]
    profiling_version: str = "csv-profile-1"
    pipeline_version: str = "csv-transform-1"
    statistics_note: str = ""
    import_info: CsvImportInfo | None = None
    source_worksheet: int | None = None
    source_table: str | None = None
    source_format: Literal["csv", "json", "jsonl", "xlsx", "parquet", "sqlite"] = "csv"


class VersionView(BaseModel):
    version_no: int
    source_version: int | None
    job_id: UUID
    content_hash: str
    profile: DataProfile
    steps: list[Step]
    created_at: datetime
    created_by_user_id: UUID


class JobView(BaseModel):
    id: UUID
    dataset_id: UUID
    kind: Literal["IMPORT", "PREVIEW"]
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"]
    progress: int = 0
    progress_message: str = ""
    processed_rows: int = 0
    import_options: ImportOptions | None = None
    source_version: int | None
    steps: list[Step]
    error: str | None
    profile: DataProfile | None
    result_hash: str | None
    created_at: datetime
    finished_at: datetime | None


class DatasetSummary(BaseModel):
    id: UUID
    name: str
    filename: str
    current_version: int
    created_at: datetime


class DatasetView(DatasetSummary):
    original_hash: str
    original_bytes: int
    delimiter: str
    versions: list[VersionView]
    jobs: list[JobView]


class UploadInput(ImportOptions):
    name: str = Field(min_length=1, max_length=160)
    filename: str = Field(
        min_length=1,
        max_length=160,
        pattern=r"^[^/\\\x00-\x1f]+\.(?i:csv|json|jsonl|xlsx|parquet|sqlite|sqlite3|db)$",
    )
    total_bytes: int = Field(ge=1, le=1073741824)


class UploadView(BaseModel):
    table_name: str | None = None
    worksheet: int = 1
    encoding: str = "auto"
    has_header: bool = True
    name: str = ""
    filename: str = ""
    delimiter: str = ";"
    id: UUID
    status: Literal["OPEN", "SEALED", "CANCELLED"]
    expected_bytes: int
    received_bytes: int
    chunk_count: int
    chunk_bytes: int = 4194304


class ChartRow(BaseModel):
    row_number: int
    values: list[str]


class ChartSample(BaseModel):
    version_no: int
    content_hash: str
    total_rows: int
    columns: list[str]
    rows: list[ChartRow]
    method: Literal["complete", "systematic-chunks-v1"]
    truncated_cells: int = 0
