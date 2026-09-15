"""Installiert das feste offizielle Trivy-Release nach SHA-256-Prüfung lokal.

Entpackt ausschließlich die einzelne ausführbare Datei, ohne globale Installation.
"""

import hashlib
import io
import json
import os
import platform
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "0.74.0"
ROOT = Path(__file__).resolve().parents[1]


def download(url):
    with urllib.request.urlopen(url, timeout=90) as response:
        return response.read()


def main():
    if platform.machine().lower() not in {"amd64", "x86_64"}:
        raise SystemExit("Dieser Installer ist bislang nur für AMD64 ausgearbeitet.")
    windows = platform.system() == "Windows"
    filename = f"trivy_{VERSION}_" + ("windows-64bit.zip" if windows else "Linux-64bit.tar.gz")
    base = f"https://github.com/aquasecurity/trivy/releases/download/v{VERSION}/"
    checksums = download(base + f"trivy_{VERSION}_checksums.txt").decode()
    expected = next(line.split()[0] for line in checksums.splitlines() if line.endswith(filename))
    content = download(base + filename)
    actual = hashlib.sha256(content).hexdigest()
    if actual != expected:
        raise RuntimeError("Prüfsumme stimmt nicht überein.")
    destination = Path(tempfile.gettempdir()) / "unternehmensplattform-tools" / ("trivy-" + VERSION)
    destination.mkdir(parents=True, exist_ok=True)
    executable = destination / ("trivy.exe" if windows else "trivy")
    if windows:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            executable.write_bytes(archive.read("trivy.exe"))
    else:
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
            entry = archive.extractfile("trivy")
            if entry is None:
                raise RuntimeError("Prüfprogramm fehlt im Archiv.")
            executable.write_bytes(entry.read())
    os.chmod(executable, 0o700)
    report = {
        "version": VERSION,
        "archive_sha256": actual,
        "binary_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "path": str(executable),
        "source": base + filename,
    }
    (ROOT / ".local").mkdir(exist_ok=True)
    (ROOT / ".local/scanner-install.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print("Offizielles Trivy-Release und SHA-256 geprüft; lokales Prüfwerkzeug bereit.")


if __name__ == "__main__":
    main()
