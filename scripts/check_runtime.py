"""Prüft nur Laufzeitgrenzen und einen kurzen DB-Ausfall der lokalen Demo."""

import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def docker(*args):
    result = subprocess.run(
        ["docker", *args], cwd=ROOT, capture_output=True, timeout=180, check=False
    )
    if result.returncode:
        raise RuntimeError(
            "Lokale Laufzeitprüfung fehlgeschlagen; Docker-Ausgaben bleiben vertraulich."
        )
    return result.stdout


def health(path):
    try:
        with urllib.request.urlopen(
            "http://localhost:8080/api/v1/health/" + path, timeout=15
        ) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (OSError, TimeoutError):
        return 0


def main():
    config = json.loads(docker("compose", "config", "--format", "json"))
    env = config["services"]["api"]["environment"]
    if env.get("ENVIRONMENT") != "demo" or env.get("PUBLIC_ORIGIN") != "http://localhost:8080":
        raise RuntimeError("Diese Prüfung ist ausschließlich für die lokale Demo freigegeben.")
    report = {"checked_at": datetime.now(UTC).isoformat(), "containers": {}}
    for service in ("api", "web", "keycloak", "postgres", "data-worker", "intelligence-worker"):
        cid = docker("compose", "ps", "-q", service).decode().strip()
        item = json.loads(docker("inspect", cid))[0]
        facts = {
            "image_id": item["Image"],
            "configured_user": item["Config"].get("User"),
            "privileged": item["HostConfig"]["Privileged"],
            "read_only": item["HostConfig"]["ReadonlyRootfs"],
            "published_ports": item["NetworkSettings"].get("Ports"),
            "host_socket_mounted": any("docker.sock" in m["Destination"] for m in item["Mounts"]),
        }
        assert not facts["privileged"] and not facts["host_socket_mounted"]
        if service in {"api", "web", "keycloak", "data-worker", "intelligence-worker"}:
            assert facts["configured_user"] not in {"", "0", "root"}
        if service in {"api", "web", "data-worker", "intelligence-worker"}:
            assert facts["read_only"]
        for bindings in (facts["published_ports"] or {}).values():
            for binding in bindings or []:
                assert (
                    service == "web"
                    and binding["HostIp"] == "127.0.0.1"
                    and binding["HostPort"] == "8080"
                )
        if service in {"data-worker", "intelligence-worker"}:
            assert item["HostConfig"]["Memory"] == 268435456
            assert item["HostConfig"]["NanoCpus"] == 1000000000
            expected_networks = {"unternehmensplattform_data"}
            if service == "intelligence-worker":
                expected_networks.add("unternehmensplattform_egress")
            assert set(item["NetworkSettings"]["Networks"]) == expected_networks
            names = {entry.split("=", 1)[0] for entry in item["Config"]["Env"]}
            assert not names & {
                "AUTH_DATABASE_URL",
                "MIGRATION_DATABASE_URL",
                "OIDC_CLIENT_SECRET",
                "SESSION_SECRET",
                "OPENAI_API_KEY",
            }
            facts["memory_bytes"] = item["HostConfig"]["Memory"]
            facts["cpu_limit"] = 1
            facts["internal_network_only"] = service == "data-worker"
            facts["no_identity_or_model_credentials"] = True
            work_mounts = [m for m in item["Mounts"] if m["Destination"] == "/work"]
            assert (
                len(work_mounts) == 1
                and work_mounts[0]["Type"] == "volume"
                and work_mounts[0]["RW"]
            )
            assert "SQLITE_TMPDIR=/work" in item["Config"]["Env"]
            facts["scratch_on_disk_volume"] = True
            facts["sqlite_temporary_files_on_disk"] = True
        report["containers"][service] = facts
    users = docker("compose", "exec", "-T", "postgres", "sh", "-c", "ps -o user,comm").decode()
    assert any("postgres" in line and line.split()[0] == "postgres" for line in users.splitlines())
    assert health("ready") == 200
    start = time.perf_counter()
    try:
        docker("compose", "stop", "postgres")
        report["database_down_readiness"] = health("ready")
        report["database_down_liveness"] = health("live")
        assert report["database_down_readiness"] == 503
        assert report["database_down_liveness"] == 200
    finally:
        docker("compose", "up", "-d", "--wait", "--wait-timeout", "120", "postgres")
        deadline = time.monotonic() + 90
        while health("ready") != 200:
            if time.monotonic() > deadline:
                raise RuntimeError("Demo nach DB-Ausfall noch nicht bereit.")
            time.sleep(1)
    report["recovered"] = True
    report["exercise_seconds"] = round(time.perf_counter() - start, 3)
    (ROOT / ".local/runtime-boundaries.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("Containergrenzen, DB-Ausfall (503), Liveness (200) und Wiederanlauf erfolgreich.")


if __name__ == "__main__":
    main()
