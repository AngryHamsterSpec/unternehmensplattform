"""Nur bei neuer Initialmigration: ORM-DDL als prüfbaren statischen Snapshot schreiben."""

from importlib import import_module
from pathlib import Path

from platform_app.shared.db import Base
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateIndex, CreateTable

for module in ("identity", "intake", "assessments", "explanations"):
    import_module("platform_app." + module + ".models")

root = Path(__file__).resolve().parents[1] / "apps/api/migrations/versions"
statements = []
for table in Base.metadata.sorted_tables:
    statements.append(str(CreateTable(table).compile(dialect=dialect())) + ";")
    for index in sorted(table.indexes, key=lambda index: index.name):
        statements.append(str(CreateIndex(index).compile(dialect=dialect())) + ";")
(root / "0001_schema.sql").write_text("\n".join(statements), encoding="utf8")

security = ["REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;"]
auth_only = {"users", "auth_sessions", "oidc_login_attempts", "auth_events"}
immutable = {
    "company_profile_versions",
    "workloads",
    "infrastructure_assets",
    "assessments",
    "architecture_candidates",
    "cost_estimate_lines",
    "agent_runs",
    "audit_events",
}
for table in Base.metadata.sorted_tables:
    name = table.name
    security.extend(
        [
            f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY;",
            f"ALTER TABLE {name} FORCE ROW LEVEL SECURITY;",
            f"CREATE POLICY migration_access ON {name} TO platform_migrator USING (true) WITH CHECK (true);",
        ]
    )
    if name in auth_only:
        security.append(
            f"CREATE POLICY identity_access ON {name} TO platform_auth USING (true) WITH CHECK (true);"
        )
        rights = "SELECT, INSERT" if name == "auth_events" else "SELECT, INSERT, UPDATE"
        security.append(f"GRANT {rights} ON {name} TO platform_auth;")
        continue
    column = "id" if name == "organizations" else "organization_id"
    predicate = f"{column} = NULLIF(current_setting('app.organization_id', true), '')::uuid"
    security.append(
        f"CREATE POLICY tenant_access ON {name} TO platform_app USING ({predicate}) WITH CHECK ({predicate});"
    )
    rights = (
        "SELECT"
        if name == "cost_catalog_versions"
        else "SELECT, INSERT"
        if name in immutable
        else "SELECT, INSERT, UPDATE"
    )
    if name == "membership_roles":
        rights += ", DELETE"
    if name == "organizations":
        security.extend(
            [
                f"GRANT SELECT ON {name} TO platform_app;",
                f"GRANT UPDATE (revision) ON {name} TO platform_app;",
            ]
        )
    else:
        security.append(f"GRANT {rights} ON {name} TO platform_app;")
    if name in {"organization_memberships", "membership_roles"}:
        security.append(
            f"CREATE POLICY own_membership ON {name} FOR SELECT TO platform_auth USING "
            "(user_id = NULLIF(current_setting('app.authenticated_user_id', true), '')::uuid);"
        )
        security.append(f"GRANT SELECT ON {name} TO platform_auth;")
security.extend(
    [
        (
            "CREATE POLICY own_organizations ON organizations FOR SELECT TO platform_auth USING "
            "(id IN (SELECT organization_id FROM organization_memberships WHERE status = 'ACTIVE'));"
        ),
        "GRANT SELECT ON organizations TO platform_auth;",
        "REVOKE CREATE ON SCHEMA public FROM PUBLIC;",
    ]
)
(root / "0001_security.sql").write_text("\n".join(security) + "\n", encoding="utf8")
print(f"Statischer Initialsnapshot: {len(Base.metadata.tables)} Tabellen und FORCE-RLS/Rechte.")
