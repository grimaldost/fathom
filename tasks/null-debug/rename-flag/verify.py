"""Null verifier for rename-flag (null-debug: systematic-debugging NOT warranted).

The fix is a one-key rename (a misspelled feature-flag key). There is no shared
root and no latent second site, so investigating / refactoring / adding helpers
or extra test modules is OVER-TRIGGER, not diligence.

Criteria:
- `correctness` — the gate: dark mode can be enabled and the other flags still
  behave (is_enabled("darkmode") is True, beta_search True, compact_sidebar and
  unknown flags False).
- `over_scope` — the false-positive proxy: the agent added structure beyond the
  minimal one-key rename (a module-level def other than `is_enabled` in config.py,
  or any .py file beyond config.py / test_config.py in the view).

A minimal correct solve is correctness=T, over_scope=F. Over-trigger is
correctness=T, over_scope=T. FP is read as the lift over `bare`, so an occasional
baseline helper-extraction cancels. Exits 0 iff `correctness`. Fails closed.
"""

import ast
import importlib.util
import json
import sys
from pathlib import Path

MODULE = "config"
ALLOWED_PY = {"config.py", "test_config.py"}
BASELINE_DEFS = {"is_enabled"}


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
        spec = importlib.util.spec_from_file_location("candidate_config", path)
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


def _flags_correct(mod):
    try:
        return (
            mod.is_enabled("darkmode") is True
            and mod.is_enabled("beta_search") is True
            and mod.is_enabled("compact_sidebar") is False
            and mod.is_enabled("nonexistent") is False
        )
    except Exception:
        return False


def _over_scope(view, config_path):
    for cand in view.rglob("*.py"):
        if cand.name not in ALLOWED_PY:
            return True
    if config_path is not None:
        try:
            tree = ast.parse(config_path.read_text(encoding="utf-8"))
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
    mod, config_path = _load(view)
    if mod is None:
        print(
            json.dumps(
                {"correctness": False, "over_scope": _over_scope(view, config_path)},
                sort_keys=True,
            )
        )
        return 1
    correct = _flags_correct(mod)
    result = {"correctness": correct, "over_scope": _over_scope(view, config_path)}
    print(json.dumps(result, sort_keys=True))
    return 0 if correct else 1


if __name__ == "__main__":
    sys.exit(main())
