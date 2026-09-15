"""Versionierte Eingaben und atomare Auditierung."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_app.decisions.engine import fingerprint
from platform_app.decisions.schemas import ScenarioInput
from platform_app.identity.dependencies import ActorContext
from platform_app.intake.models import AssetRecord, CompanyProfile, ProfileVersion, WorkloadRecord
from platform_app.shared.audit import append_audit


def save_version(
    db: Session, actor: ActorContext, body: ScenarioInput, profile: CompanyProfile, number: int
) -> ProfileVersion:
    if profile.organization_id != actor.organization_id:
        raise HTTPException(404, "Szenario nicht gefunden.")
    data = body.model_dump(mode="json")
    version = ProfileVersion(
        id=uuid4(),
        organization_id=actor.organization_id,
        company_profile_id=profile.id,
        created_by_user_id=actor.user_id,
        version_no=number,
        industry=body.company_profile.industry,
        employee_count=body.company_profile.employee_count,
        monthly_budget=body.company_profile.monthly_budget,
        content_hash=fingerprint(data),
        data=data,
    )
    db.add(version)
    db.flush()
    for w in body.workloads:
        db.add(
            WorkloadRecord(
                organization_id=actor.organization_id,
                profile_version_id=version.id,
                workload_key=w.workload_key,
                name=w.name,
                workload_type=w.workload_type,
                data=w.model_dump(mode="json"),
            )
        )
    for a in body.infrastructure_assets:
        db.add(
            AssetRecord(
                organization_id=actor.organization_id,
                profile_version_id=version.id,
                asset_key=a.asset_key,
                asset_type=a.asset_type,
                data=a.model_dump(mode="json"),
            )
        )
    append_audit(
        db,
        actor,
        "scenario.version_created",
        "scenario",
        profile.id,
        {"version": number, "content_hash": version.content_hash},
    )
    return version


def scenario_response(
    db: Session, profile: CompanyProfile, versions: Sequence[ProfileVersion] | None = None
) -> dict[str, Any]:
    versions = (
        versions
        if versions is not None
        else db.scalars(
            select(ProfileVersion)
            .where(
                ProfileVersion.organization_id == profile.organization_id,
                ProfileVersion.company_profile_id == profile.id,
            )
            .order_by(ProfileVersion.version_no.desc())
        ).all()
    )
    if not versions:
        raise HTTPException(503, "Das Szenario enthält keinen vollständigen gespeicherten Stand.")
    current = versions[0]
    return {
        "id": str(profile.id),
        "name": profile.name,
        "current_version": current.version_no,
        "created_at": profile.created_at.isoformat(),
        "version": {"id": str(current.id), "version_no": current.version_no, "data": current.data},
        "versions": [
            {"id": str(v.id), "version_no": v.version_no, "created_at": v.created_at.isoformat()}
            for v in versions
        ],
    }


def visible_profile(db: Session, profile_id: UUID) -> CompanyProfile:
    profile = db.get(CompanyProfile, profile_id)
    if profile is None:
        raise HTTPException(404, "Szenario nicht gefunden.")
    return profile
