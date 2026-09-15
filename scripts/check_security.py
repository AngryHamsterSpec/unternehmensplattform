"""Prüft nur Projektquellen und die vier ausdrücklich benannten Demo-Images.



Keine Hostsocket-Freigabe an den Scanner. Trivy liest lokale Image-Archive.

Rohberichte können Test-Fixtures enthalten und verbleiben unter .local/security.

"""

import argparse
import hashlib
import json
import secrets
import shutil
import string
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from security_policy import disposition, local_http_deployment

ROOT = Path(__file__).resolve().parents[1]

IMAGES = {
    "api": "unternehmensplattform-api:0.1.0",
    "web": "unternehmensplattform-web:0.1.0",
    "postgres": "unternehmensplattform-postgres:18.6-p1",
    "keycloak": "quay.io/keycloak/keycloak:26.7.3@sha256:ff4257d0d64efbe99ed1ddfaf07765cc3c36dc7518bf8324d41961327f441c54",
}


def findings(report):

    results = report.get("Results", [])

    return {
        "secrets": sum(len(item.get("Secrets") or []) for item in results),
        "vulnerabilities": [
            {
                "id": finding["VulnerabilityID"],
                "package": finding["PkgName"],
                "installed": finding["InstalledVersion"],
                "fixed": finding.get("FixedVersion"),
                "severity": finding["Severity"],
                "path": finding.get("PkgPath"),
            }
            for item in results
            for finding in item.get("Vulnerabilities") or []
        ],
    }


def main():

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--sources-only", action="store_true")

    args = parser.parse_args()

    installation = json.loads((ROOT / ".local/scanner-install.json").read_text(encoding="utf8"))

    executable = Path(installation["path"])

    if hashlib.sha256(executable.read_bytes()).hexdigest() != installation["binary_sha256"]:
        raise RuntimeError("Das Prüfprogramm wurde seit der Installation verändert.")

    directory = ROOT / ".local/security" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    source = directory / "source"

    source.mkdir(parents=True, exist_ok=False)

    listed = (
        subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
        .stdout.decode()
        .split("\0")
    )

    for name in set(filter(None, listed)):
        relative = Path(name)

        if not (ROOT / relative).is_file():
            continue

        if not (ROOT / relative).resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError("Quellpfad verlässt das Projekt.")

        target = source / relative

        target.parent.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(ROOT / relative, target)

    fixture = directory / "fixture"

    fixture.mkdir()

    fake = "ghp_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36))

    (fixture / "secret.txt").write_text("GITHUB_TOKEN=" + fake, encoding="utf8")

    (fixture / "package-lock.json").write_text(
        json.dumps(
            {
                "name": "scanner-fixture",
                "version": "0.0.0",
                "lockfileVersion": 1,
                "dependencies": {"axios": {"version": "0.21.0"}},
            }
        ),
        encoding="utf8",
    )

    def scan(name, *arguments):

        output = directory / (name + ".json")

        print("Sicherheitsprüfung: " + name, flush=True)

        process = subprocess.run(
            [
                str(executable),
                *arguments,
                "--format",
                "json",
                "--output",
                str(output),
                "--cache-dir",
                str(ROOT / ".local/trivy-cache"),
                "--timeout",
                "10m",
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=660,
            check=False,
        )

        if process.returncode:
            # Keine fremden Scannertexte/gefundenen Geheimnisse in regulären Logs.

            raise RuntimeError("Scanner konnte die Prüfung nicht abschließen: " + name)

        return findings(json.loads(output.read_text(encoding="utf8")))

    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "trivy": installation["version"],
    }

    probe = scan("fixture", "filesystem", "--scanners", "vuln,secret", str(fixture))

    if probe["secrets"] < 1 or not probe["vulnerabilities"]:
        raise RuntimeError("Scanner erkennt die bekannte Secret-/Schwachstellen-Fixture nicht.")

    report["fixture_detected"] = True

    report["sources"] = scan("sources", "filesystem", "--scanners", "vuln,secret", str(source))

    report["images"] = {}

    if not args.sources_only:
        for name, image in IMAGES.items():
            archive = directory / (name + ".tar")

            subprocess.run(
                ["docker", "image", "save", "--output", str(archive), image],
                check=True,
                timeout=240,
            )

            report["images"][name] = scan(
                name, "image", "--scanners", "vuln,secret", "--input", str(archive)
            )

    checks = [report["sources"], *report["images"].values()]

    report["secrets_found"] = sum(check["secrets"] for check in checks)

    report["fixable_high_or_critical"] = sum(
        finding["severity"] in {"HIGH", "CRITICAL"} and bool(finding["fixed"])
        for check in checks
        for finding in check["vulnerabilities"]
    )

    # Compose enthält Geheimnisse: nur im Speicher prüfen, niemals ausgeben.

    config = (
        json.loads(
            subprocess.run(
                ["docker", "compose", "config", "--format", "json"],
                cwd=ROOT,
                capture_output=True,
                check=True,
            ).stdout
        )
        if not args.sources_only
        else {}
    )

    local_http = local_http_deployment(config)

    report["local_http_deployment_confirmed"] = local_http

    report["reviewed_findings"] = []

    for name, check in report["images"].items():
        for finding in check["vulnerabilities"]:
            if finding["severity"] not in {"HIGH", "CRITICAL"} or not finding["fixed"]:
                continue

            review = disposition(
                finding,
                IMAGES[name],
                local_http=local_http,
                today=datetime.now(UTC).date(),
            )

            if review:
                report["reviewed_findings"].append({"image": name, **finding, **review})

    report["actionable_fixable_high_or_critical"] = report["fixable_high_or_critical"] - len(
        report["reviewed_findings"]
    )

    report["unfixed_high_or_critical"] = sum(
        finding["severity"] in {"HIGH", "CRITICAL"} and not finding["fixed"]
        for check in checks
        for finding in check["vulnerabilities"]
    )

    report["gate_passed"] = (
        report["secrets_found"] == 0 and report["actionable_fixable_high_or_critical"] == 0
    )

    (directory / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf8")

    print("Sanitisierter Prüfbericht: " + str(directory / "summary.json"), flush=True)

    if not report["gate_passed"]:
        raise SystemExit("Sicherheitsgate offen: Funde im Prüfbericht bearbeiten.")


if __name__ == "__main__":
    main()
