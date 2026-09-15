"""Idempotente, rein synthetische Inhalte für den öffentlichen Recruiter-Demozugang."""

import os
from copy import deepcopy
from uuid import UUID

from sqlalchemy.orm import Session

from platform_app.data.engine import encode_table, parse_csv, profile
from platform_app.data.models import DataJob, Dataset, DataVersion
from platform_app.data.storage import PostgresBlobStore
from platform_app.decisions.demo import demo_scenario
from platform_app.decisions.engine import fingerprint
from platform_app.decisions.schemas import ScenarioInput
from platform_app.intake.models import AssetRecord, CompanyProfile, ProfileVersion, WorkloadRecord, now
from platform_app.shared.config import get_settings
from platform_app.shared.db import engine_for

ORG_ID = UUID("10000000-0000-4000-8000-000000000001")
CREATOR_ID = UUID("20000000-0000-4000-8000-000000000002")

PROFILE_A = UUID("31000000-0000-4000-8000-000000000001")
PROFILE_A_V1 = UUID("31100000-0000-4000-8000-000000000001")
PROFILE_A_V2 = UUID("31100000-0000-4000-8000-000000000002")
PROFILE_B = UUID("31000000-0000-4000-8000-000000000002")
PROFILE_B_V1 = UUID("31200000-0000-4000-8000-000000000001")

DATASET_ID = UUID("32000000-0000-4000-8000-000000000001")
DATA_JOB_ID = UUID("32100000-0000-4000-8000-000000000001")
DATA_VERSION_ID = UUID("32200000-0000-4000-8000-000000000001")


def _enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _add_version(
    db: Session,
    *,
    profile_row: CompanyProfile,
    version_id: UUID,
    version_no: int,
    payload: dict[str, object],
) -> None:
    body = ScenarioInput.model_validate(payload)
    data = body.model_dump(mode="json")
    version = ProfileVersion(
        id=version_id,
        organization_id=ORG_ID,
        company_profile_id=profile_row.id,
        created_by_user_id=CREATOR_ID,
        version_no=version_no,
        industry=body.company_profile.industry,
        employee_count=body.company_profile.employee_count,
        monthly_budget=body.company_profile.monthly_budget,
        content_hash=fingerprint(data),
        data=data,
    )
    db.add(version)
    db.flush()
    for workload in body.workloads:
        db.add(
            WorkloadRecord(
                organization_id=ORG_ID,
                profile_version_id=version.id,
                workload_key=workload.workload_key,
                name=workload.name,
                workload_type=workload.workload_type,
                data=workload.model_dump(mode="json"),
            )
        )
    for asset in body.infrastructure_assets:
        db.add(
            AssetRecord(
                organization_id=ORG_ID,
                profile_version_id=version.id,
                asset_key=asset.asset_key,
                asset_type=asset.asset_type,
                data=asset.model_dump(mode="json"),
            )
        )


def _seed_scenarios(db: Session) -> None:
    if db.get(CompanyProfile, PROFILE_A) is None:
        first = demo_scenario()
        second = deepcopy(first)
        second["company_profile"]["employee_count"] = 48
        second["company_profile"]["monthly_budget"] = "15000"
        second["workloads"][0]["user_count"] = 48
        second["workloads"].append(
            {
                "workload_key": "reporting-db",
                "name": "Reporting-Datenbank",
                "workload_type": "DATABASE",
                "user_count": 12,
                "vcpu_count": "8",
                "memory_gib": "32",
                "storage_gib": "600",
                "max_latency_ms": "35",
                "availability_percent": "99.9",
                "rto_seconds": 7200,
                "rpo_seconds": 1800,
                "sensitivity": "CONFIDENTIAL",
                "internet_dependency_allowed": True,
            }
        )
        row = CompanyProfile(
            id=PROFILE_A,
            organization_id=ORG_ID,
            created_by_user_id=CREATOR_ID,
            name=str(first["name"]),
            revision=2,
        )
        db.add(row)
        db.flush()
        _add_version(db, profile_row=row, version_id=PROFILE_A_V1, version_no=1, payload=first)
        _add_version(db, profile_row=row, version_id=PROFILE_A_V2, version_no=2, payload=second)

    if db.get(CompanyProfile, PROFILE_B) is None:
        payload = {
            "name": "Musterwerk: Kundenportal modernisieren",
            "company_profile": {
                "industry": "Industrie & Service",
                "employee_count": 120,
                "it_staff_fte": "4",
                "monthly_budget": "26000",
                "initial_budget": "65000",
                "currency": "EUR",
            },
            "workloads": [
                {
                    "workload_key": "customer-portal",
                    "name": "Kundenportal",
                    "workload_type": "WEB_APP",
                    "user_count": 850,
                    "vcpu_count": "12",
                    "memory_gib": "32",
                    "storage_gib": "180",
                    "max_latency_ms": "120",
                    "availability_percent": "99.9",
                    "rto_seconds": 3600,
                    "rpo_seconds": 900,
                    "sensitivity": "CONFIDENTIAL",
                    "internet_dependency_allowed": True,
                },
                {
                    "workload_key": "customer-data",
                    "name": "Kundendatenbank",
                    "workload_type": "DATABASE",
                    "user_count": 45,
                    "vcpu_count": "16",
                    "memory_gib": "64",
                    "storage_gib": "900",
                    "max_latency_ms": "25",
                    "availability_percent": "99.95",
                    "rto_seconds": 1800,
                    "rpo_seconds": 300,
                    "sensitivity": "RESTRICTED",
                    "internet_dependency_allowed": False,
                },
            ],
            "infrastructure_assets": [
                {
                    "asset_key": "legacy-hosts",
                    "name": "Bestehende Virtualisierungshosts",
                    "asset_type": "SERVER",
                    "quantity": 3,
                    "notes": "Synthetischer Altbestand für die Demoentscheidung.",
                }
            ],
            "requirements": {"region": "EU", "hard_budget": False},
        }
        row = CompanyProfile(
            id=PROFILE_B,
            organization_id=ORG_ID,
            created_by_user_id=CREATOR_ID,
            name=str(payload["name"]),
            revision=1,
        )
        db.add(row)
        db.flush()
        _add_version(db, profile_row=row, version_id=PROFILE_B_V1, version_no=1, payload=payload)


