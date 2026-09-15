"""Idempotente synthetische Identitäts-/Katalogdaten; nur Migrationsrolle."""

from uuid import UUID

from sqlalchemy.orm import Session

from platform_app.assessments.models import CostCatalog
from platform_app.decisions.catalog import catalog_metadata
from platform_app.decisions.engine import fingerprint
from platform_app.identity.models import MembershipRole, Organization, OrganizationMembership, User
from platform_app.shared.config import get_settings
from platform_app.shared.db import engine_for

ORGS = [
    ("10000000-0000-4000-8000-000000000001", "Musterwerk IT", "musterwerk"),
    ("10000000-0000-4000-8000-000000000002", "Testmandant B", "testmandant-b"),
]
USERS = [
    ("20000000-0000-4000-8000-000000000001", "Demo Administration", "ORG_ADMIN", 0),
    ("20000000-0000-4000-8000-000000000002", "Demo Architektur", "ARCHITECTURE_ANALYST", 0),
    ("20000000-0000-4000-8000-000000000003", "Demo Lesekonto", "VIEWER", 0),
    ("20000000-0000-4000-8000-000000000004", "Demo Testmandant B", "ORG_ADMIN", 1),
]


def main() -> None:
    settings = get_settings()
    if settings.environment not in {"demo", "test", "development"}:
        raise RuntimeError("Demo-Seeding ist in diesem Betriebsmodus gesperrt.")
    with Session(engine_for("migration")) as db, db.begin():
        for identifier, name, slug in ORGS:
            if db.get(Organization, UUID(identifier)) is None:
                db.add(Organization(id=UUID(identifier), name=name, slug=slug))
        db.flush()
        for identifier, name, role, org in USERS:
            uid, oid = UUID(identifier), UUID(ORGS[org][0])
            if db.get(User, uid) is None:
                db.add(
                    User(
                        id=uid,
                        oidc_issuer=settings.oidc_issuer,
                        oidc_subject=identifier,
                        display_name=name,
                    )
                )
                db.flush()
                db.add(OrganizationMembership(organization_id=oid, user_id=uid))
                db.flush()
                db.add(MembershipRole(organization_id=oid, user_id=uid, role_code=role))
        db.flush()
        catalog = catalog_metadata()
        from sqlalchemy import select

        for identifier, _, _ in ORGS:
            oid = UUID(identifier)
            existing = db.scalar(
                select(CostCatalog).where(
                    CostCatalog.organization_id == oid, CostCatalog.version == catalog["version"]
                )
            )
            if existing is None:
                db.add(
                    CostCatalog(
                        organization_id=oid,
                        version=catalog["version"],
                        content_hash=fingerprint(catalog),
                        data=catalog,
                    )
                )
            elif existing.content_hash != fingerprint(catalog):
                raise RuntimeError(
                    "Ein veröffentlichter Katalog wurde verändert. Neue Version erforderlich."
                )
    print("Synthetische Demo-Identitäten und Kataloge sind bereit.")


if __name__ == "__main__":
    main()
