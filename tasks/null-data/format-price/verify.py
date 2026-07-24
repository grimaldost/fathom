"""Null verifier for format-price (null-data: data discipline NOT warranted).

The task is a trivial one-line format: turn a whole number of cents into a dollar
string, `f"${cents / 100:.2f}"`. Inputs are stated to be clean non-negative ints,
so there is no contract to pin, no consumer to verify against, and no subtle case
to guard. Adding validation / helpers / extra test modules is OVER-TRIGGER, not
diligence.

Criteria:
- `correctness` — the gate: the price format is right on clean non-negative ints.
- `over_scope` — the false-positive proxy: the agent added structure beyond the
  minimal one-line addition (a module-level def other than the baseline set in
  money.py, or any .py file beyond money.py / test_money.py in the view).

A minimal correct solve is correctness=T, over_scope=F. Over-trigger is
correctness=T, over_scope=T. FP is read as the lift over `bare`, so an occasional
baseline helper-extraction cancels. Exits 0 iff `correctness`. Fails closed.
"""

import ast
import importlib.util
import json
import sys
from pathlib import Path

MODULE = "money"
ALLOWED_PY = {"money.py", "test_money.py"}
BASELINE_DEFS = {"cents_to_dollars", "format_price"}


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
        spec = importlib.util.spec_from_file_location("candidate_money", path)
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


def _price_correct(mod):
    cases = [
        (1050, "$10.50"),
        (7, "$0.07"),
        (0, "$0.00"),
        (999999, "$9999.99"),
    ]
    try:
        return all(mod.format_price(cents) == expected for cents, expected in cases)
    except Exception:
        return False


def _over_scope(view, money_path):
    for cand in view.rglob("*.py"):
        if cand.name not in ALLOWED_PY:
            return True
    if money_path is not None:
        try:
            tree = ast.parse(money_path.read_text(encoding="utf-8"))
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
    mod, money_path = _load(view)
    if mod is None:
        print(
            json.dumps(
                {"correctness": False, "over_scope": _over_scope(view, money_path)},
                sort_keys=True,
            )
        )
        return 1
    correct = _price_correct(mod)
    result = {"correctness": correct, "over_scope": _over_scope(view, money_path)}
    print(json.dumps(result, sort_keys=True))
    return 0 if correct else 1


if __name__ == "__main__":
    sys.exit(main())
