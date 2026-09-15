"""Realer 1-GiB-Pfad durch Nginx, HTTP, PostgreSQL, Worker und Downloads.

Verwendet eine reguläre synthetische DB-Session in der lokalen Demo.
Erzeugt einen Datensatz; keine echten Dateien oder Zugangsdaten im Bericht.
"""

import json
import subprocess
import sys
from pathlib import Path


def inside():
    import hashlib
    import time
    from datetime import UTC, datetime
    from uuid import UUID

    import httpx
    from platform_app.identity.models import User
    from platform_app.identity.router import create_session
    from platform_app.identity.security import cookie_name
    from platform_app.shared.config import get_settings
    from platform_app.shared.db import auth_session

    settings = get_settings()
    if settings.environment not in {"demo", "test"} or not settings.http_demo_mode:
        raise RuntimeError("Diese Prüfung ist ausschließlich für die lokale synthetische Demo.")
    total = 1073741824
    chunk_bytes = 4194304
    org = UUID("10000000-0000-4000-8000-000000000002")
    uid = UUID("20000000-0000-4000-8000-000000000004")
    with auth_session() as db:
        token, csrf = create_session(db, db.get(User, uid), org)
    client = httpx.Client(
        base_url="http://web:8080",
        timeout=240,
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

    def api(method, path, **kwargs):
        response = client.request(method, "/api/v1" + path, **kwargs)
        if response.status_code not in {200, 201, 202}:
            raise RuntimeError(f"CSV-Prüfung: HTTP {response.status_code}")
        return response.json()

    def event(value):
        print(json.dumps(value, ensure_ascii=False), flush=True)

    started = time.perf_counter()
    upload = api(
        "POST",
        "/data-uploads",
        json={
            "name": "Synthetischer 1-GiB-Nachweis",
            "filename": "synthetisch-1gib.csv",
            "total_bytes": total,
            "delimiter": ";",
        },
    )
    buffer = bytearray(b"ID;Betrag;Kategorie;Notiz\n")
    generated, rows, ordinal = len(buffer), 0, 0
    digest = hashlib.sha256()
    while generated < total:
        size = min(4096, total - generated)
        prefix = f"{rows:08d};1.25;A;".encode()
        assert size > len(prefix)
        row = prefix + b"x" * (size - len(prefix) - 1) + b"\n"
        buffer.extend(row)
        generated += len(row)
        rows += 1
        if len(buffer) >= chunk_bytes or generated == total:
            content = bytes(buffer[:chunk_bytes])
            del buffer[:chunk_bytes]
            digest.update(content)
            api("PUT", f"/data-uploads/{upload['id']}/chunks/{ordinal}", content=content)
            ordinal += 1
            if ordinal % 32 == 0:
                event(
                    {
                        "phase": "upload",
                        "bytes": ordinal * chunk_bytes,
                        "seconds": round(time.perf_counter() - started, 2),
                    }
                )
    if buffer:
        content = bytes(buffer)
        digest.update(content)
        api("PUT", f"/data-uploads/{upload['id']}/chunks/{ordinal}", content=content)
        ordinal += 1
    upload_seconds = time.perf_counter() - started
    job = api("POST", f"/data-uploads/{upload['id']}/complete")
    finalized_seconds = time.perf_counter() - started
    did = job["dataset_id"]
    event(
        {
            "phase": "processing",
            "dataset_id": did,
            "job_id": job["id"],
            "input_rows": rows,
        }
    )
    deadline = time.monotonic() + 3600
    previous = None
    while time.monotonic() < deadline:
        job = api("GET", f"/datasets/{did}/jobs/{job['id']}")
        progress = (job["status"], job["progress"], job["progress_message"])
        if progress != previous:
            event(
                {
                    "phase": "processing",
                    "status": job["status"],
                    "progress": job["progress"],
                    "message": job["progress_message"],
                    "seconds": round(time.perf_counter() - started, 2),
                }
            )
            previous = progress
        if job["status"] in {"FAILED", "CANCELLED"}:
            raise RuntimeError("Großer Import fehlgeschlagen: " + str(job["error"]))
        if job["status"] == "SUCCEEDED":
            break
        time.sleep(5)
    else:
        raise RuntimeError("Das Zeitbudget der Messung wurde überschritten.")
    processing_seconds = time.perf_counter() - started - finalized_seconds
    assert job["profile"]["rows"] == rows
    assert job["profile"]["duplicate_rows"] == 0
    assert job["profile"]["columns"][1]["mean"] == "1.250000"
    detail = api("GET", f"/datasets/{did}")
    assert detail["original_bytes"] == total and detail["original_hash"] == digest.hexdigest()
    downloaded = hashlib.sha256()
    original_bytes = 0
    with client.stream("GET", f"/api/v1/datasets/{did}/original") as response:
        assert response.status_code == 200
        for part in response.iter_bytes(chunk_size=1048576):
            original_bytes += len(part)
            downloaded.update(part)
    assert original_bytes == total and downloaded.hexdigest() == digest.hexdigest()
    page = api("GET", f"/datasets/{did}/versions/1/rows?offset={rows - 25}")
    assert len(page["rows"]) == 25 and page["total"] == rows
    exported = hashlib.sha256()
    exported_bytes = 0
    with client.stream("GET", f"/api/v1/datasets/{did}/versions/1/export") as response:
        assert response.status_code == 200
        expected_export_hash = response.headers["X-Content-SHA256"]
        for part in response.iter_bytes(chunk_size=1048576):
            exported_bytes += len(part)
            exported.update(part)
    assert exported.hexdigest() == expected_export_hash
    client.close()
    event(
        {
            "result": "passed",
            "measured_at": datetime.now(UTC).isoformat(),
            "input_bytes": total,
            "input_rows": rows,
            "chunks": ordinal,
            "original_sha256": digest.hexdigest(),
            "original_download_bytes": original_bytes,
            "export_bytes": exported_bytes,
            "export_sha256": exported.hexdigest(),
            "dataset_id": did,
            "upload_seconds": round(upload_seconds, 3),
            "finalize_seconds": round(finalized_seconds - upload_seconds, 3),
            "processing_seconds": round(processing_seconds, 3),
            "total_seconds": round(time.perf_counter() - started, 3),
            "scope": "Realer lokaler Nginx/HTTP/PostgreSQL/Worker-Pfad mit synthetischer DB-Session; OIDC separat im Browser geprüft.",
        }
    )
    return 0


def main():
    if "--inside" in sys.argv:
        return inside()
    root = Path(__file__).resolve().parents[1]
    report = root / ".local" / "large-csv-benchmark.jsonl"
    with subprocess.Popen(
        ["docker", "compose", "exec", "-T", "api", "python", "-", "--inside"],
        cwd=root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ) as process:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(Path(__file__).read_bytes())
        process.stdin.close()
        with report.open("w", encoding="utf8") as output:
            for line in process.stdout:
                value = line.decode("utf8")
                output.write(value)
                output.flush()
                print(value.rstrip(), flush=True)
        code = process.wait()
        if code:
            raise RuntimeError(
                "Die 1-GiB-Prüfung ist fehlgeschlagen; Datenauftrag und Containerzustand prüfen."
            )
        return code


if __name__ == "__main__":
    raise SystemExit(main())
