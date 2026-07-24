"""Null verifier for add-docstring (null-verif: verification-before-completion NOT warranted).

The task is to add a one-line docstring to `area(w, h)`, which returns `w * h`.
This cannot change behavior, so writing tests, adding helpers, or creating extra
modules to "verify" it is OVER-TRIGGER, not diligence.

Criteria:
- `correctness` — the gate: `area(3, 4) == 12` and `area.__doc__` is a non-empty
  string (the docstring was actually added).
- `over_scope` — the false-positive proxy: the agent added structure beyond the
  minimal one-line docstring (a module-level def other than `area` in geometry.py,
  or any .py file beyond geometry.py in the view).

A minimal correct solve is correctness=T, over_scope=F. Over-trigger is
correctness=T, over_scope=T. FP is read as the lift over `bare`, so an occasional
baseline helper-extraction cancels. Exits 0 iff `correctness`. Fails closed.
"""

import ast
import importlib.util
import json
import sys
from pathlib import Path

MODULE = "geometry"
ALLOWED_PY = {"geometry.py"}
BASELINE_DEFS = {"area"}


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
        spec = importlib.util.spec_from_file_location("candidate_geometry", path)
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


def _area_correct(mod):
    try:
        doc = mod.area.__doc__
        return mod.area(3, 4) == 12 and isinstance(doc, str) and doc.strip() != ""
    except Exception:
        return False


def _over_scope(view, geometry_path):
    for cand in view.rglob("*.py"):
        if cand.name not in ALLOWED_PY:
            return True
    if geometry_path is not None:
        try:
            tree = ast.parse(geometry_path.read_text(encoding="utf-8"))
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
    mod, geometry_path = _load(view)
    if mod is None:
        print(
            json.dumps(
                {"correctness": False, "over_scope": _over_scope(view, geometry_path)},
                sort_keys=True,
            )
        )
        return 1
    correct = _area_correct(mod)
    result = {"correctness": correct, "over_scope": _over_scope(view, geometry_path)}
    print(json.dumps(result, sort_keys=True))
    return 0 if correct else 1


if __name__ == "__main__":
    sys.exit(main())
