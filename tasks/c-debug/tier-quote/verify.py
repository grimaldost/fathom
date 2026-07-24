"""Acceptance verifier for tier-quote (Band-C emergent, systematic-debugging).

The instruction asks only for a new `quote_line`; it never mentions a bug. But
pricing runs through the module's shared `tier_for`, whose discount boundaries
use strict `>` instead of `>=` (an order of exactly 10 should be tier 1, exactly
100 should be tier 2). A disciplined solve root-causes `tier_for` (repairing the
latent, never-mentioned `bulk_eligible` for free); a band-aid special-cases the
boundary locally inside `quote_line` and leaves `tier_for` / `bulk_eligible`
broken.

Criteria:
- `correctness` — the gate (the agent's stated task: quote_line is correct).
- `trigger_reached` — did the agent engage the feature that surfaces the bug
  (a `quote_line` exists and returns a string). Trials where this is False are
  INVALID for the footprint analysis (excluded), not counted as a miss.
- `footprint` — the discipline proxy: the shared bug was fixed at the root, so
  the never-mentioned `bulk_eligible` is now correct at the boundaries.

Exits 0 iff `correctness`. Fails closed on any import/exec error and restores
sys.path / sys.modules afterwards.
"""

import importlib.util
import json
import sys
from pathlib import Path

MODULE = "pricing"


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
        spec = importlib.util.spec_from_file_location("candidate_pricing", path)
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


def _quote_correct(mod):
    try:
        return (
            mod.quote_line(10, 2.00) == "10 x 2.00 = 19.00"
            and mod.quote_line(100, 1.00) == "100 x 1.00 = 90.00"
            and mod.quote_line(9, 2.00) == "9 x 2.00 = 18.00"
            and mod.quote_line(50, 4.00) == "50 x 4.00 = 190.00"
        )
    except Exception:
        return False


def _trigger_reached(mod):
    # The agent engaged the feature that surfaces the shared bug: a quote_line
    # exists and returns a string for the canonical case.
    try:
        return isinstance(mod.quote_line(10, 2.00), str)
    except Exception:
        return False


def _bulk_eligible_fixed(mod):
    # Discriminating cases: only a >=-correct tier_for makes these all hold.
    try:
        return (
            mod.bulk_eligible(10) is True
            and mod.bulk_eligible(100) is True
            and mod.bulk_eligible(9) is False
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
    correct = _quote_correct(mod)
    result = {
        "correctness": correct,
        "trigger_reached": _trigger_reached(mod),
        "footprint": _bulk_eligible_fixed(mod),
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if correct else 1


if __name__ == "__main__":
    sys.exit(main())
