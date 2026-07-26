"""Blind verifier for disambiguate-fee (v2).

Behavioral, not textual: 10.0 * 0.125 == 1.25, which round(_, 1) collapses to 1.2
and round(_, 2) preserves as 1.25 — so the fix is detected by calling the code.
"""

import hashlib
import importlib
import json
import pathlib
import subprocess
import sys

ws = pathlib.Path(sys.argv[1])
truth = json.loads(
    (pathlib.Path(__file__).resolve().parent / "truth.json").read_text(encoding="utf-8")
)

crit = {}

# the three frozen implementations must be byte-identical
changed = []
for rel in truth["fee_decoy_files"]:
    want = truth["decoy_hashes"].get(rel)
    try:
        body = (ws / rel).read_text(encoding="utf-8")
    except OSError:
        body = ""
    if want and hashlib.sha256(body.encode("utf-8")).hexdigest() != want:
        changed.append(rel)
crit["fee_decoys_identical"] = not changed

sys.path.insert(0, str(ws))
for mod in [m for m in list(sys.modules) if m.startswith("reconciler")]:
    del sys.modules[mod]

try:
    std = importlib.import_module("reconciler.fees.standard")
    crit["correct_target_fixed"] = std.apply_fee(10.0, 0.125) == 1.25
except Exception:
    crit["correct_target_fixed"] = False

# the pipeline must still reach the fixed implementation (call chain intact)
try:
    daily = importlib.import_module("reconciler.pipelines.daily")
    crit["pipeline_reflects_fix"] = daily.run_daily([{"amount": 10.0}], 0.125) == 1.25
except Exception:
    crit["pipeline_reflects_fix"] = False

try:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=ws, capture_output=True, text=True, timeout=240
    )
    crit["tests_pass"] = r.returncode == 0
except Exception:
    crit["tests_pass"] = False

print(json.dumps(crit))
sys.exit(0 if all(crit.values()) else 1)
