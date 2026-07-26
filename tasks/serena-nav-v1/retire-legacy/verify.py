"""Blind verifier for retire-legacy. Reads only argv[1] (result-view)."""

import json
import pathlib
import re
import subprocess
import sys

ws = pathlib.Path(sys.argv[1])

crit = {}

offenders = []
for p in sorted(ws.rglob("*.py")):
    rel = p.relative_to(ws).as_posix()
    if rel.startswith("ledgerline/legacy/"):
        continue
    try:
        txt = p.read_text(encoding="utf-8")
    except OSError:
        continue
    if "oldapi" in txt:
        offenders.append(rel)
crit["no_internal_legacy_refs"] = not offenders

try:
    old_src = (ws / "ledgerline/legacy/oldapi.py").read_text(encoding="utf-8")
except OSError:
    old_src = ""
crit["module_preserved"] = bool(
    re.search(r"def settle\(entries", old_src) and re.search(r"def legacy_total\(entries", old_src)
)

try:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=ws, capture_output=True, text=True, timeout=120
    )
    crit["tests_pass"] = r.returncode == 0
except Exception:
    crit["tests_pass"] = False

print(json.dumps(crit))
sys.exit(0 if all(crit.values()) else 1)