def _seed_dataset(db: Session) -> None:
    if db.get(Dataset, DATASET_ID) is not None:
        return
    original = (
        "monat,bereich,tickets,loesungszeit_stunden,sla_prozent,kosten_eur\n"
        "2026-01,Support,142,7.8,91.2,18400\n"
        "2026-02,Support,151,7.1,92.6,17950\n"
        "2026-03,Support,164,6.6,94.1,17620\n"
        "2026-04,Support,158,6.2,95.0,17180\n"
        "2026-05,Support,173,5.9,95.8,16940\n"
        "2026-06,Support,181,5.5,96.4,16600\n"
        "2026-01,Operations,88,11.4,86.0,23100\n"
        "2026-02,Operations,91,10.7,88.2,22600\n"
        "2026-03,Operations,97,9.9,90.1,21950\n"
        "2026-04,Operations,104,9.1,91.7,21400\n"
        "2026-05,Operations,99,8.6,93.0,20850\n"
        "2026-06,Operations,108,8.0,94.3,20100\n"
    ).encode("utf-8")
    table = parse_csv(original, ",")
    result = encode_table(table)
    data_profile = profile(table).model_dump(mode="json")
    store = PostgresBlobStore(db, ORG_ID)
    original_blob_id, original_hash = store.put(original)
    result_blob_id, result_hash = store.put(result)
    dataset = Dataset(
        id=DATASET_ID,
        organization_id=ORG_ID,
        created_by_user_id=CREATOR_ID,
        name="Service Operations – Demo-Kennzahlen",
        filename="service-operations-demo.csv",
        delimiter=",",
        original_blob_id=original_blob_id,
        original_hash=original_hash,
        original_bytes=len(original),
        current_version=1,
    )
    db.add(dataset)
    db.flush()
    job = DataJob(
        id=DATA_JOB_ID,
        organization_id=ORG_ID,
        dataset_id=DATASET_ID,
        created_by_user_id=CREATOR_ID,
        kind="IMPORT",
        status="SUCCEEDED",
        source_version=None,
        processing_mode="LEGACY",
        progress=100,
        progress_message="Synthetische Demo-Daten importiert.",
        processed_rows=len(table.rows),
        import_options={},
        steps=[],
        result_blob_id=result_blob_id,
        result_hash=result_hash,
        profile=data_profile,
        error=None,
        finished_at=now(),
    )
    db.add(job)
    db.flush()
    db.add(
        DataVersion(
            id=DATA_VERSION_ID,
            organization_id=ORG_ID,
            dataset_id=DATASET_ID,
            job_id=DATA_JOB_ID,
            blob_id=result_blob_id,
            created_by_user_id=CREATOR_ID,
            version_no=1,
            source_version=None,
            content_hash=result_hash,
            profile=data_profile,
            steps=[],
        )
    )


def main() -> None:
    settings = get_settings()
    if settings.environment not in {"demo", "development"}:
        raise RuntimeError("Recruiter-Demo-Seeding ist außerhalb einer Demo-/Entwicklungsumgebung gesperrt.")
    if not _enabled(os.environ.get("PUBLIC_DEMO_ACCESS_ENABLED")):
        print("Recruiter-Demo-Seeding übersprungen: öffentlicher Demo-Zugang ist deaktiviert.")
        return
    with Session(engine_for("migration")) as db, db.begin():
        _seed_scenarios(db)
        _seed_dataset(db)
    print("Recruiter-Demo-Inhalte sind bereit: 2 Szenarien, 1 versionierter Beispieldatensatz.")


if __name__ == "__main__":
    main()
