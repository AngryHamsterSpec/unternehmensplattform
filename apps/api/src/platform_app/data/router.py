"""Mandantengebundene CSV-API; Downloads referenzieren ausschließlich gespeicherte Stände."""

import base64
import binascii
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select, text

from platform_app.contracts import Page
from platform_app.data.chunks import blob_info, iter_object
from platform_app.data.engine import MAX_BYTES, DataError, decode_table, digest, safe_export
from platform_app.data.models import DataBlob, DataJob, Dataset, DataVersion
from platform_app.data.schemas import (
    ChartSample,
    CommitInput,
    DatasetSummary,
    DatasetView,
    ImportInput,
    ImportOptions,
    JobView,
    PreviewInput,
    VersionView,
)
from platform_app.data.service import (
    check_dataset_quota,
    check_quota,
    commit_preview,
    dataset_for,
    job_view,
    version_for,
    version_view,
)
from platform_app.data.storage import PostgresBlobStore
from platform_app.data.visualization import chart_sample
from platform_app.identity.dependencies import ActorContext, get_actor, require_write
from platform_app.intake.models import now
from platform_app.shared.audit import append_audit
from platform_app.shared.authorization import check_write
from platform_app.shared.db import tenant_session

router = APIRouter(prefix="/api/v1/datasets", tags=["Datenintelligenz"])


@router.post("", status_code=202, response_model=JobView)
def upload(payload: ImportInput, actor: ActorContext = Depends(require_write)) -> JobView:
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, "Die Dateikodierung ist ungültig.") from None
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(413, "Die Datei muss zwischen 1 Byte und 128 KiB groß sein.")
    if not payload.name.strip():
        raise HTTPException(422, "Bitte einen Datensatznamen angeben.")
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        check_quota(db)
        check_dataset_quota(db)
        blob, content_hash = PostgresBlobStore(db, actor.organization_id).put(content)
        dataset = Dataset(
            organization_id=actor.organization_id,
            created_by_user_id=actor.user_id,
            name=payload.name.strip(),
            filename=payload.filename,
            delimiter=payload.delimiter,
            original_blob_id=blob,
            original_hash=content_hash,
            original_bytes=len(content),
        )
        db.add(dataset)
        db.flush()
        job = DataJob(
            organization_id=actor.organization_id,
            dataset_id=dataset.id,
            created_by_user_id=actor.user_id,
            kind="IMPORT",
        )
        db.add(job)
        db.flush()
        append_audit(
            db,
            actor,
            "data.import.queued",
            "dataset",
            dataset.id,
            {"job_id": str(job.id), "original_hash": content_hash, "bytes": len(content)},
        )
        return job_view(job)


@router.get("", response_model=Page[DatasetSummary])
def list_datasets(actor: ActorContext = Depends(get_actor)) -> Page[DatasetSummary]:
    with tenant_session(actor.organization_id) as db:
        rows = db.scalars(
            select(Dataset).order_by(Dataset.created_at.desc(), Dataset.id.desc()).limit(100)
        ).all()
        return Page(items=[DatasetSummary.model_validate(v, from_attributes=True) for v in rows])


@router.get("/{dataset_id}", response_model=DatasetView)
def detail(dataset_id: UUID, actor: ActorContext = Depends(get_actor)) -> DatasetView:
    with tenant_session(actor.organization_id) as db:
        # Veröffentlichung und Kopfstand bleiben während dieses Abrufs konsistent.
        dataset = dataset_for(db, dataset_id, read_lock=True)
        versions = db.scalars(
            select(DataVersion)
            .where(DataVersion.dataset_id == dataset_id)
            .order_by(DataVersion.version_no.desc())
        ).all()
        jobs = db.scalars(
            select(DataJob)
            .where(DataJob.dataset_id == dataset_id)
            .order_by(DataJob.created_at.desc(), DataJob.id.desc())
            .limit(50)
        ).all()
        return DatasetView(
            **DatasetSummary.model_validate(dataset, from_attributes=True).model_dump(),
            original_hash=dataset.original_hash,
            original_bytes=dataset.original_bytes,
            delimiter=dataset.delimiter,
            versions=[version_view(v) for v in versions],
            jobs=[job_view(j) for j in jobs],
        )


@router.get("/{dataset_id}/jobs/{job_id}", response_model=JobView)
def get_job(dataset_id: UUID, job_id: UUID, actor: ActorContext = Depends(get_actor)) -> JobView:
    with tenant_session(actor.organization_id) as db:
        job = db.scalar(
            select(DataJob).where(DataJob.id == job_id, DataJob.dataset_id == dataset_id)
        )
        if job is None:
            raise HTTPException(404, "Der Datenauftrag wurde nicht gefunden.")
        return job_view(job)


