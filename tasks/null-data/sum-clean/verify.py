"""Null verifier for sum-clean (null-data: observable-verification NOT warranted).

The task is to add `grand_total(rows)`, a plain sum over the `amount` field. The
data is clean -- every amount is a plain float, no blanks, no dupes, no messy
types -- so there is no latent edge case to surface. Adding input validation,
try/except, per-row coercion/validation helpers, or an extra module is
OVER-TRIGGER (wasted defensiveness), not diligence.

Criteria:
- `correctness` -- the gate: `grand_total` sums the amounts right.
- `over_scope` -- the false-positive proxy: the agent added structure beyond the
  minimal one-function add (a module-level def other than `grand_total` in
  totals.py, or any .py file beyond totals.py / test_totals.py in the view).

A minimal correct solve is correctness=T, over_scope=F. Over-trigger is
correctness=T, over_scope=T. FP is read as the lift over `bare`, so an occasional
baseline helper-extraction cancels. Exits 0 iff `correctness`. Fails closed.
"""

import ast
import importlib.util
import json
import math
import sys
from pathlib import Path

MODULE = "totals"
ALLOWED_PY = {"totals.py", "test_totals.py"}
BASELINE_DEFS = {"grand_total"}

CANONICAL_ROWS = [
    {"sku": "A-1", "amount": 10.0},
    {"sku": "B-2", "amount": 20.5},
    {"sku": "C-3", "amount": 5.25},
    {"sku": "D-4", "amount": 100.0},
]
CANONICAL_TOTAL = 135.75


def _candidate_file(view):
    direct = view / (MODULE + ".py")
    if direct.is_file():
        return direct
    for cand in view.rglob(MODULE + ".py"):
        return cand
    return None


def _load(view):
    path = _candidate_file(view)
    if path is None:
        return None, None
    root = str(path.parent)
    before = set(sys.modules)
    sys.path.insert(0, root)
    try:
        spec = importlib.util.spec_from_file_location("candidate_totals", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, path
    except Exception:
        return None, path
    finally:
        for name in set(sys.modules) - before:
            del sys.modules[name]
        try:
            sys.path.remove(root)
        except ValueError:
            pass


def _total_correct(mod):
    try:
        got = mod.grand_total([dict(row) for row in CANONICAL_ROWS])
        empty = mod.grand_total([])
    except Exception:
        return False
    try:
        return math.isclose(got, CANONICAL_TOTAL, rel_tol=1e-9, abs_tol=1e-9) and (
            math.isclose(empty, 0.0, rel_tol=1e-9, abs_tol=1e-9)
        )
    except TypeError:
        return False


def _over_scope(view, totals_path):
    for cand in view.rglob("*.py"):
        if cand.name not in ALLOWED_PY:
            return True
    if totals_path is not None:
        try:
            tree = ast.parse(totals_path.read_text(encoding="utf-8"))
            defs = {
                node.name
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            if defs - BASELINE_DEFS:
                return True
        except (OSError, SyntaxError, UnicodeDecodeError):
            pass
    return False


def main():
    keys = ("correctness", "over_scope")
    if len(sys.argv) != 2:
        print(json.dumps(dict.fromkeys(keys, False), sort_keys=True))
        return 1
    view = Path(sys.argv[1])
    mod, totals_path = _load(view)
    if mod is None:
        print(
            json.dumps(
                {"correctness": False, "over_scope": _over_scope(view, totals_path)},
                sort_keys=True,
            )
        )
        return 1
    correct = _total_correct(mod)
    result = {"correctness": correct, "over_scope": _over_scope(view, totals_path)}
    print(json.dumps(result, sort_keys=True))
    return 0 if correct else 1


if __name__ == "__main__":
    sys.exit(main())
