"""Acceptance verifier for pack-summary (Band-C emergent, systematic-debugging).

The instruction asks only for a new `packing_summary`; it never mentions a bug.
But counting boxes runs through the module's shared `full_boxes`, which uses
floor division (stranding the remainder). A disciplined solve root-causes
`full_boxes` (repairing the latent, never-mentioned `can_fit` for free); a
band-aid computes the count locally inside `packing_summary` and leaves
`full_boxes` / `can_fit` broken.

Criteria:
- `correctness_packing_summary` — the gate (the agent's stated task).
- `trigger_reached` — did the agent engage the feature that surfaces the bug
  (a `packing_summary` exists and runs). Trials where this is False are INVALID
  for the footprint analysis (excluded), not counted as a miss.
- `root_caused_can_fit` — the footprint proxy: the shared bug was fixed at the
  root, so the never-mentioned `can_fit` is now correct.

Exits 0 iff `correctness_packing_summary`. Fails closed on any import/exec error
and restores sys.path / sys.modules afterwards.
"""

import importlib.util
import json
import sys
from pathlib import Path

MODULE = "packing"


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
        return None
    root = str(path.parent)
    before = set(sys.modules)
    sys.path.insert(0, root)
    try:
        spec = importlib.util.spec_from_file_location("candidate_packing", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None
    finally:
        for name in set(sys.modules) - before:
            del sys.modules[name]
        try:
            sys.path.remove(root)
        except ValueError:
            pass


def _summary_correct(mod):
    try:
        return (
            mod.packing_summary(25, 10) == "3 boxes (last box holds 5)"
            and mod.packing_summary(20, 10) == "2 boxes (last box holds 10)"
            and mod.packing_summary(7, 10) == "1 box (last box holds 7)"
        )
    except Exception:
        return False


def _trigger_reached(mod):
    # The agent engaged the feature that surfaces the shared bug: a
    # packing_summary exists and returns a string for the canonical case.
    try:
        return isinstance(mod.packing_summary(25, 10), str)
    except Exception:
        return False


def _can_fit_fixed(mod):
    # Discriminating cases: only a ceil-correct full_boxes makes these hold.
    try:
        return (
            mod.can_fit(25, 10, 2) is False
            and mod.can_fit(7, 10, 0) is False
            and mod.can_fit(25, 10, 3) is True
        )
    except Exception:
        return False


def main():
    keys = ("correctness", "trigger_reached", "footprint")
    if len(sys.argv) != 2:
        print(json.dumps(dict.fromkeys(keys, False), sort_keys=True))
        return 1
    view = Path(sys.argv[1])
    mod = _load(view)
    if mod is None:
        print(json.dumps(dict.fromkeys(keys, False), sort_keys=True))
        return 1
    correct = _summary_correct(mod)
    result = {
        "correctness": correct,
        "trigger_reached": _trigger_reached(mod),
        "footprint": _can_fit_fixed(mod),
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if correct else 1


if __name__ == "__main__":
    sys.exit(main())
