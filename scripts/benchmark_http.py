"""Misst den echten lokalen HTTP-/PostgreSQL-Pfad mit zehn parallelen Sessions.

Erzeugt 100 zusätzliche synthetische Szenarien im Demo-Mandanten. Kein
Auth-Bypass im Server: Die lokale Testfixture verwendet reguläre DB-Sessions.
"""

import json
import math
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def inside():
    import os
    import platform
    from concurrent.futures import ThreadPoolExecutor
    from time import perf_counter
    from uuid import UUID, uuid4

    import httpx
    from platform_app.decisions import demo_scenario
    from platform_app.decisions.schemas import ScenarioInput
    from platform_app.identity.dependencies import ActorContext
    from platform_app.identity.models import User
    from platform_app.identity.router import create_session
    from platform_app.identity.security import cookie_name
    from platform_app.intake.models import CompanyProfile
    from platform_app.intake.service import save_version
    from platform_app.shared.authorization import check_write
    from platform_app.shared.config import get_settings
    from platform_app.shared.db import auth_session, tenant_session
    from sqlalchemy import func, select

    settings = get_settings()
    if settings.environment not in {"demo", "test"} or not settings.http_demo_mode:
        raise RuntimeError("Lasttest ist ausschließlich in der lokalen Demo erlaubt.")
    org = UUID("10000000-0000-4000-8000-000000000002")
    uid = UUID("20000000-0000-4000-8000-000000000004")
    actor = ActorContext(uid, org, frozenset({"ORG_ADMIN"}), "Lasttest")
    clients = []
    with auth_session() as db:
        user = db.get(User, uid)
        for _ in range(10):
            token, csrf = create_session(db, user, org)
            clients.append(
                httpx.Client(
                    base_url="http://web:8080",
                    timeout=30,
                    headers={
                        "Host": "localhost:8080",
                        "Origin": settings.public_origin,
                        "X-CSRF-Token": csrf,
                    },
                    cookies={
                        cookie_name(settings, "session"): token,
                        cookie_name(settings, "csrf"): csrf,
                    },
                )
            )
    profiles = []
    versions = []
    with tenant_session(org) as db:
        check_write(db, actor)
        for index in range(100):
            data = ScenarioInput.model_validate(
                {**demo_scenario(), "name": f"Lasttest {uuid4().hex[:8]} {index}"}
            )
            profile = CompanyProfile(
                id=uuid4(), organization_id=org, created_by_user_id=uid, name=data.name
            )
            db.add(profile)
            db.flush()
            version = save_version(db, actor, data, profile, 1)
            db.flush()
            profiles.append(str(profile.id))
            versions.append(str(version.id))
        count = db.scalar(select(func.count()).select_from(CompanyProfile))

    def worker(index):
        client = clients[index]
        timings = {"read": [], "list": [], "assessment": []}

        def measure(kind, method, path, **kwargs):
            start = perf_counter()
            response = client.request(method, path, **kwargs)
            elapsed = (perf_counter() - start) * 1000
            if response.status_code not in {200, 201}:
                raise RuntimeError(f"Lasttest: HTTP {response.status_code} bei {kind}")
            if kind == "assessment" and response.json()["status"] != "VERIFIED":
                raise RuntimeError("Lasttest-Bewertung ist nicht verifiziert.")
            timings[kind].append(elapsed)

        for offset in range(10):
            measure("read", "GET", "/api/v1/scenarios/" + profiles[index * 10 + offset])
        measure("list", "GET", "/api/v1/scenarios?limit=25")
        measure(
            "assessment",
            "POST",
            "/api/v1/assessments",
            json={
                "scenario_version_id": versions[index * 10],
                "valuation_date": "2026-09-10",
            },
            headers={"Idempotency-Key": str(uuid4())},
        )
        return timings

    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(worker, range(10)))
    finally:
        for client in clients:
            client.close()

    def stats(name):
        values = sorted(value for result in results for value in result[name])
        return {
            "samples": len(values),
            "p95_ms": round(values[math.ceil(len(values) * 0.95) - 1], 3),
            "max_ms": round(max(values), 3),
        }

    report = {
        "measured_at": datetime.now(UTC).isoformat(),
        "scope": "Echter Nginx/HTTP/API/PostgreSQL-Pfad, zehn parallele Sessions einer synthetischen Administrationsidentität in Testmandant B",
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "visible_cpus": os.cpu_count(),
        "organization_scenarios": count,
        "created_scenarios": 100,
        "concurrent_sessions": 10,
        "read": stats("read"),
        "list": stats("list"),
        "assessment": stats("assessment"),
    }
    report["target_met"] = (
        report["read"]["p95_ms"] < 500
        and report["list"]["p95_ms"] < 500
        and report["assessment"]["p95_ms"] < 2000
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["target_met"] else 1


def main():
    if "--inside" in sys.argv:
        return inside()
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-", "--inside"],
        input=Path(__file__).read_bytes(),
        cwd=root,
        capture_output=True,
        check=False,
        timeout=300,
    )
    if result.stdout:
        report = json.loads(result.stdout)
        (root / ".local/http-benchmark.json").write_text(
            json.dumps(report, indent=2), encoding="utf8"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        raise RuntimeError(
            "HTTP-Lastprüfung fehlgeschlagen; keine Messwerte. "
            + result.stderr.decode(errors="replace")[-1000:]
        )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
