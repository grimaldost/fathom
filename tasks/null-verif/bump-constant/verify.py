"""Null verifier for bump-constant (null-verif: verification NOT warranted).

The task is a one-token constant bump (MAX_RETRIES 3 -> 5). Nothing depends on the
value and there is nothing to check, so writing a test, adding a validation helper,
or introducing extra config is OVER-TRIGGER, not diligence.

Criteria:
- `correctness` — the gate: MAX_RETRIES is now 5.
- `over_scope` — the false-positive proxy: the agent added structure beyond the
  minimal change (any .py file beyond settings.py in the view, or any module-level
  name in settings.py other than MAX_RETRIES — a def, class, or extra assignment).

A minimal correct solve is correctness=T, over_scope=F. Over-trigger is
correctness=T, over_scope=T. FP is read as the lift over `bare`, so an occasional
baseline extra cancels. Exits 0 iff `correctness`. Fails closed.
"""

import ast
import importlib.util
import json
import sys
from pathlib import Path

MODULE = "settings"
ALLOWED_PY = {"settings.py"}
BASELINE_NAMES = {"MAX_RETRIES"}


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
        spec = importlib.util.spec_from_file_location("candidate_settings", path)
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


def _correct(mod):
    try:
        return mod.MAX_RETRIES == 5
    except Exception:
        return False


def _module_names(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _over_scope(view, settings_path):
    for cand in view.rglob("*.py"):
        if cand.name not in ALLOWED_PY:
            return True
    if settings_path is not None:
        try:
            tree = ast.parse(settings_path.read_text(encoding="utf-8"))
            if _module_names(tree) - BASELINE_NAMES:
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
    mod, settings_path = _load(view)
    if mod is None:
        print(
            json.dumps(
                {"correctness": False, "over_scope": _over_scope(view, settings_path)},
                sort_keys=True,
            )
        )
        return 1
    correct = _correct(mod)
    result = {"correctness": correct, "over_scope": _over_scope(view, settings_path)}
    print(json.dumps(result, sort_keys=True))
    return 0 if correct else 1


if __name__ == "__main__":
    sys.exit(main())
