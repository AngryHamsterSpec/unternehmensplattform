"""Versionierte HTTP-Schnittstellen für den vollständigen Entscheidungsschnitt."""

import base64
import json
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import Field
from sqlalchemy import select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from platform_app.assessments.models import (
    AgentRun,
    Assessment,
    AuditEvent,
    CandidateRecord,
    CostCatalog,
    CostLineRecord,
)
from platform_app.contracts import AssessmentView, AuditView, Page, ScenarioView, VersionView
from platform_app.decisions.catalog import catalog_metadata
from platform_app.decisions.demo import demo_scenario
from platform_app.decisions.engine import evaluate, fingerprint
from platform_app.decisions.schemas import AssessmentOptions, ScenarioInput
from platform_app.identity.dependencies import ActorContext, get_actor, require_admin, require_write
from platform_app.intake.models import CompanyProfile, ProfileVersion
from platform_app.intake.service import save_version, scenario_response, visible_profile
from platform_app.shared.audit import append_audit
from platform_app.shared.authorization import check_write
from platform_app.shared.db import tenant_session

router = APIRouter(prefix="/api/v1")


def cursor_decode(cursor: str) -> tuple[datetime, UUID]:
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("shape")
        stamp = datetime.fromisoformat(value[0])
        if stamp.tzinfo is None:
            raise ValueError("timezone")
        return stamp, UUID(value[1])
    except (ValueError, TypeError, IndexError):
        raise HTTPException(422, "Ungültiger Seitencursor.") from None


def next_cursor(row: Any) -> str:
    return base64.urlsafe_b64encode(
        json.dumps([row.created_at.isoformat(), str(row.id)]).encode()
    ).decode()


class ScenarioVersionCreate(ScenarioInput):
    expected_current_version: int = Field(ge=1)


class AssessmentCreate(AssessmentOptions):
    scenario_version_id: UUID
    candidate_catalog_version: str | None = None
    cost_catalog_version: str | None = None
    rule_set_version: str | None = None


@router.get("/demo-scenario")
def example(actor: ActorContext = Depends(get_actor)) -> dict[str, Any]:
    return demo_scenario()


@router.get("/scenarios", response_model=Page[ScenarioView])
def list_scenarios(
    actor: ActorContext = Depends(get_actor),
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = None,
) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        stmt = (
            select(CompanyProfile)
            .order_by(CompanyProfile.created_at, CompanyProfile.id)
            .limit(limit + 1)
        )
        if cursor:
            stmt = stmt.where(
                tuple_(CompanyProfile.created_at, CompanyProfile.id) > cursor_decode(cursor)
            )
        rows = db.scalars(stmt).all()
        current = db.scalars(
            select(ProfileVersion)
            .join(
                CompanyProfile,
                (CompanyProfile.id == ProfileVersion.company_profile_id)
                & (CompanyProfile.revision == ProfileVersion.version_no),
            )
            .where(CompanyProfile.id.in_([p.id for p in rows[:limit]]))
        ).all()
        versions = {version.company_profile_id: version for version in current}
        return {
            "items": [
                scenario_response(db, p, [versions[p.id]] if p.id in versions else [])
                for p in rows[:limit]
            ],
            "next_cursor": next_cursor(rows[limit - 1]) if len(rows) > limit else None,
        }


@router.post("/scenarios", status_code=201, response_model=ScenarioView)
def create_scenario(
    body: ScenarioInput, actor: ActorContext = Depends(require_write)
) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        profile = CompanyProfile(
            id=uuid4(),
            organization_id=actor.organization_id,
            created_by_user_id=actor.user_id,
            name=body.name,
        )
        db.add(profile)
        db.flush()
        save_version(db, actor, body, profile, 1)
        db.flush()
        return scenario_response(db, profile)


@router.get("/scenarios/{profile_id}", response_model=ScenarioView)
def get_scenario(profile_id: UUID, actor: ActorContext = Depends(get_actor)) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        return scenario_response(db, visible_profile(db, profile_id))


@router.post("/scenarios/{profile_id}/versions", status_code=201, response_model=ScenarioView)
def create_version(
    profile_id: UUID, body: ScenarioVersionCreate, actor: ActorContext = Depends(require_write)
) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        profile = db.scalar(
            select(CompanyProfile).where(CompanyProfile.id == profile_id).with_for_update()
        )
        if not profile:
            raise HTTPException(404, "Szenario nicht gefunden.")
        if profile.revision != body.expected_current_version:
            raise HTTPException(409, "Das Szenario wurde inzwischen geändert. Bitte neu laden.")
        profile.revision += 1
        profile.name = body.name
        data = ScenarioInput.model_validate(body.model_dump(exclude={"expected_current_version"}))
        save_version(db, actor, data, profile, profile.revision)
        db.flush()
        return scenario_response(db, profile)