@router.post("/{dataset_id}/previews", status_code=202, response_model=JobView)
def preview(
    dataset_id: UUID, payload: PreviewInput, actor: ActorContext = Depends(require_write)
) -> JobView:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        dataset_for(db, dataset_id)
        source = version_for(db, dataset_id, payload.source_version)
        source_blob = db.get(DataBlob, source.blob_id)
        mode = "STREAM" if source_blob and source_blob.object_id else "LEGACY"
        check_quota(db)
        job = DataJob(
            organization_id=actor.organization_id,
            dataset_id=dataset_id,
            created_by_user_id=actor.user_id,
            kind="PREVIEW",
            processing_mode=mode,
            source_version=payload.source_version,
            steps=[s.model_dump() for s in payload.steps],
        )
        db.add(job)
        db.flush()
        append_audit(
            db,
            actor,
            "data.preview.queued",
            "dataset",
            dataset_id,
            {
                "job_id": str(job.id),
                "source_version": payload.source_version,
                "steps": len(payload.steps),
            },
        )
        return job_view(job)


@router.post("/{dataset_id}/versions", status_code=201, response_model=VersionView)
def commit(
    dataset_id: UUID, payload: CommitInput, actor: ActorContext = Depends(require_write)
) -> VersionView:
    with tenant_session(actor.organization_id) as db:
        return commit_preview(db, actor, dataset_id, payload)


@router.get("/{dataset_id}/versions/{version_no}/export")
def export_csv(
    dataset_id: UUID, version_no: int, actor: ActorContext = Depends(get_actor)
) -> Response:
    with tenant_session(actor.organization_id) as db:
        version = version_for(db, dataset_id, version_no)
        blob = db.get(DataBlob, version.blob_id)
        if blob is not None and blob.object_id is not None:
            export_blob, obj = blob_info(db, UUID(blob.storage_meta["export_blob_id"]))
            assert export_blob.object_id is not None
            append_audit(
                db,
                actor,
                "data.export.downloaded",
                "dataset",
                dataset_id,
                {
                    "version_no": version_no,
                    "export_hash": export_blob.content_hash,
                    "protected_cells": blob.storage_meta["protected_cells"],
                },
            )
            return StreamingResponse(
                iter_object(actor.organization_id, export_blob.object_id, obj["chunk_count"]),
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="datensatz-{dataset_id}-v{version_no}.csv"',
                    "Content-Length": str(obj["received_bytes"]),
                    "X-Content-SHA256": export_blob.content_hash,
                    "X-Protected-Cells": str(blob.storage_meta["protected_cells"]),
                    "X-Source-SHA256": version.content_hash,
                },
            )
        try:
            content, protected = safe_export(
                decode_table(PostgresBlobStore(db, actor.organization_id).get(version.blob_id))
            )
        except DataError:
            raise HTTPException(409, "Die Export-Integritätsprüfung ist fehlgeschlagen.") from None
        append_audit(
            db,
            actor,
            "data.export.downloaded",
            "dataset",
            dataset_id,
            {
                "version_no": version_no,
                "export_hash": digest(content),
                "protected_cells": protected,
            },
        )
        return Response(
            content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="datensatz-{dataset_id}-v{version_no}.csv"',
                "X-Content-SHA256": digest(content),
                "X-Protected-Cells": str(protected),
                "X-Source-SHA256": version.content_hash,
            },
        )


@router.get("/{dataset_id}/original")
def original(dataset_id: UUID, actor: ActorContext = Depends(get_actor)) -> Response:
    with tenant_session(actor.organization_id) as db:
        dataset = dataset_for(db, dataset_id)
        blob = db.get(DataBlob, dataset.original_blob_id)
        if blob is not None and blob.object_id is not None:
            _, obj = blob_info(db, blob.id)
            append_audit(
                db,
                actor,
                "data.original.downloaded",
                "dataset",
                dataset_id,
                {"original_hash": dataset.original_hash},
            )
            return StreamingResponse(
                iter_object(actor.organization_id, blob.object_id, obj["chunk_count"]),
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f'attachment; filename="original-{dataset_id}.{dataset.filename.rsplit(chr(46), 1)[-1]}.txt"',
                    "Content-Length": str(obj["received_bytes"]),
                    "X-Content-SHA256": dataset.original_hash,
                },
            )
        content = PostgresBlobStore(db, actor.organization_id).get(dataset.original_blob_id)
        append_audit(
            db,
            actor,
            "data.original.downloaded",
            "dataset",
            dataset_id,
            {"original_hash": dataset.original_hash},
        )
        return Response(
            content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="original-{dataset_id}.{dataset.filename.rsplit(chr(46), 1)[-1]}.txt"',
                "X-Content-SHA256": dataset.original_hash,
            },
        )


