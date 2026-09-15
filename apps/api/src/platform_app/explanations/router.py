import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from platform_app.assessments.models import Assessment
from platform_app.decisions.engine import fingerprint
from platform_app.explanations.models import ExplanationRequest, ProviderBudgetDay
from platform_app.explanations.provider import (
    OpenAIExplanationProvider,
    check_payload,
    minimized_payload,
    reservation,
)
from platform_app.identity.dependencies import ActorContext, get_actor, require_write
from platform_app.intake.models import now
from platform_app.shared.audit import append_audit
from platform_app.shared.authorization import check_write
from platform_app.shared.config import get_settings
from platform_app.shared.db import tenant_session

router = APIRouter(prefix="/api/v1")


class ExplanationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve_external_processing: bool


def available(organization_id: UUID | None) -> bool:
    settings = get_settings()
    return settings.openai_enabled and str(organization_id) in {
        v.strip() for v in settings.openai_organization_ids.split(",")
    }


def view(row: ExplanationRequest) -> dict[str, Any]:
    # Keine Wiederholung nach unklarem externem Ausgang; Reservierung bleibt erhalten.
    uncertain = row.status == "RESERVED" and now() - row.created_at > timedelta(seconds=30)
    return {
        "id": str(row.id),
        "assessment_id": str(row.assessment_id),
        "status": "INDETERMINATE" if uncertain else row.status,
        "provider": "openai",
        "model": row.model,
        "price_version": row.price_version,
        "reserved_usd": str(row.reserved_usd),
        "output": row.output,
        "failure_code": "OUTCOME_UNKNOWN" if uncertain else row.failure_code,
        "created_at": row.created_at.isoformat(),
        "notice": "Optionale KI-Formulierung; der geprüfte Bewertungssnapshot bleibt maßgeblich.",
    }


@router.post("/assessments/{assessment_id}/explanations", status_code=201)
def create(
    assessment_id: UUID,
    body: ExplanationCreate,
    response: Response,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    actor: ActorContext = Depends(require_write),
) -> dict[str, Any]:
    settings = get_settings()
    if not available(actor.organization_id) or not body.approve_external_processing:
        raise HTTPException(403, "Die externe Verarbeitung ist nicht freigegeben.")
    request_hash = fingerprint({"assessment_id": str(assessment_id), **body.model_dump()})
    with tenant_session(actor.organization_id) as db:
        # Derselbe Organisationslock serialisiert Idempotenz und Budgetreservierungen.
        check_write(db, actor)
        previous = db.scalar(
            select(ExplanationRequest).where(
                ExplanationRequest.created_by_user_id == actor.user_id,
                ExplanationRequest.idempotency_key == idempotency_key,
            )
        )
        if previous:
            if previous.request_hash != request_hash:
                raise HTTPException(
                    409, "Der Wiederholungsschlüssel gehört zu einer anderen Anfrage."
                )
            result = view(previous)
            response.status_code = 202 if result["status"] == "RESERVED" else 200
            return result
        assessment = db.get(Assessment, assessment_id)
        if assessment is None:
            raise HTTPException(404, "Bewertung nicht gefunden.")
        if assessment.status != "VERIFIED":
            raise HTTPException(
                409, "Nur verifizierte Bewertungen können zusätzlich erklärt werden."
            )
        payload = minimized_payload(assessment.result)
        try:
            check_payload(payload)
        except ValueError:
            raise HTTPException(
                422, "Das minimierte Ergebnis überschreitet das Übertragungslimit."
            ) from None
        amount = reservation(settings)
        day = datetime.now(UTC).date()
        db.execute(
            insert(ProviderBudgetDay)
            .values(organization_id=actor.organization_id, budget_date=day, reserved_usd=0)
            .on_conflict_do_nothing()
        )
        budget = db.execute(
            select(ProviderBudgetDay).where(ProviderBudgetDay.budget_date == day).with_for_update()
        ).scalar_one()
        if budget.reserved_usd + amount > Decimal(settings.openai_daily_budget):
            raise HTTPException(429, "Das Tagesbudget für optionale Erklärungen ist ausgeschöpft.")
        budget.reserved_usd += amount
        row = ExplanationRequest(
            id=uuid4(),
            organization_id=actor.organization_id,
            assessment_id=assessment_id,
            created_by_user_id=actor.user_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            model=settings.openai_model,
            price_version=settings.openai_price_version,
            reserved_usd=amount,
            input_hash=fingerprint(payload),
        )
        db.add(row)
        append_audit(
            db,
            actor,
            "explanation.reserved",
            "explanation",
            row.id,
            {"input_hash": row.input_hash, "reserved_usd": str(amount)},
        )
        db.flush()
        request_id = row.id
    # Niemals DB-Transaktion während externer Anfrage offenhalten.
    output = None
    failure = None
    try:
        output = asyncio.run(OpenAIExplanationProvider(settings).explain(payload)).model_dump()
    except Exception:
        # Keine Providerfehlertexte protokollieren: Sie können Eingabedaten enthalten.
        failure = "PROVIDER_FAILED"
    with tenant_session(actor.organization_id) as db:
        saved = db.get(ExplanationRequest, request_id)
        assert saved is not None
        saved.status = "FAILED" if failure else "SUCCEEDED"
        saved.failure_code = failure
        saved.output = output
        saved.finished_at = now()
        append_audit(
            db, actor, "explanation.finished", "explanation", saved.id, {"status": saved.status}
        )
        db.flush()
        return view(saved)


@router.get("/assessments/{assessment_id}/explanations")
def list_for_assessment(
    assessment_id: UUID, actor: ActorContext = Depends(get_actor)
) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        if db.get(Assessment, assessment_id) is None:
            raise HTTPException(404, "Bewertung nicht gefunden.")
        rows = db.scalars(
            select(ExplanationRequest)
            .where(ExplanationRequest.assessment_id == assessment_id)
            .order_by(ExplanationRequest.created_at)
        ).all()
        return {"items": [view(row) for row in rows]}


@router.get("/explanation-requests/{request_id}")
def get_request(
    request_id: UUID, response: Response, actor: ActorContext = Depends(get_actor)
) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        row = db.get(ExplanationRequest, request_id)
        if row is None:
            raise HTTPException(404, "Erklärungsanfrage nicht gefunden.")
        result = view(row)
        response.status_code = 202 if result["status"] == "RESERVED" else 200
        return result