@router.get("/scenarios/{profile_id}/versions/{version_no}", response_model=VersionView)
def get_version(
    profile_id: UUID, version_no: int, actor: ActorContext = Depends(get_actor)
) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        visible_profile(db, profile_id)
        v = db.scalar(
            select(ProfileVersion).where(
                ProfileVersion.company_profile_id == profile_id,
                ProfileVersion.version_no == version_no,
            )
        )
        if not v:
            raise HTTPException(404, "Profilversion nicht gefunden.")
        return {"id": str(v.id), "version_no": v.version_no, "data": v.data}


@router.get("/decision-catalogs")
def catalogs(actor: ActorContext = Depends(get_actor)) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        rows = db.scalars(select(CostCatalog)).all()
        return {"items": [{"id": str(r.id), **r.data} for r in rows]}


def assessment_response(a: Assessment) -> dict[str, Any]:
    return {
        **a.result,
        "id": str(a.id),
        "scenario_version_id": str(a.profile_version_id),
        "created_at": a.created_at.isoformat(),
        "result_hash": a.result_hash,
        "options": a.options,
    }


def existing(db: Session, actor: ActorContext, key: UUID, request_hash: str) -> Assessment | None:
    row = db.scalar(
        select(Assessment).where(
            Assessment.created_by_user_id == actor.user_id, Assessment.idempotency_key == key
        )
    )
    if row and row.request_hash != request_hash:
        raise HTTPException(409, "Der Wiederholungsschlüssel gehört zu einer anderen Anfrage.")
    return row


@router.post("/assessments", status_code=201, response_model=AssessmentView)
def create_assessment(
    body: AssessmentCreate,
    response: Response,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    actor: ActorContext = Depends(require_write),
) -> dict[str, Any]:
    data = body.model_dump(mode="json")
    request_hash = fingerprint(body.model_dump(mode="json", exclude_unset=True))
    meta = catalog_metadata()
    for field in ("rule_set_version", "cost_catalog_version", "candidate_catalog_version"):
        if data.get(field) is not None and data[field] != meta[field]:
            raise HTTPException(
                422, "Die angeforderte Katalog- oder Regelversion ist nicht verfügbar."
            )
    with tenant_session(actor.organization_id) as db:
        previous = existing(db, actor, idempotency_key, request_hash)
        if previous:
            response.status_code = 200
            return assessment_response(previous)
        version = db.get(ProfileVersion, body.scenario_version_id)
        if version is None:
            raise HTTPException(404, "Profilversion nicht gefunden.")
        snapshot = version.data
        catalog = db.scalar(
            select(CostCatalog).where(CostCatalog.version == meta["cost_catalog_version"])
        )
        if catalog is None:
            raise HTTPException(503, "Der freigegebene Kostenkatalog fehlt.")
        if catalog.content_hash != fingerprint(meta):
            raise HTTPException(
                503, "Der Kataloginhalt stimmt nicht mit seiner freigegebenen Version überein."
            )
        catalog_id = catalog.id
    options = AssessmentOptions.model_validate(
        body.model_dump(
            include={"weight_profile", "custom_weights", "horizon_months", "valuation_date"}
        )
    )
    result = evaluate(ScenarioInput.model_validate(snapshot), options)
    result_data = result.model_dump(mode="json")
    try:
        with tenant_session(actor.organization_id) as db:
            check_write(db, actor)
            previous = existing(db, actor, idempotency_key, request_hash)
            if previous:
                response.status_code = 200
                return assessment_response(previous)
            row = Assessment(
                id=uuid4(),
                organization_id=actor.organization_id,
                created_by_user_id=actor.user_id,
                profile_version_id=body.scenario_version_id,
                catalog_version_id=catalog_id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                result_hash=fingerprint(result_data),
                status=result.status,
                options=options.model_dump(mode="json"),
                input_snapshot=snapshot,
                result=result_data,
            )
            db.add(row)
            db.flush()
            for c in result.candidates:
                stored = CandidateRecord(
                    id=uuid4(),
                    organization_id=actor.organization_id,
                    assessment_id=row.id,
                    candidate_key=c.key,
                    status=c.status,
                    score=c.score,
                    rank=c.rank,
                    tco_total=c.costs.tco_total,
                )
                db.add(stored)
                db.flush()
                for line in c.costs.lines:
                    db.add(
                        CostLineRecord(
                            organization_id=actor.organization_id,
                            assessment_id=row.id,
                            candidate_id=stored.id,
                            label=line.label,
                            category=line.category,
                            total=line.total,
                            data=line.model_dump(mode="json"),
                        )
                    )
            for name in ("InfrastructureManager", "CostEstimator", "Verifier"):
                db.add(
                    AgentRun(
                        organization_id=actor.organization_id,
                        assessment_id=row.id,
                        agent_key=name,
                        status="SUCCEEDED" if result.verification.valid else "FAILED",
                        data={
                            "rule_version": result.rule_set_version,
                            "result_hash": row.result_hash,
                            "verification": result.verification.model_dump(),
                        },
                    )
                )
            append_audit(
                db,
                actor,
                "assessment.created",
                "assessment",
                row.id,
                {"status": row.status, "result_hash": row.result_hash},
            )
            db.flush()
            return assessment_response(row)
    except IntegrityError:
        with tenant_session(actor.organization_id) as db:
            previous = existing(db, actor, idempotency_key, request_hash)
            if previous:
                response.status_code = 200
                return assessment_response(previous)
        raise HTTPException(
            409, "Bewertung konnte wegen einer konkurrierenden Änderung nicht gespeichert werden."
        ) from None