@router.get("/{dataset_id}/versions/{version_no}/rows")
def rows(
    dataset_id: UUID,
    version_no: int,
    offset: int = Query(0, ge=0, le=1073741824),
    actor: ActorContext = Depends(get_actor),
) -> dict[str, object]:
    with tenant_session(actor.organization_id) as db:
        version = version_for(db, dataset_id, version_no)
        blob = db.get(DataBlob, version.blob_id)
        if blob is not None and blob.object_id is not None:
            ordinals = db.execute(
                text(
                    "SELECT ordinal,row_start FROM data_chunks WHERE object_id=:id AND row_start < :end AND row_start+row_count > :start ORDER BY ordinal"
                ),
                {"id": blob.object_id, "start": offset + 1, "end": offset + 26},
            ).all()
            page = []
            for ordinal, row_start in ordinals:
                chunk = db.execute(
                    text(
                        "SELECT content,content_hash FROM data_chunks WHERE object_id=:id AND ordinal=:n"
                    ),
                    {"id": blob.object_id, "n": ordinal},
                ).one()
                content = bytes(chunk[0])
                if digest(content) != chunk[1]:
                    raise HTTPException(
                        409, "Die Integritätsprüfung des Speicherabschnitts ist fehlgeschlagen."
                    )
                for index, line in enumerate(content.splitlines()):
                    if offset + 1 <= row_start + index < offset + 26:
                        page.append([value[:512] for value in json.loads(line)])
            return {
                "columns": blob.storage_meta["columns"],
                "rows": page,
                "total": version.profile["rows"],
                "offset": offset,
            }
        table = decode_table(PostgresBlobStore(db, actor.organization_id).get(version.blob_id))
        return {
            "columns": table.columns,
            "rows": table.rows[offset : offset + 25],
            "total": len(table.rows),
            "offset": offset,
        }


@router.get("/{dataset_id}/versions/{version_no}/export-info")
def export_info(
    dataset_id: UUID, version_no: int, actor: ActorContext = Depends(get_actor)
) -> dict[str, object]:
    with tenant_session(actor.organization_id) as db:
        version = version_for(db, dataset_id, version_no)
        blob = db.get(DataBlob, version.blob_id)
        if blob is not None and blob.object_id is not None:
            return {
                "content_hash": blob.storage_meta["export_hash"],
                "protected_cells": blob.storage_meta["protected_cells"],
            }
        content, protected = safe_export(
            decode_table(PostgresBlobStore(db, actor.organization_id).get(version.blob_id))
        )
        return {"content_hash": digest(content), "protected_cells": protected}


@router.post("/{dataset_id}/jobs/{job_id}/cancel", response_model=JobView)
def cancel_job(
    dataset_id: UUID, job_id: UUID, actor: ActorContext = Depends(require_write)
) -> JobView:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        job = db.scalar(
            select(DataJob)
            .where(DataJob.id == job_id, DataJob.dataset_id == dataset_id)
            .with_for_update()
        )
        if job is None:
            raise HTTPException(404, "Der Datenauftrag wurde nicht gefunden.")
        if job.status == "CANCELLED":
            return job_view(job)
        if job.status not in {"QUEUED", "RUNNING"}:
            raise HTTPException(409, "Dieser Auftrag ist bereits abgeschlossen.")
        job.status, job.finished_at, job.error = (
            "CANCELLED",
            now(),
            "Der Auftrag wurde durch ein schreibberechtigtes Mitglied abgebrochen.",
        )
        append_audit(
            db, actor, "data.job.cancelled", "dataset", dataset_id, {"job_id": str(job.id)}
        )
        db.flush()
        return job_view(job)


@router.get("/{dataset_id}/versions/{version_no}/chart-sample", response_model=ChartSample)
def visualization_sample(
    dataset_id: UUID,
    version_no: int,
    x: int = Query(0, ge=0, le=255),
    y: int = Query(0, ge=0, le=255),
    actor: ActorContext = Depends(get_actor),
) -> ChartSample:
    return chart_sample(actor, dataset_id, version_no, x, y)


@router.post("/{dataset_id}/retry-import", status_code=202, response_model=JobView)
def retry_import(
    dataset_id: UUID, payload: ImportOptions, actor: ActorContext = Depends(require_write)
) -> JobView:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        dataset = dataset_for(db, dataset_id, lock=True)
        if dataset.current_version:
            raise HTTPException(
                409,
                "Dieser Datensatz wurde bereits importiert. Bestehende Versionen bleiben unverändert.",
            )
        pending = db.scalar(
            select(DataJob)
            .where(
                DataJob.dataset_id == dataset_id,
                DataJob.kind == "IMPORT",
                DataJob.status.in_(["QUEUED", "RUNNING"]),
            )
            .limit(1)
        )
        options = payload.model_dump(mode="json")
        if pending:
            if ImportOptions.model_validate(pending.import_options).model_dump() == options:
                return job_view(pending)
            raise HTTPException(
                409,
                "Ein Import mit anderen Einstellungen läuft bereits. Bitte zuerst abschließen lassen oder abbrechen.",
            )
        check_quota(db)
        job = DataJob(
            organization_id=actor.organization_id,
            dataset_id=dataset_id,
            created_by_user_id=actor.user_id,
            kind="IMPORT",
            processing_mode="STREAM",
            import_options=options,
        )
        db.add(job)
        db.flush()
        append_audit(
            db,
            actor,
            "data.import.retried",
            "dataset",
            dataset_id,
            {"job_id": str(job.id), "original_hash": dataset.original_hash, "options": options},
        )
        return job_view(job)
