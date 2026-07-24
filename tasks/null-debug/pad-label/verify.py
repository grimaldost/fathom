"""Null verifier for pad-label (null-debug: systematic-debugging NOT warranted).

The fix is a one-line format change (zero-pad the order id). There is no shared
root and no latent second site, so investigating / refactoring / adding helpers
or extra test modules is OVER-TRIGGER, not diligence.

Criteria:
- `correctness_label` — the gate: the padded format is right.
- `over_scope` — the false-positive proxy: the agent added structure beyond the
  minimal one-line fix (a module-level def other than `shipping_label` in
  labels.py, or any .py file beyond labels.py / test_labels.py in the view).

A minimal correct solve is correctness=T, over_scope=F. Over-trigger is
correctness=T, over_scope=T. FP is read as the lift over `bare`, so an occasional
baseline helper-extraction cancels. Exits 0 iff `correctness_label`. Fails closed.
"""

import ast
import importlib.util
import json
import sys
from pathlib import Path

MODULE = "labels"
ALLOWED_PY = {"labels.py", "test_labels.py"}
BASELINE_DEFS = {"shipping_label"}


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
        spec = importlib.util.spec_from_file_location("candidate_labels", path)
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


def _label_correct(mod):
    try:
        return (
            mod.shipping_label(42) == "ORDER-00042"
            and mod.shipping_label(7) == "ORDER-00007"
            and mod.shipping_label(12345) == "ORDER-12345"
        )
    except Exception:
        return False


def _over_scope(view, labels_path):
    for cand in view.rglob("*.py"):
        if cand.name not in ALLOWED_PY:
            return True
    if labels_path is not None:
        try:
            tree = ast.parse(labels_path.read_text(encoding="utf-8"))
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
    mod, labels_path = _load(view)
    if mod is None:
        print(
            json.dumps(
                {"correctness": False, "over_scope": _over_scope(view, labels_path)},
                sort_keys=True,
            )
        )
        return 1
    correct = _label_correct(mod)
    result = {"correctness": correct, "over_scope": _over_scope(view, labels_path)}
    print(json.dumps(result, sort_keys=True))
    return 0 if correct else 1


if __name__ == "__main__":
    sys.exit(main())
