"""Schreibfreigabe innerhalb derselben Transaktion wie die Fachänderung."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_app.identity.dependencies import ActorContext
from platform_app.identity.models import MembershipRole, Organization, OrganizationMembership


def check_write(db: Session, actor: ActorContext) -> None:
    organization = db.scalar(
        select(Organization).where(Organization.id == actor.organization_id).with_for_update()
    )
    member = db.get(OrganizationMembership, (actor.organization_id, actor.user_id))
    roles = db.scalars(
        select(MembershipRole.role_code).where(
            MembershipRole.organization_id == actor.organization_id,
            MembershipRole.user_id == actor.user_id,
        )
    ).all()
    if (
        organization is None
        or organization.status != "ACTIVE"
        or member is None
        or member.status != "ACTIVE"
        or not set(roles) & {"ORG_ADMIN", "ARCHITECTURE_ANALYST"}
    ):
        raise HTTPException(403, "Die Schreibberechtigung wurde entzogen.")
