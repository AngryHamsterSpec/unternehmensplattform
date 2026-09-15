"""Öffentliche M2-Verträge: Quellen, Analysen, Regeln und geprüfte Pläne."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import load_only

from platform_app.data.engine import DataError
from platform_app.data.intelligence_models import DataTask, QualityRuleSet
from platform_app.data.intelligence_schemas import (
    AnalysisInput,
    PlanInput,
    PlanSelection,
    RuleSetInput,
    RuleSetView,
    SourceImportInput,
    TaskSummary,
    TaskView,
)
from platform_app.data.intelligence_service import create_task, task_for, task_view
from platform_app.data.models import DataBlob, DataJob
from platform_app.data.plan_advisor import (
    OpenAIPlanProvider,
    candidates,
    check_payload,
    minimized_payload,
    verify_plan,
)
from platform_app.data.postgres_source import source_for, sources
from platform_app.data.reports import analytical_html
from platform_app.data.schemas import DataProfile, JobView, Step
from platform_app.data.service import (
    check_dataset_quota,
    check_quota,
    dataset_for,
    job_view,
    version_for,
)
from platform_app.decisions.engine import fingerprint
from platform_app.explanations.models import ProviderBudgetDay
from platform_app.explanations.provider import reservation
from platform_app.explanations.router import available
from platform_app.identity.dependencies import ActorContext, get_actor, require_write
from platform_app.intake.models import now
from platform_app.shared.audit import append_audit
from platform_app.shared.authorization import check_write
from platform_app.shared.config import get_settings
from platform_app.shared.db import tenant_session

router = APIRouter(prefix="/api/v1", tags=["Datenanalyse"])
Idempotency = Annotated[UUID, Header(alias="Idempotency-Key")]


@router.get("/data-sources")
def list_sources(actor: ActorContext = Depends(get_actor)) -> dict[str, Any]:
    try:
        items = [
            {"id": c.id, "name": c.name, "tables": c.tables, "provider": "postgresql"}
            for c in sources(actor.organization_id)
        ]
    except DataError as error:
        raise HTTPException(503, str(error)) from None
    return {"items": items, "live_ai_available": available(actor.organization_id)}


@router.post("/data-sources/import", status_code=202, response_model=TaskView)
def import_source(
    payload: SourceImportInput,
    idempotency_key: Idempotency,
    actor: ActorContext = Depends(require_write),
) -> TaskView:
    try:
        source_for(actor.organization_id, payload.source_id, payload.table)
    except DataError as error:
        raise HTTPException(422, str(error)) from None
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        check_dataset_quota(db)
        task, _ = create_task(db, actor, "SOURCE", payload.model_dump(), idempotency_key)
        return task_view(task)


@router.get("/data-rule-sets")
def list_rules(actor: ActorContext = Depends(get_actor)) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        rows = db.scalars(select(QualityRuleSet).order_by(QualityRuleSet.created_at.desc())).all()
        return {"items": [RuleSetView.model_validate(r, from_attributes=True) for r in rows]}


@router.post("/data-rule-sets", status_code=201, response_model=RuleSetView)
def save_rules(payload: RuleSetInput, actor: ActorContext = Depends(require_write)) -> RuleSetView:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        if (db.scalar(select(func.count()).select_from(QualityRuleSet)) or 0) >= 500:
            raise HTTPException(
                409, "Maximal 500 unveränderliche Regelsatzversionen je Organisation."
            )
        if payload.replaces_id and db.get(QualityRuleSet, payload.replaces_id) is None:
            raise HTTPException(404, "Die vorherige Regelsatzversion wurde nicht gefunden.")
        row = QualityRuleSet(
            organization_id=actor.organization_id,
            created_by_user_id=actor.user_id,
            **payload.model_dump(),
        )
        db.add(row)
        db.flush()
        append_audit(
            db,
            actor,
            "data.ruleset.created",
            "data_ruleset",
            row.id,
            {"rules_hash": fingerprint(row.rules), "replaces_id": str(row.replaces_id)},
        )
        return RuleSetView.model_validate(row, from_attributes=True)


@router.post("/datasets/{dataset_id}/analyses", status_code=202, response_model=TaskView)
def queue_analysis(
    dataset_id: UUID,
    payload: AnalysisInput,
    idempotency_key: Idempotency,
    actor: ActorContext = Depends(require_write),
) -> TaskView:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        version = version_for(db, dataset_id, payload.version_no)
        options = payload.model_dump(mode="json")
        snapshot = None
        if payload.ruleset_id:
            ruleset = db.get(QualityRuleSet, payload.ruleset_id)
            if ruleset is None:
                raise HTTPException(404, "Der Regelsatz wurde nicht gefunden.")
            snapshot = {
                "id": str(ruleset.id),
                "name": ruleset.name,
                "created_at": ruleset.created_at.isoformat(),
            }
            options["rules"], options["ruleset_id"] = ruleset.rules, None
        validated = AnalysisInput.model_validate(options)
        selected = (
            validated.numeric_columns
            + [r.column for r in validated.rules]
            + [v for v in (validated.date_column, validated.time_metric) if v]
        )
        if any(c not in {p["name"] for p in version.profile["columns"]} for c in selected):
            raise HTTPException(422, "Eine gewählte Spalte fehlt in der Datenversion.")
        task, _ = create_task(
            db,
            actor,
            "ANALYSIS",
            {"analysis": options, "ruleset": snapshot},
            idempotency_key,
            dataset_id,
            payload.version_no,
        )
        return task_view(task)


@router.get("/data-tasks")
def tasks(
    dataset_id: UUID | None = None,
    kind: Literal["SOURCE", "ANALYSIS", "PLAN"] | None = None,
    before: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    actor: ActorContext = Depends(get_actor),
) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        query = (
            select(DataTask)
            .options(load_only(*(getattr(DataTask, field) for field in TaskSummary.model_fields)))
            .order_by(DataTask.created_at.desc(), DataTask.id.desc())
        )
        if dataset_id:
            dataset_for(db, dataset_id)
            query = query.where(DataTask.dataset_id == dataset_id)
        if kind:
            query = query.where(DataTask.kind == kind)
        if before:
            cursor = task_for(db, before)
            query = query.where(
                (DataTask.created_at < cursor.created_at)
                | ((DataTask.created_at == cursor.created_at) & (DataTask.id < cursor.id))
            )
        rows = db.scalars(query.limit(limit + 1)).all()
        return {
            "items": [TaskSummary.model_validate(r, from_attributes=True) for r in rows[:limit]],
            "next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None,
        }


@router.get("/data-tasks/{task_id}", response_model=TaskView)
def get_task(task_id: UUID, actor: ActorContext = Depends(get_actor)) -> TaskView:
    with tenant_session(actor.organization_id) as db:
        return task_view(task_for(db, task_id))


@router.post("/data-tasks/{task_id}/cancel", response_model=TaskView)
def cancel(task_id: UUID, actor: ActorContext = Depends(require_write)) -> TaskView:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        task = task_for(db, task_id, lock=True)
        if task.status in {"QUEUED", "RUNNING"}:
            task.status, task.finished_at, task.error = (
                "CANCELLED",
                now(),
                "Auftrag bewusst abgebrochen. Bereits begonnene externe Verarbeitung kann noch auslaufen.",
            )
            append_audit(db, actor, "data.task.cancelled", "data_task", task.id, {})
        return task_view(task)


@router.post("/data-tasks/{task_id}/retry", status_code=202, response_model=TaskView)
def retry(
    task_id: UUID, idempotency_key: Idempotency, actor: ActorContext = Depends(require_write)
) -> TaskView:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        previous = task_for(db, task_id)
        if previous.status not in {"FAILED", "CANCELLED"} or previous.kind == "PLAN":
            raise HTTPException(
                409,
                "Nur fehlgeschlagene oder abgebrochene Analyse-/Quellenaufträge wiederholen. KI-Pläne bewusst neu anfordern.",
            )
        task, _ = create_task(
            db,
            actor,
            previous.kind,
            previous.request,
            idempotency_key,
            previous.dataset_id,
            previous.version_no,
        )
        append_audit(
            db,
            actor,
            "data.task.retried",
            "data_task",
            task.id,
            {"previous_task_id": str(previous.id)},
        )
        return task_view(task)


@router.get("/data-tasks/{task_id}/report")
def export_report(
    task_id: UUID,
    format: str = Query("html", pattern="^(html|json)$"),
    actor: ActorContext = Depends(get_actor),
) -> Response:
    with tenant_session(actor.organization_id) as db:
        task = task_for(db, task_id)
        if (
            task.kind != "ANALYSIS"
            or task.status != "SUCCEEDED"
            or task.result is None
            or task.result_hash is None
        ):
            raise HTTPException(409, "Der Analysebericht ist noch nicht verfügbar.")
        if fingerprint(task.result) != task.result_hash:
            raise HTTPException(409, "Der Analysebericht besteht die Integritätsprüfung nicht.")
        metadata = {
            "created_by_user_id": str(task.created_by_user_id),
            "created_at": task.created_at.isoformat(),
            "finished_at": task.finished_at.isoformat() if task.finished_at else "",
        }
        body = (
            analytical_html(task.result, str(task.id), task.result_hash, metadata)
            if format == "html"
            else json.dumps(
                {
                    "task_id": str(task.id),
                    **metadata,
                    "result_hash": task.result_hash,
                    "result": task.result,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        append_audit(
            db,
            actor,
            "data.report.exported",
            "data_task",
            task.id,
            {"result_hash": task.result_hash, "format": format},
        )
        return Response(
            body,
            media_type="text/html" if format == "html" else "application/json",
            headers={
                "Content-Disposition": f'attachment; filename="analyse-{task.id}.{format}"',
                "X-Content-Type-Options": "nosniff",
            },
        )


@router.post("/datasets/{dataset_id}/plans", status_code=201, response_model=TaskView)
def plan(
    dataset_id: UUID,
    payload: PlanInput,
    idempotency_key: Idempotency,
    actor: ActorContext = Depends(require_write),
) -> TaskView:
    settings = get_settings()
    if payload.mode == "openai" and (
        not available(actor.organization_id) or not payload.approve_external_processing
    ):
        raise HTTPException(
            403,
            "Die externe KI-Verarbeitung benötigt Organisationsfreigabe und ausdrückliche Zustimmung.",
        )
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        version = version_for(db, dataset_id, payload.version_no)
        profile = DataProfile.model_validate(version.profile)
        choices = candidates(profile)
        context = minimized_payload(profile, choices)
        check_payload(context)
        source_hash = version.content_hash
        task, created = create_task(
            db, actor, "PLAN", payload.model_dump(), idempotency_key, dataset_id, payload.version_no
        )
        if not created:
            return task_view(task)
        amount = Decimal(0)
        if payload.mode == "openai":
            amount = reservation(settings)
            day = datetime.now(UTC).date()
            db.execute(
                insert(ProviderBudgetDay)
                .values(organization_id=actor.organization_id, budget_date=day, reserved_usd=0)
                .on_conflict_do_nothing()
            )
            budget = db.scalar(
                select(ProviderBudgetDay)
                .where(ProviderBudgetDay.budget_date == day)
                .with_for_update()
            )
            assert budget is not None
            if budget.reserved_usd + amount > Decimal(settings.openai_daily_budget):
                raise HTTPException(429, "Das gemeinsame KI-Tagesbudget ist ausgeschöpft.")
            budget.reserved_usd += amount
        task.status, task.attempts, task.lease_token, task.lease_until = (
            "RUNNING",
            1,
            uuid4(),
            now() + timedelta(seconds=90),
        )
        task_id, token = task.id, task.lease_token
        append_audit(
            db,
            actor,
            "data.plan.reserved",
            "data_task",
            task.id,
            {
                "source_hash": source_hash,
                "input_hash": fingerprint(context),
                "reserved_usd": str(amount),
                "model": settings.openai_model if payload.mode == "openai" else None,
                "price_version": settings.openai_price_version
                if payload.mode == "openai"
                else None,
            },
        )
    result, failure = None, None
    try:
        selection = (
            asyncio.run(OpenAIPlanProvider().select(settings, context))
            if payload.mode == "openai"
            else PlanSelection(candidate_ids=[c["id"] for c in choices])
        )
        result = verify_plan(profile, choices, selection, source_hash, payload.mode)
        result.update(
            {
                "reserved_usd": str(amount),
                "model": settings.openai_model if payload.mode == "openai" else None,
                "price_version": settings.openai_price_version
                if payload.mode == "openai"
                else None,
                "input_hash": fingerprint(context),
            }
        )
    except Exception:
        failure = "Kein geprüfter Plan verfügbar. Anbieterfehler, Ablehnung oder Verifier-Grenze; keine automatische Wiederholung."
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        task = task_for(db, task_id, lock=True)
        if (
            task.status != "RUNNING"
            or task.lease_token != token
            or task.lease_until is None
            or task.lease_until < now()
        ):
            return task_view(task)
        task.status, task.finished_at = ("FAILED" if failure else "SUCCEEDED"), now()
        task.result, task.error = result, failure
        task.result_hash = fingerprint(result) if result else None
        task.progress, task.message = 100, "Plan geprüft" if result else "Planung fehlgeschlagen"
        append_audit(
            db,
            actor,
            "data.plan.finished",
            "data_task",
            task.id,
            {"status": task.status, "result_hash": task.result_hash},
        )
        return task_view(task)


@router.post("/data-tasks/{task_id}/preview", status_code=202, response_model=JobView)
def plan_preview(task_id: UUID, actor: ActorContext = Depends(require_write)) -> JobView:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        task = task_for(db, task_id)
        if (
            task.kind != "PLAN"
            or task.status != "SUCCEEDED"
            or not task.result
            or task.dataset_id is None
        ):
            raise HTTPException(409, "Es liegt kein geprüfter Plan vor.")
        if fingerprint(task.result) != task.result_hash:
            raise HTTPException(409, "Die Planprüfsumme stimmt nicht.")
        dataset = dataset_for(db, task.dataset_id, lock=True)
        version = version_for(db, dataset.id, task.version_no or 0)
        if (
            dataset.current_version != task.version_no
            or version.content_hash != task.result["source_hash"]
        ):
            raise HTTPException(
                409,
                "Der Plan gehört zu einer älteren Datenversion. Bitte für die aktuelle Version neu planen.",
            )
        steps = [Step.model_validate(s).model_dump() for s in task.result["steps"]]
        if not steps:
            raise HTTPException(409, "Der Plan enthält keine ausreichend belegte Änderung.")
        existing = db.scalar(
            select(DataJob)
            .where(
                DataJob.dataset_id == dataset.id,
                DataJob.created_by_user_id == actor.user_id,
                DataJob.kind == "PREVIEW",
                DataJob.source_version == task.version_no,
                DataJob.steps == steps,
                DataJob.status.in_(["QUEUED", "RUNNING", "SUCCEEDED"]),
            )
            .order_by(DataJob.created_at.desc())
            .limit(1)
        )
        if existing:
            append_audit(
                db,
                actor,
                "data.plan.preview.reused",
                "dataset",
                dataset.id,
                {
                    "plan_task_id": str(task.id),
                    "plan_hash": task.result_hash,
                    "job_id": str(existing.id),
                },
            )
            return job_view(existing)
        check_quota(db)
        source_blob = db.get(DataBlob, version.blob_id)
        if source_blob is None:
            raise HTTPException(409, "Die Datenversion ist nicht vollständig verfügbar.")
        job = DataJob(
            organization_id=actor.organization_id,
            dataset_id=dataset.id,
            created_by_user_id=actor.user_id,
            kind="PREVIEW",
            processing_mode="STREAM" if source_blob.object_id else "LEGACY",
            source_version=task.version_no,
            steps=steps,
        )
        db.add(job)
        db.flush()
        append_audit(
            db,
            actor,
            "data.plan.preview.queued",
            "dataset",
            dataset.id,
            {"plan_task_id": str(task.id), "plan_hash": task.result_hash, "job_id": str(job.id)},
        )
        return job_view(job)
