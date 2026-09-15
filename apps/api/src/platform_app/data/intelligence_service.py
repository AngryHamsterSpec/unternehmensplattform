"""Persistente M2-Aufträge mit RLS, Idempotenz und unveränderlichem Ergebnis."""

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from platform_app.data.intelligence_models import DataTask
from platform_app.data.intelligence_schemas import TaskView
from platform_app.decisions.engine import fingerprint
from platform_app.identity.dependencies import ActorContext
from platform_app.shared.audit import append_audit


def task_for(db: Session, task_id: UUID, *, lock: bool = False) -> DataTask:
    query = select(DataTask).where(DataTask.id == task_id)
    task = db.scalar(query.with_for_update() if lock else query)
    if task is None:
        raise HTTPException(404, "Der Datenauftrag wurde nicht gefunden.")
    return task


def task_view(task: DataTask) -> TaskView:
    return TaskView.model_validate(task, from_attributes=True)


def create_task(
    db: Session,
    actor: ActorContext,
    kind: str,
    request: dict[str, Any],
    key: UUID,
    dataset_id: UUID | None = None,
    version_no: int | None = None,
) -> tuple[DataTask, bool]:
    digest = fingerprint(
        {"kind": kind, "dataset_id": str(dataset_id), "version_no": version_no, "request": request}
    )
    previous = db.scalar(
        select(DataTask).where(
            DataTask.created_by_user_id == actor.user_id, DataTask.idempotency_key == key
        )
    )
    if previous:
        if previous.request_hash != digest:
            raise HTTPException(
                409, "Dieser Wiederholungsschlüssel gehört zu einem anderen Auftrag."
            )
        return previous, False
    waiting = (
        db.scalar(
            select(func.count())
            .select_from(DataTask)
            .where(DataTask.status.in_(["QUEUED", "RUNNING"]))
        )
        or 0
    )
    count = db.scalar(select(func.count()).select_from(DataTask)) or 0
    if waiting >= 10 or count >= 10000:
        raise HTTPException(
            409,
            "Maximal zehn aktive oder 10.000 gespeicherte Analyse-/Quellen-/Planungsaufträge je Organisation.",
        )
    task = DataTask(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        idempotency_key=key,
        dataset_id=dataset_id,
        version_no=version_no,
        kind=kind,
        request=request,
        request_hash=digest,
    )
    db.add(task)
    db.flush()
    append_audit(
        db, actor, "data.task.queued", "data_task", task.id, {"kind": kind, "request_hash": digest}
    )
    return task, True
