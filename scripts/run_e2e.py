"""Echte Browserabnahme mit lokalen Demo-Zugangsdaten ohne Secret-Ausgabe.

--isolated kopiert nur gesperrte Frontend-Abhängigkeiten und E2E-Quellen in ein
temporäres Verzeichnis. Das vermeidet beschädigte OneDrive-Paketdateien.
"""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isolated", action="store_true")
    parser.add_argument("--grep", help="Nur passende Browserfälle ausführen (Playwright-Muster).")
    args = parser.parse_args()
    environment = os.environ.copy()
    password = dotenv_values(ROOT / ".env").get("DEMO_PASSWORD")
    if not password:
        raise SystemExit("Lokales Demo-Passwort fehlt. scripts/setup_local.py ausführen.")
    environment["DEMO_PASSWORD"] = password
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        candidate = (
            Path.home()
            / ".cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback/pnpm.cmd"
        )
        if candidate.is_file():
            pnpm = str(candidate)
    if not pnpm:
        raise SystemExit("pnpm 11.19.0 wird benötigt.")
    working = ROOT / "apps/web"
    if args.isolated:
        working = Path(tempfile.mkdtemp(prefix="unternehmensplattform-e2e-"))
        for name in (
            "package.json",
            "pnpm-lock.yaml",
            "pnpm-workspace.yaml",
            "playwright.config.ts",
        ):
            shutil.copyfile(ROOT / "apps/web" / name, working / name)
        shutil.copytree(ROOT / "apps/web/e2e", working / "e2e")
        installation = subprocess.run(
            [pnpm, "--dir", str(working), "install", "--frozen-lockfile"],
            env={**environment, "CI": "true"},
            check=False,
        )
        if installation.returncode:
            raise SystemExit(installation.returncode)
        print("Isolierte E2E-Arbeitskopie und Prüfartefakte: " + str(working), flush=True)
    result = subprocess.run(
        [
            pnpm,
            "--dir",
            str(working),
            "run",
            "test:e2e",
            *(["--grep", args.grep] if args.grep else []),
        ],
        env=environment,
        check=False,
    )
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
