"""Prüft interne Markdown-Dateilinks und Pflichtdokumentation ohne Netzaufrufe."""

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", ".local", ".pnpm-store", "node_modules", "dist"}
required = [
    ROOT / "docs" / name
    for name in (
        "PROJECT_CHARTER.md",
        "STATUS.md",
        "PHASE_1_SPEC.md",
        "testing/PHASE_1_REPORT.md",
    )
]
required += [
    ROOT / "apps/api/src/platform_app" / module / name
    for module in ("identity", "intake", "decisions", "assessments", "explanations", "data")
    for name in ("README.md", "EXPLAIN.md", "TESTING.md")
]
failures = [f"Pflichtdatei fehlt: {p.relative_to(ROOT)}" for p in required if not p.is_file()]
files = []
for current, directories, names in os.walk(ROOT):
    directories[:] = [name for name in directories if name not in SKIP]
    files.extend(Path(current) / name for name in names if name.endswith(".md"))
count = 0
for path in files:
    body = path.read_text(encoding="utf-8-sig")
    # Codebeispiele und historische Originalprompts sind keine Navigationslinks.
    if path.parent.name == "requirements":
        continue
    body = re.sub(r"```[\s\S]*?```", "", body)
    for match in re.finditer(r"\[[^\]\n]*\]\(([^)\n]+)\)", body):
        target = match.group(1).strip().strip("<>")
        if urlsplit(target).scheme or target.startswith("#"):
            continue
        target = unquote(target.split("#")[0])
        if target and not (path.parent / target).exists():
            failures.append(f"{path.relative_to(ROOT)}: fehlendes Linkziel {target}")
        count += 1
if failures:
    raise SystemExit("\n".join(failures))
print(f"{len(files)} Markdown-Dateien, {count} interne Links und Modulpflichtdateien geprüft.")
