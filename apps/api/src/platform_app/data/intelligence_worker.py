"""Leased Analyse-/Quellenaufträge; alte Datenworker behalten ihre innere Netzgrenze."""

import hashlib
import logging
import os
import shutil
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select, text

from platform_app.data.analytics import analyze
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
from platform_app.data.engine import DataError, decode_table
from platform_app.data.intelligence_models import DataTask
from platform_app.data.intelligence_schemas import AnalysisInput, SourceImportInput
from platform_app.data.models import DataBlob, DataJob, Dataset
from platform_app.data.postgres_source import snapshot, source_for
from platform_app.data.schemas import DataProfile, ImportOptions
from platform_app.data.service import check_dataset_quota, check_quota, dataset_for, version_for
from platform_app.data.stream_engine import encode_row
from platform_app.data.stream_worker import LeaseLost
from platform_app.decisions.engine import fingerprint
from platform_app.identity.dependencies import ActorContext
from platform_app.intake.models import now
from platform_app.shared.audit import append_audit
from platform_app.shared.authorization import check_write
from platform_app.shared.config import AppSettings
from platform_app.shared.db import tenant_session


def process_task(org: UUID) -> bool:
    # Derselbe zentrale Default; der Quellenworker benötigt dafür keine OIDC-Geheimnisse.
    dataset_limit = int(
        os.environ.get("DATASET_LIMIT_PER_ORGANIZATION")
        or AppSettings.model_fields["dataset_limit_per_organization"].default
    )
    with tenant_session(org) as db:
        if not db.execute(
            text("SELECT id FROM organizations WHERE id=:id FOR UPDATE SKIP LOCKED"), {"id": org}
        ).first():
            return False
        task = db.scalar(
            select(DataTask)
            .where(
                (DataTask.status == "QUEUED")
                | ((DataTask.status == "RUNNING") & (DataTask.lease_until < now()))
            )
            .order_by(DataTask.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if task is None:
            return False
        actor = ActorContext(task.created_by_user_id, org, frozenset(), "Datenanalyseauftrag")
        task_id, token, kind, request, dataset_id, version_no = (
            task.id,
            uuid4(),
            task.kind,
            task.request,
            task.dataset_id,
            task.version_no,
        )
        if task.attempts >= 3 or kind == "PLAN":
            task.status, task.finished_at, task.error = (
                "FAILED",
                now(),
                "Auftrag unterbrochen. KI-Ausgänge werden nicht automatisch wiederholt; bitte einen neuen Auftrag bewusst starten.",
            )
            append_audit(
                db,
                actor,
                "data.task.failed",
                "data_task",
                task_id,
                {"reason": "attempts_or_uncertain_provider"},
            )
            return True
        task.status, task.lease_token, task.lease_until = (
            "RUNNING",
            token,
            now() + timedelta(seconds=90),
        )
        task.attempts += 1
        task.progress, task.message = 1, "Auftrag wird verarbeitet"
        # Verwaiste Abschnitte ausschließlich dieses Auftrags freigeben.
        for oid in db.scalars(
            text("SELECT id FROM data_objects WHERE status='OPEN' AND metadata->>'task_id'=:task"),
            {"task": str(task_id)},
        ):
            cancel_object(db, oid)
    last_heartbeat = 0.0
    started = time.monotonic()
    staged: UUID | None = None

    def heartbeat(percent: int, message: str, *, force: bool = False) -> None:
        nonlocal last_heartbeat
        if time.monotonic() - started > 1800:
            raise DataError(
                "Der Auftrag überschreitet 30 Minuten. Weniger Analysespalten/Regeln oder eine kleinere Quelltabelle wählen."
            )
        if not force and time.monotonic() - last_heartbeat < 2:
            return
        with tenant_session(org) as db:
            check_write(db, actor)
            current = db.scalar(select(DataTask).where(DataTask.id == task_id).with_for_update())
            if (
                current is None
                or current.status != "RUNNING"
                or current.lease_token != token
                or current.lease_until is None
                or current.lease_until < now()
            ):
                raise LeaseLost
            current.lease_until = now() + timedelta(seconds=90)
            current.progress = max(current.progress, percent)
            current.message = message[:160]
        last_heartbeat = time.monotonic()

    try:
        heartbeat(2, "Rechte und Quelle werden geprüft", force=True)
        work_root = Path(os.environ.get("DATA_WORK_DIRECTORY", tempfile.gettempdir()))
        with tempfile.TemporaryDirectory(prefix=f"data-task-{task_id}-", dir=work_root) as folder:
            directory, result = Path(folder), {}
            source = directory / "source"
            metadata = None
            source_options = None
            if kind == "ANALYSIS":
                assert dataset_id is not None and version_no is not None
                options = AnalysisInput.model_validate(request["analysis"])
                with tenant_session(org) as db:
                    check_write(db, actor)
                    version = version_for(db, dataset_id, version_no)
                    profile = DataProfile.model_validate(version.profile)
                    content_hash = version.content_hash
                    original_hash = dataset_for(db, dataset_id).original_hash
                    blob = db.get(DataBlob, version.blob_id)
                    assert blob is not None
                    object_id, inline = blob.object_id, blob.content
                    _, info = blob_info(db, version.blob_id) if object_id else (None, {})
                    size = info.get("received_bytes", len(inline or b""))
                    count = info.get("chunk_count", 0)
                if shutil.disk_usage(work_root).free < size * 6 + 256 * 1024**2:
                    raise DataError(
                        "Für die Analyse fehlt temporärer Speicher: mindestens sechsfache Quelldateigröße plus 256 MiB bereitstellen."
                    )
                digest = hashlib.sha256()
                with source.open("wb") as output:
                    for block in (
                        iter_object(org, object_id, count) if object_id else [inline or b""]
                    ):
                        output.write(block)
                        digest.update(block)
                        heartbeat(10, "Version wird gelesen und gehasht")
                if digest.hexdigest() != content_hash:
                    raise DataError("Die Prüfsumme der Analysequelle stimmt nicht.")
                if object_id is None:
                    table = decode_table(inline or b"")
                    with source.open("w", encoding="utf8", newline="\n") as normalized:
                        normalized.write(encode_row(table.columns) + "\n")
                        for row in table.rows:
                            normalized.write(encode_row(row) + "\n")
                result = analyze(source, directory, profile, options, heartbeat)
                result["ruleset"] = request.get("ruleset")
                result.update(
                    {
                        "dataset_id": str(dataset_id),
                        "version_no": version_no,
                        "content_hash": content_hash,
                        "original_hash": original_hash,
                    }
                )
            elif kind == "SOURCE":
                source_options = SourceImportInput.model_validate(request)
                config = source_for(org, source_options.source_id, source_options.table)
                if shutil.disk_usage(work_root).free < 1280 * 1024**2:
                    raise DataError(
                        "Für den Datenbanksnapshot müssen mindestens 1,25 GiB Arbeitsvolumen frei sein."
                    )
                metadata = snapshot(config, source_options.table, source, heartbeat)
                heartbeat(75, "Snapshot wird als unveränderliches Original gespeichert", force=True)
                with tenant_session(org) as db:
                    check_write(db, actor)
                    check_dataset_quota(db, configured_limit=dataset_limit)
                    staged = new_object(
                        db,
                        actor,
                        "DERIVED",
                        metadata={"task_id": str(task_id), "lease_token": str(token)},
                    )
                digest = hashlib.sha256()
                with source.open("rb") as stream:
                    ordinal = 0
                    while block := stream.read(CHUNK_BYTES):
                        heartbeat(80, "Snapshotabschnitte werden gespeichert")
                        append_chunk(actor, staged, ordinal, block)
                        digest.update(block)
                        ordinal += 1
                content_hash = digest.hexdigest()
            else:
                raise DataError("Unbekannter Datenauftrag.")
            heartbeat(95, "Ergebnis wird atomar veröffentlicht", force=True)
            with tenant_session(org) as db:
                check_write(db, actor)
                current = db.scalar(
                    select(DataTask).where(DataTask.id == task_id).with_for_update()
                )
                if (
                    current is None
                    or current.status != "RUNNING"
                    or current.lease_token != token
                    or current.lease_until is None
                    or current.lease_until < now()
                ):
                    raise LeaseLost
                if kind == "SOURCE":
                    assert (
                        staged is not None and source_options is not None and metadata is not None
                    )
                    # Konfiguration/Organisation kann während des Transfers widerrufen worden sein.
                    if source_for(org, source_options.source_id, source_options.table) != config:
                        raise DataError(
                            "Die Quellenkonfiguration wurde während des Imports geändert. Bitte einen neuen Auftrag starten."
                        )
                    check_dataset_quota(db, configured_limit=dataset_limit)
                    check_quota(db)
                    blob = seal_blob(
                        db,
                        actor,
                        staged,
                        content_hash,
                        {"format": "csv", "database_source": metadata},
                    )
                    dataset = Dataset(
                        organization_id=org,
                        created_by_user_id=actor.user_id,
                        name=source_options.name,
                        filename="postgres-snapshot.csv",
                        delimiter=",",
                        original_blob_id=blob.id,
                        original_hash=content_hash,
                        original_bytes=source.stat().st_size,
                    )
                    db.add(dataset)
                    db.flush()
                    job = DataJob(
                        organization_id=org,
                        created_by_user_id=actor.user_id,
                        dataset_id=dataset.id,
                        kind="IMPORT",
                        processing_mode="STREAM",
                        import_options=ImportOptions(
                            delimiter=",", encoding="utf-8-sig"
                        ).model_dump(),
                    )
                    db.add(job)
                    db.flush()
                    result = {
                        "dataset_id": str(dataset.id),
                        "job_id": str(job.id),
                        "original_hash": content_hash,
                        "source": metadata,
                    }
                    append_audit(
                        db,
                        actor,
                        "data.import.queued",
                        "dataset",
                        dataset.id,
                        {
                            "source_task_id": str(task_id),
                            "job_id": str(job.id),
                            "original_hash": content_hash,
                        },
                    )
                current.result = result
                current.result_hash = fingerprint(result)
                current.status, current.progress, current.finished_at, current.message = (
                    "SUCCEEDED",
                    100,
                    now(),
                    "Auftrag abgeschlossen",
                )
                append_audit(
                    db,
                    actor,
                    "data.task.finished",
                    "data_task",
                    task_id,
                    {"kind": kind, "result_hash": current.result_hash},
                )
    except LeaseLost:
        pass
    except (DataError, HTTPException, OSError, ValueError) as error:
        with tenant_session(org) as db:
            current = db.scalar(select(DataTask).where(DataTask.id == task_id).with_for_update())
            if current is not None and current.status == "RUNNING" and current.lease_token == token:
                current.status, current.finished_at = "FAILED", now()
                current.error = (
                    str(error)[:300]
                    if isinstance(error, DataError)
                    else "Auftrag abgebrochen: Quelle, Struktur, Speicher oder Schreibrecht nicht verfügbar."
                )
                append_audit(db, actor, "data.task.failed", "data_task", task_id, {"kind": kind})
    finally:
        if staged:
            with tenant_session(org) as db:
                if object_for(db, staged, lock=True)["status"] == "OPEN":
                    cancel_object(db, staged)
    return True


def main() -> None:
    organizations = [
        UUID(v.strip())
        for v in os.environ.get("DATA_WORKER_ORGANIZATION_IDS", "").split(",")
        if v.strip()
    ]
    if not organizations:
        raise RuntimeError("Der Analyseworker benötigt explizite Organisationen.")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    while True:
        processed = False
        for org in organizations:
            try:
                processed = process_task(org) or processed
            except Exception as error:
                logging.error("data_task_worker_retry:%s", type(error).__name__)
                time.sleep(2)
        if not processed:
            time.sleep(1)


if __name__ == "__main__":
    main()
