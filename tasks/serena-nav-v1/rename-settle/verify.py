"""Blind verifier for rename-settle. Reads only argv[1] (result-view)."""

import ast
import json
import pathlib
import re
import subprocess
import sys

ws = pathlib.Path(sys.argv[1])
DECOYS = {"ledgerline/utils/money.py", "ledgerline/legacy/oldapi.py"}


def read(rel):
    try:
        return (ws / rel).read_text(encoding="utf-8")
    except OSError:
        return ""


def toplevel_funcs(rel):
    try:
        tree = ast.parse(read(rel))
    except SyntaxError:
        return set()
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


crit = {}

compute_funcs = toplevel_funcs("ledgerline/core/compute.py")
crit["renamed_definition"] = "settle_entries" in compute_funcs and "settle" not in compute_funcs

crit["decoy_method_intact"] = bool(
    re.search(r"def settle\(self", read("ledgerline/utils/money.py"))
)

old_src = read("ledgerline/legacy/oldapi.py")
crit["decoy_wrapper_intact"] = (
    bool(re.search(r"def settle\(entries", old_src)) and "settle_entries" in old_src
)

stale = []
for p in sorted(ws.rglob("*.py")):
    rel = p.relative_to(ws).as_posix()
    if rel in DECOYS:
        continue
    try:
        txt = p.read_text(encoding="utf-8")
    except OSError:
        continue
    if re.search(r"\bsettle\b", txt):
        stale.append(rel)
crit["no_stale_references"] = not stale

try:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=ws, capture_output=True, text=True, timeout=120
    )
    crit["tests_pass"] = r.returncode == 0
except Exception:
    crit["tests_pass"] = False

print(json.dumps(crit))
sys.exit(0 if all(crit.values()) else 1)
