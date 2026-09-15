"""Kurze Claims und erneuerbare Leases für lange CSV-Verarbeitung."""

import hashlib
import os
import shutil
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from typing import Literal, cast
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select, text

from platform_app.data.chunks import (
    CHUNK_BYTES,
    append_chunk,
    blob_info,
    cancel_object,
    iter_object,
    new_object,
    object_for,
    seal_blob,
)
from platform_app.data.engine import DataError
from platform_app.data.models import DataBlob, DataJob
from platform_app.data.schemas import CsvImportInfo, ImportOptions, Step
from platform_app.data.service import create_version, dataset_for, version_for
from platform_app.data.stream_engine import build
from platform_app.identity.dependencies import ActorContext
from platform_app.intake.models import now
from platform_app.shared.audit import append_audit
from platform_app.shared.authorization import check_write
from platform_app.shared.db import tenant_session


class LeaseLost(Exception):
    pass


def process_stream_job(org: UUID) -> bool:
    with tenant_session(org) as db:
        # Gleiche Sperrreihenfolge wie Rechteänderung und Publikation.
        if not db.execute(
            text("SELECT id FROM organizations WHERE id=:id FOR UPDATE SKIP LOCKED"), {"id": org}
        ).first():
            return False
        job = db.scalar(
            select(DataJob)
            .where(
                DataJob.processing_mode == "STREAM",
                (DataJob.status == "QUEUED")
                | ((DataJob.status == "RUNNING") & (DataJob.lease_until < now())),
            )
            .order_by(DataJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return False
        job_id, dataset_id, token = job.id, job.dataset_id, uuid4()
        actor = ActorContext(job.created_by_user_id, org, frozenset(), "Datenauftrag")
        if job.attempts >= 3:
            job.status, job.error, job.finished_at = (
                "FAILED",
                "Drei Verarbeitungsversuche wurden unterbrochen. Bitte einen neuen Auftrag erstellen.",
                now(),
            )
            append_audit(
                db, actor, "data.job.failed", "dataset", dataset_id, {"job_id": str(job_id)}
            )
            return True
        job.status, job.lease_token, job.lease_until = (
            "RUNNING",
            token,
            now() + timedelta(seconds=90),
        )
        job.attempts += 1
        job.progress, job.progress_message = 1, "Verarbeitung wurde übernommen"
        steps = [Step.model_validate(s) for s in job.steps]
        dataset = dataset_for(db, dataset_id)
        source_id = (
            dataset.original_blob_id
            if job.kind == "IMPORT"
            else version_for(db, dataset_id, job.source_version or 0).blob_id
        )
        source_blob = db.get(DataBlob, source_id)
        assert source_blob is not None
        source_format = cast(
            Literal["csv", "json", "jsonl", "xlsx", "parquet", "sqlite"],
            source_blob.storage_meta.get("format", "csv")
            if job.kind == "IMPORT"
            else version_for(db, dataset_id, job.source_version or 0).profile.get(
                "source_format", "csv"
            ),
        )
        if source_format not in {"csv", "json", "jsonl", "xlsx", "parquet", "sqlite"}:
            source_format = "csv"
        source_hash = source_blob.content_hash
        database_source = (
            source_blob.storage_meta.get("database_source")
            if job.kind == "IMPORT"
            else version_for(db, dataset_id, job.source_version or 0).profile.get("database_source")
        )
        source_object_id = source_blob.object_id
        inline_source = source_blob.content
        source_count = 0
        source_size = len(inline_source or b"")
        if source_object_id:
            _, source_obj = blob_info(db, source_id)
            source_count, source_size = source_obj["chunk_count"], source_obj["received_bytes"]
        delimiter, is_jsonl = dataset.delimiter, job.kind == "PREVIEW"
        csv_options = (
            ImportOptions.model_validate(job.import_options)
            if job.import_options
            else ImportOptions.model_validate({"delimiter": delimiter, "encoding": "utf-8-sig"})
        )
        original_worksheet = None
        original_table = None
        original_import_info = None
        if is_jsonl:
            original_table = version_for(db, dataset_id, job.source_version or 0).profile.get(
                "source_table"
            )
            original_worksheet = version_for(db, dataset_id, job.source_version or 0).profile.get(
                "source_worksheet"
            )
            original_import_info = version_for(db, dataset_id, job.source_version or 0).profile.get(
                "import_info"
            )
    last_heartbeat = 0.0
    last_progress = 1
    last_message = "Verarbeitung wurde übernommen"
    last_rows = 0
    staged: list[UUID] = []

    def heartbeat(percent: int, message: str, rows: int, *, force: bool = False) -> None:
        nonlocal last_heartbeat, last_progress, last_message, last_rows
        if percent >= 0:
            last_progress, last_message = max(last_progress, percent), message
        last_rows = max(last_rows, rows)
        if not force and time.monotonic() - last_heartbeat < 2:
            return
        with tenant_session(org) as db:
            check_write(db, actor)
            current = db.scalar(select(DataJob).where(DataJob.id == job_id).with_for_update())
            if (
                current is None
                or current.status != "RUNNING"
                or current.lease_token != token
                or current.lease_until is None
                or current.lease_until < now()
            ):
                raise LeaseLost
            current.lease_until = now() + timedelta(seconds=90)
            current.progress, current.progress_message = last_progress, last_message
            current.processed_rows = max(current.processed_rows, last_rows)
        last_heartbeat = time.monotonic()

    def save(path: Path, *, indexed: bool) -> tuple[UUID, str]:
        heartbeat(80, "Ergebnis wird abschnittsweise gespeichert", 0, force=True)
        with tenant_session(org) as db:
            check_write(db, actor)
            oid = new_object(
                db, actor, "DERIVED", metadata={"job_id": str(job_id), "lease_token": str(token)}
            )
        staged.append(oid)
        result_hash = hashlib.sha256()
        ordinal, row_start = 0, 0
        with path.open("rb") as stream:
            if indexed:
                buffer = bytearray()
                row_count = 0
                for line in stream:
                    if buffer and len(buffer) + len(line) > CHUNK_BYTES:
                        heartbeat(85, "Datenversion wird gespeichert", row_start)
                        data = bytes(buffer)
                        append_chunk(actor, oid, ordinal, data, row_start, row_count)
                        result_hash.update(data)
                        ordinal, row_start = ordinal + 1, row_start + row_count
                        buffer, row_count = bytearray(), 0
                    buffer.extend(line)
                    row_count += 1
                if buffer:
                    data = bytes(buffer)
                    append_chunk(actor, oid, ordinal, data, row_start, row_count)
                    result_hash.update(data)
            else:
                while data := stream.read(CHUNK_BYTES):
                    heartbeat(90, "Sicherer Export wird gespeichert", 0)
                    append_chunk(actor, oid, ordinal, data)
                    result_hash.update(data)
                    ordinal += 1
        return oid, result_hash.hexdigest()

    try:
        heartbeat(2, "Originaldatei wird gelesen und geprüft", 0, force=True)
        work_root = Path(os.environ.get("DATA_WORK_DIRECTORY", tempfile.gettempdir()))
        if shutil.disk_usage(work_root).free < source_size * 6 + 256 * 1024 * 1024:
            raise DataError(
                "Für die Verarbeitung fehlt temporärer Speicherplatz. Bitte mindestens das Sechsfache der Dateigröße plus 256 MiB bereitstellen."
            )
        with tempfile.TemporaryDirectory(prefix=f"csv-{job_id}-", dir=work_root) as folder:
            directory = Path(folder)
            source = directory / "source"
            source_digest = hashlib.sha256()
            read_bytes = 0
            with source.open("wb") as output:
                chunks = (
                    iter_object(org, source_object_id, source_count)
                    if source_object_id
                    else iter([inline_source or b""])
                )
                for chunk in chunks:
                    output.write(chunk)
                    source_digest.update(chunk)
                    read_bytes += len(chunk)
                    heartbeat(
                        2 + int(23 * read_bytes / max(1, source_size)),
                        "Originaldatei wird gelesen und geprüft",
                        0,
                    )
            if source_digest.hexdigest() != source_hash:
                raise DataError(
                    "Die Integritätsprüfung der gesamten Quelldatei ist fehlgeschlagen."
                )
            normalized, exported, profile, protected = build(
                source,
                directory,
                delimiter,
                is_jsonl,
                steps,
                heartbeat,
                csv_options=csv_options,
                source_format=source_format,
            )
            if is_jsonl:
                profile.source_worksheet = original_worksheet
                profile.source_table = original_table
            if original_import_info:
                profile.import_info = CsvImportInfo.model_validate(original_import_info)
            profile.database_source = database_source
            result_oid, result_hash = save(normalized, indexed=True)
            export_oid, export_hash = save(exported, indexed=False)
            heartbeat(99, "Ergebnis wird atomar veröffentlicht", profile.rows, force=True)
            with tenant_session(org) as db:
                check_write(db, actor)
                current = db.scalar(select(DataJob).where(DataJob.id == job_id).with_for_update())
                if (
                    current is None
                    or current.status != "RUNNING"
                    or current.lease_token != token
                    or current.lease_until is None
                    or current.lease_until < now()
                ):
                    raise LeaseLost
                export_blob = seal_blob(db, actor, export_oid, export_hash, {"format": "safe-csv"})
                result_blob = seal_blob(
                    db,
                    actor,
                    result_oid,
                    result_hash,
                    {
                        "format": "jsonl",
                        "columns": [c.name for c in profile.columns],
                        "export_blob_id": str(export_blob.id),
                        "export_hash": export_hash,
                        "export_bytes": exported.stat().st_size,
                        "protected_cells": protected,
                    },
                )
                current.result_blob_id, current.result_hash = result_blob.id, result_hash
                current.profile = profile.model_dump(mode="json")
                current.status, current.finished_at = "SUCCEEDED", now()
                current.progress, current.progress_message, current.processed_rows = (
                    100,
                    "Verarbeitung abgeschlossen",
                    profile.rows,
                )
                db.flush()
                if current.kind == "IMPORT":
                    create_version(db, dataset_for(db, dataset_id, lock=True), current, actor)
                else:
                    append_audit(
                        db,
                        actor,
                        "data.preview.ready",
                        "dataset",
                        dataset_id,
                        {"job_id": str(job_id), "result_hash": result_hash},
                    )
    except LeaseLost:
        pass
    except (DataError, HTTPException) as error:
        with tenant_session(org) as db:
            current = db.scalar(select(DataJob).where(DataJob.id == job_id).with_for_update())
            if current is not None and current.status == "RUNNING" and current.lease_token == token:
                current.status, current.finished_at = "FAILED", now()
                current.error = (
                    str(error)[:300]
                    if isinstance(error, DataError)
                    else "Verarbeitung abgebrochen: Quelle, Speicher oder Schreibberechtigung nicht mehr verfügbar."
                )
                append_audit(
                    db, actor, "data.job.failed", "dataset", dataset_id, {"job_id": str(job_id)}
                )
    finally:
        # Nur unveröffentlichte Abschnitte dieses Versuchs werden entfernt.
        for oid in staged:
            with tenant_session(org) as db:
                obj = object_for(db, oid, lock=True)
                if obj["status"] == "OPEN":
                    cancel_object(db, oid)
    return True
