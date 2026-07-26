"""Blind verifier for impact-report (v2). Set equality against the harness-side truth."""

import hashlib
import json
import pathlib
import subprocess
import sys

ws = pathlib.Path(sys.argv[1])
truth = json.loads(
    (pathlib.Path(__file__).resolve().parent / "truth.json").read_text(encoding="utf-8")
)

crit = {}

raw = None
try:
    raw = json.loads((ws / "impact.json").read_text(encoding="utf-8"))
except Exception:
    raw = None

crit["report_present"] = isinstance(raw, list) and all(isinstance(x, str) for x in raw)

want = set(truth["call_closure_modules"])
got = set(raw) if crit["report_present"] else set()
crit["closure_exact"] = got == want
crit["no_false_positives"] = crit["report_present"] and not (got - want)
crit["no_omissions"] = crit["report_present"] and not (want - got)
crit["sorted_output"] = crit["report_present"] and raw == sorted(raw)

# read-only task: the corpus must be untouched
changed = []
for rel, wanted in truth["decoy_hashes"].items():
    try:
        body = (ws / rel).read_text(encoding="utf-8")
    except OSError:
        body = ""
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != wanted:
        changed.append(rel)
crit["sources_untouched"] = not changed

try:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=ws, capture_output=True, text=True, timeout=240
    )
    crit["tests_pass"] = r.returncode == 0
except Exception:
    crit["tests_pass"] = False

print(json.dumps(crit))
sys.exit(0 if all(crit.values()) else 1)
