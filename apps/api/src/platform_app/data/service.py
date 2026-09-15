"""Atomare Verarbeitung, Rechteprüfung und versionierte Übernahme."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from platform_app.data.engine import (
    DataError,
    decode_table,
    encode_table,
    parse_csv,
    profile,
    transform,
)
from platform_app.data.models import DataJob, Dataset, DataVersion
from platform_app.data.schemas import (
    CommitInput,
    DataProfile,
    ImportOptions,
    JobView,
    Step,
    VersionView,
)
from platform_app.data.storage import BlobStore, PostgresBlobStore
from platform_app.identity.dependencies import ActorContext
from platform_app.intake.models import now
from platform_app.shared.audit import append_audit
from platform_app.shared.authorization import check_write
from platform_app.shared.config import get_settings
from platform_app.shared.db import tenant_session


def dataset_for(
    db: Session, dataset_id: UUID, *, lock: bool = False, read_lock: bool = False
) -> Dataset:
    query = select(Dataset).where(Dataset.id == dataset_id)
    dataset = db.scalar(query.with_for_update(read=read_lock) if lock or read_lock else query)
    if dataset is None:
        raise HTTPException(404, "Der Datensatz wurde nicht gefunden.")
    return dataset


def version_for(db: Session, dataset_id: UUID, version: int) -> DataVersion:
    value = db.scalar(
        select(DataVersion).where(
            DataVersion.dataset_id == dataset_id, DataVersion.version_no == version
        )
    )
    if value is None:
        raise HTTPException(404, "Die Datenversion wurde nicht gefunden.")
    return value


def job_view(job: DataJob) -> JobView:
    return JobView(
        id=job.id,
        dataset_id=job.dataset_id,
        kind=job.kind,
        import_options=ImportOptions.model_validate(job.import_options)
        if job.import_options
        else None,
        status=job.status,
        progress=job.progress,
        progress_message=job.progress_message,
        processed_rows=job.processed_rows,
        source_version=job.source_version,
        steps=[Step.model_validate(s) for s in job.steps],
        error=job.error,
        profile=DataProfile.model_validate(job.profile) if job.profile else None,
        result_hash=job.result_hash,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


def version_view(version: DataVersion) -> VersionView:
    return VersionView(
        version_no=version.version_no,
        source_version=version.source_version,
        job_id=version.job_id,
        content_hash=version.content_hash,
        profile=DataProfile.model_validate(version.profile),
        steps=[Step.model_validate(s) for s in version.steps],
        created_at=version.created_at,
        created_by_user_id=version.created_by_user_id,
    )


def check_dataset_quota(db: Session, *, configured_limit: int | None = None) -> None:
    """Limit the number of datasets visible in the current tenant session."""
    limit = (
        get_settings().dataset_limit_per_organization
        if configured_limit is None
        else configured_limit
    )
    if not 1 <= limit <= 100000:
        raise ValueError("Ungültige zentrale Dataset-Quote.")
    count = db.scalar(select(func.count()).select_from(Dataset)) or 0
    if count >= limit:
        raise HTTPException(
            409,
            f"Die konfigurierte Grenze von {limit} Datens?tzen ist erreicht.",
        )


def check_quota(db: Session) -> None:
    count = db.scalar(select(func.count()).select_from(DataJob)) or 0
    waiting = (
        db.scalar(
            select(func.count())
            .select_from(DataJob)
            .where(DataJob.status.in_(["QUEUED", "RUNNING"]))
        )
        or 0
    )
    if count >= 500 or waiting >= 10:
        raise HTTPException(
            409, "Die lokale Grenze von 500 Aufträgen oder zehn wartenden Aufträgen ist erreicht."
        )


def create_version(db: Session, dataset: Dataset, job: DataJob, actor: ActorContext) -> DataVersion:
    assert job.result_blob_id and job.result_hash and job.profile is not None
    version = DataVersion(
        organization_id=actor.organization_id,
        dataset_id=dataset.id,
        job_id=job.id,
        blob_id=job.result_blob_id,
        created_by_user_id=actor.user_id,
        version_no=dataset.current_version + 1,
        source_version=job.source_version,
        content_hash=job.result_hash,
        profile=job.profile,
        steps=job.steps,
    )
    dataset.current_version += 1
    db.add(version)
    db.flush()
    append_audit(
        db,
        actor,
        "data.version.created",
        "dataset",
        dataset.id,
        {
            "version_no": version.version_no,
            "job_id": str(job.id),
            "content_hash": version.content_hash,
        },
    )
    return version


def commit_preview(
    db: Session, actor: ActorContext, dataset_id: UUID, payload: CommitInput
) -> VersionView:
    check_write(db, actor)
    dataset = dataset_for(db, dataset_id, lock=True)
    job = db.scalar(
        select(DataJob).where(DataJob.id == payload.preview_id, DataJob.dataset_id == dataset.id)
    )
    if job is None:
        raise HTTPException(404, "Die Vorschau wurde nicht gefunden.")
    if job.kind != "PREVIEW" or job.status != "SUCCEEDED" or job.result_hash != payload.result_hash:
        raise HTTPException(409, "Die bestätigte Vorschau passt nicht zum berechneten Ergebnis.")
    existing = db.scalar(select(DataVersion).where(DataVersion.job_id == job.id))
    if existing:
        return version_view(existing)
    if (
        dataset.current_version != payload.expected_current_version
        or job.source_version != dataset.current_version
    ):
        raise HTTPException(
            409, "Eine neuere Datenversion liegt vor. Bitte eine neue Vorschau erstellen."
        )
    if dataset.current_version >= 20:
        raise HTTPException(409, "Die lokale Grenze von 20 Versionen ist erreicht.")
    return version_view(create_version(db, dataset, job, actor))


def process_one(organization_id: UUID) -> bool:
    """Ein Aufruf verarbeitet höchstens einen Auftrag."""
    from platform_app.data.stream_worker import process_stream_job

    if process_stream_job(organization_id):
        return True
    with tenant_session(organization_id) as db:
        db.execute(text("SET LOCAL statement_timeout = '15s'"))
        db.execute(text("SET LOCAL idle_in_transaction_session_timeout = '20s'"))
        # Lock-Reihenfolge wie API: Organisation vor Auftrag vor Datensatz.
        # SKIP LOCKED am Organisationslock verhindert Kreise mit Rollenänderungen.
        org = db.execute(
            text("SELECT id FROM organizations WHERE id=:org FOR UPDATE SKIP LOCKED"),
            {"org": organization_id},
        ).first()
        if not org:
            return False
        job = db.scalar(
            select(DataJob)
            .where(DataJob.status == "QUEUED", DataJob.processing_mode == "LEGACY")
            .order_by(DataJob.created_at, DataJob.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return False
        actor = ActorContext(job.created_by_user_id, organization_id, frozenset(), "Datenauftrag")
        try:
            # Ein Savepoint entfernt auch teilweise erzeugte Blobs/Versionen bei Fachfehlern.
            with db.begin_nested():
                check_write(db, actor)
                dataset = dataset_for(db, job.dataset_id, lock=True)
                storage: BlobStore = PostgresBlobStore(db, organization_id)
                if job.kind == "IMPORT":
                    table = parse_csv(storage.get(dataset.original_blob_id), dataset.delimiter)
                else:
                    source = version_for(db, dataset.id, job.source_version or 0)
                    table = transform(
                        decode_table(storage.get(source.blob_id)),
                        [Step.model_validate(s) for s in job.steps],
                    )
                job.result_blob_id, job.result_hash = storage.put(encode_table(table))
                job.profile = profile(table).model_dump(mode="json")
                job.finished_at, job.status = now(), "SUCCEEDED"
                db.flush()
                if job.kind == "IMPORT":
                    create_version(db, dataset, job, actor)
                else:
                    append_audit(
                        db,
                        actor,
                        "data.preview.ready",
                        "dataset",
                        dataset.id,
                        {"job_id": str(job.id), "result_hash": job.result_hash},
                    )
        except (DataError, HTTPException) as error:
            job.status, job.finished_at = "FAILED", now()
            job.error = (
                str(error)
                if isinstance(error, DataError)
                else "Verarbeitung abgebrochen: Quelle oder Schreibberechtigung nicht mehr verfügbar."
            )
            append_audit(
                db, actor, "data.job.failed", "dataset", job.dataset_id, {"job_id": str(job.id)}
            )
        return True