@router.get("/assessments", response_model=Page[AssessmentView])
def list_assessments(
    actor: ActorContext = Depends(get_actor),
    scenario_id: UUID | None = None,
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = None,
) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        stmt = select(Assessment).order_by(Assessment.created_at, Assessment.id).limit(limit + 1)
        if scenario_id:
            visible_profile(db, scenario_id)
            stmt = stmt.where(
                Assessment.profile_version_id.in_(
                    select(ProfileVersion.id).where(
                        ProfileVersion.company_profile_id == scenario_id
                    )
                )
            )
        if cursor:
            stmt = stmt.where(tuple_(Assessment.created_at, Assessment.id) > cursor_decode(cursor))
        rows = db.scalars(stmt).all()
        return {
            "items": [assessment_response(a) for a in rows[:limit]],
            "next_cursor": next_cursor(rows[limit - 1]) if len(rows) > limit else None,
        }


@router.get("/assessments/compare", response_model=Page[AssessmentView])
def compare(ids: str, actor: ActorContext = Depends(get_actor)) -> dict[str, Any]:
    try:
        keys = [UUID(v) for v in ids.split(",")]
    except ValueError:
        raise HTTPException(422, "Ungültige Bewertungskennung.") from None
    if not 1 <= len(keys) <= 5 or len(set(keys)) != len(keys):
        raise HTTPException(422, "Ein bis fünf unterschiedliche Bewertungen auswählen.")
    with tenant_session(actor.organization_id) as db:
        rows = db.scalars(select(Assessment).where(Assessment.id.in_(keys))).all()
        if len(rows) != len(keys):
            raise HTTPException(404, "Mindestens eine Bewertung ist nicht verfügbar.")
        mapping = {r.id: r for r in rows}
        return {"items": [assessment_response(mapping[k]) for k in keys]}


@router.get("/assessments/{assessment_id}", response_model=AssessmentView)
def get_assessment(assessment_id: UUID, actor: ActorContext = Depends(get_actor)) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        row = db.get(Assessment, assessment_id)
        if not row:
            raise HTTPException(404, "Bewertung nicht gefunden.")
        return assessment_response(row)


@router.get("/audit-events", response_model=Page[AuditView])
def audit(
    actor: ActorContext = Depends(require_admin),
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = None,
) -> dict[str, Any]:
    with tenant_session(actor.organization_id) as db:
        stmt = select(AuditEvent).order_by(AuditEvent.created_at, AuditEvent.id).limit(limit + 1)
        if cursor:
            stmt = stmt.where(tuple_(AuditEvent.created_at, AuditEvent.id) > cursor_decode(cursor))
        rows = db.scalars(stmt).all()
        return {
            "items": [
                {
                    "id": str(r.id),
                    "created_at": r.created_at.isoformat(),
                    "actor_user_id": str(r.actor_user_id),
                    "event_type": r.event_type,
                    "entity_type": r.entity_type,
                    "entity_id": str(r.entity_id) if r.entity_id else None,
                    "metadata": r.event_metadata,
                }
                for r in rows[:limit]
            ],
            "next_cursor": next_cursor(rows[limit - 1]) if len(rows) > limit else None,
        }
