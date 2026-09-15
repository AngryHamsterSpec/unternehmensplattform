"""Fortsetzbarer CSV-Upload: kleine Requests, Prüfsumme und atomare Veröffentlichung."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from starlette.concurrency import run_in_threadpool

from platform_app.contracts import Page
from platform_app.data.chunks import (
    append_chunk,
    cancel_object,
    hash_object,
    new_object,
    object_for,
    seal_blob,
)
from platform_app.data.models import DataBlob, DataJob, Dataset
from platform_app.data.schemas import ImportOptions, JobView, UploadInput, UploadView
from platform_app.data.service import check_dataset_quota, check_quota, job_view
from platform_app.identity.dependencies import ActorContext, require_write
from platform_app.shared.audit import append_audit
from platform_app.shared.authorization import check_write
from platform_app.shared.db import tenant_session

router = APIRouter(prefix="/api/v1/data-uploads", tags=["Datenintelligenz"])


def upload_view(obj: dict[str, Any]) -> UploadView:
    metadata = obj["metadata"]
    return UploadView.model_validate(
        {
            **obj,
            "name": metadata.get("name", ""),
            "filename": metadata.get("filename", ""),
            "delimiter": metadata.get("delimiter", ";"),
            "encoding": metadata.get("encoding", "auto"),
            "has_header": metadata.get("has_header", True),
            "worksheet": metadata.get("worksheet", 1),
            "table_name": metadata.get("table_name"),
        }
    )


@router.get("", response_model=Page[UploadView])
def pending_uploads(actor: ActorContext = Depends(require_write)) -> Page[UploadView]:
    with tenant_session(actor.organization_id) as db:
        rows = db.execute(
            text(
                "SELECT * FROM data_objects WHERE kind='UPLOAD' AND status='OPEN' ORDER BY created_at LIMIT 3"
            )
        ).mappings()
        return Page(items=[upload_view(dict(row)) for row in rows])


@router.post("", status_code=201, response_model=UploadView)
def start(payload: UploadInput, actor: ActorContext = Depends(require_write)) -> UploadView:
    if not payload.name.strip():
        raise HTTPException(422, "Bitte einen Datensatznamen angeben.")
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        check_quota(db)
        active = (
            db.scalar(
                text("SELECT count(*) FROM data_objects WHERE kind='UPLOAD' AND status='OPEN'")
            )
            or 0
        )
        if active >= 3:
            raise HTTPException(
                409, "Bitte einen der drei offenen Uploads fortsetzen oder abbrechen."
            )
        check_dataset_quota(db)
        oid = new_object(db, actor, "UPLOAD", payload.total_bytes, payload.model_dump(mode="json"))
        append_audit(
            db, actor, "data.upload.started", "data_object", oid, {"bytes": payload.total_bytes}
        )
        return upload_view(object_for(db, oid))


@router.get("/{upload_id}", response_model=UploadView)
def status(upload_id: UUID, actor: ActorContext = Depends(require_write)) -> UploadView:
    with tenant_session(actor.organization_id) as db:
        return upload_view(object_for(db, upload_id))


@router.put("/{upload_id}/chunks/{ordinal}", response_model=UploadView)
async def chunk(
    upload_id: UUID, ordinal: int, request: Request, actor: ActorContext = Depends(require_write)
) -> UploadView:
    content = await request.body()
    result = await run_in_threadpool(append_chunk, actor, upload_id, ordinal, content)
    return upload_view(result)


@router.post("/{upload_id}/cancel", response_model=UploadView)
def cancel(upload_id: UUID, actor: ActorContext = Depends(require_write)) -> UploadView:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        cancel_object(db, upload_id)
        append_audit(db, actor, "data.upload.cancelled", "data_object", upload_id, {})
        return upload_view(object_for(db, upload_id))


@router.post("/{upload_id}/complete", status_code=202, response_model=JobView)
def complete(upload_id: UUID, actor: ActorContext = Depends(require_write)) -> JobView:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        obj = object_for(db, upload_id)
        if obj["status"] == "SEALED":
            existing = db.scalar(
                select(DataJob)
                .join(Dataset, Dataset.id == DataJob.dataset_id)
                .join(DataBlob, DataBlob.id == Dataset.original_blob_id)
                .where(DataBlob.object_id == upload_id, DataJob.kind == "IMPORT")
                .order_by(DataJob.created_at, DataJob.id)
                .limit(1)
            )
            if existing:
                return job_view(existing)
        if obj["status"] != "OPEN" or obj["received_bytes"] != obj["expected_bytes"]:
            raise HTTPException(409, "Die Datei wurde noch nicht vollständig hochgeladen.")
    # Keine offene Schreibtransaktion während des begrenzten Lesens der Gesamtdatei.
    content_hash = hash_object(actor.organization_id, upload_id, obj["chunk_count"])
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        current = object_for(db, upload_id, lock=True)
        if current["status"] == "SEALED":
            existing = db.scalar(
                select(DataJob)
                .join(Dataset, Dataset.id == DataJob.dataset_id)
                .join(DataBlob, DataBlob.id == Dataset.original_blob_id)
                .where(DataBlob.object_id == upload_id, DataJob.kind == "IMPORT")
                .order_by(DataJob.created_at, DataJob.id)
                .limit(1)
            )
            if existing:
                return job_view(existing)
        check_quota(db)
        check_dataset_quota(db)
        meta = obj["metadata"]
        source_format = meta["filename"].rsplit(".", 1)[-1].lower()
        if source_format in {"sqlite3", "db"}:
            source_format = "sqlite"
        blob = seal_blob(db, actor, upload_id, content_hash, {"format": source_format})
        dataset = Dataset(
            organization_id=actor.organization_id,
            created_by_user_id=actor.user_id,
            name=meta["name"].strip(),
            filename=meta["filename"],
            delimiter=meta["delimiter"],
            original_blob_id=blob.id,
            original_hash=content_hash,
            original_bytes=obj["received_bytes"],
        )
        db.add(dataset)
        db.flush()
        job = DataJob(
            organization_id=actor.organization_id,
            dataset_id=dataset.id,
            created_by_user_id=actor.user_id,
            kind="IMPORT",
            processing_mode="STREAM",
            import_options=ImportOptions(
                delimiter=meta["delimiter"],
                encoding=meta.get("encoding", "auto"),
                has_header=meta.get("has_header", True),
                worksheet=meta.get("worksheet", 1),
                table_name=meta.get("table_name"),
            ).model_dump(),
        )
        db.add(job)
        db.flush()
        append_audit(
            db,
            actor,
            "data.import.queued",
            "dataset",
            dataset.id,
            {"job_id": str(job.id), "original_hash": content_hash, "bytes": obj["received_bytes"]},
        )
        return job_view(job)
