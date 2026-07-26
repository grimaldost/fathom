"""Blind verifier for rename-reconcile (v2, large scale).

Reads only argv[1] (the result-view) plus its own harness-side truth.json, which is
never staged into the agent workspace.
"""

import ast
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ws = pathlib.Path(sys.argv[1])
truth = json.loads(
    (pathlib.Path(__file__).resolve().parent / "truth.json").read_text(encoding="utf-8")
)

WORD = re.compile(r"\breconcile\b")


def read(rel: str) -> str:
    try:
        return (ws / rel).read_text(encoding="utf-8")
    except OSError:
        return ""


crit = {}

# 1. the definition moved to the new name
try:
    tree = ast.parse(read(truth["defining_file"]))
    names = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
except SyntaxError:
    names = set()
crit["renamed_definition"] = "reconcile_entries" in names and "reconcile" not in names

# 2. no genuine reference still uses the bare old name
stale = [p for p in truth["genuine_reference_files"] if WORD.search(read(p))]
crit["no_stale_genuine_refs"] = not stale

# 3. every genuine reference actually adopted the new name
missing = [p for p in truth["genuine_reference_files"] if "reconcile_entries" not in read(p)]
crit["genuine_refs_updated"] = not missing

# 4. all ~150 decoys byte-identical (no partial credit for a careless sweep)
changed = []
for rel, want in truth["decoy_hashes"].items():
    got = hashlib.sha256(read(rel).encode("utf-8")).hexdigest()
    if got != want:
        changed.append(rel)
crit["decoys_byte_identical"] = not changed

try:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=ws, capture_output=True, text=True, timeout=240
    )
    crit["tests_pass"] = r.returncode == 0
except Exception:
    crit["tests_pass"] = False

print(json.dumps(crit))
sys.exit(0 if all(crit.values()) else 1)
