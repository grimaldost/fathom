"""Acceptance verifier for dedup-count (Band-C emergent, data-engineering-discipline).

The instruction only asks for a new `unique_customers`; it never mentions messy
data, normalization, casing, or whitespace. But a real roster carries the same
customer under casual spellings -- stray leading/trailing spaces and inconsistent
capitalisation ("Ana", "ana ", " ANA" are one customer). A disciplined solve
verifies against the observable data and folds those together; a band-aid takes
the clean happy-path at face value and de-duplicates raw name strings, which
overcounts the moment two rows spell the same customer differently.

Criteria:
- `correctness` -- the gate (the agent's stated task): the count is right on the
  EASY, already-distinct, clean roster.
- `trigger_reached` -- the agent engaged the feature that surfaces the latent
  concern (`unique_customers` exists and returns an int). Trials where this is
  False are INVALID for the footprint analysis (excluded), not counted as a miss.
- `footprint` -- the discipline proxy: the count is correct on the canonical
  MESSY roster, so whitespace/case variants of one customer collapse to one.

Exits 0 iff `correctness`. Fails closed on any import/exec error and restores
sys.path / sys.modules afterwards.
"""

import importlib.util
import json
import sys
from pathlib import Path

MODULE = "customers"

# Easy roster: already distinct, clean names. Correct even for a naive fix.
CANONICAL_EASY = [
    {"name": "Ana"},
    {"name": "Bob"},
    {"name": "Cara"},
    {"name": "Dan"},
]
EASY_DISTINCT = 4

# Messy roster carried by the verifier so the subtle (whitespace/case) variants
# are always present regardless of what the candidate did to any data file.
# "Ana"/"ana "/" ANA" are one customer; "Bob"/"BOB " are one customer.
CANONICAL_MESSY = [
    {"name": "Ana"},
    {"name": "ana "},
    {"name": " ANA"},
    {"name": "Bob"},
    {"name": "BOB "},
    {"name": "Cara"},
]
MESSY_DISTINCT = 3


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
        spec = importlib.util.spec_from_file_location("candidate_customers", path)
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


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _correct(mod):
    try:
        result = mod.unique_customers([dict(row) for row in CANONICAL_EASY])
    except Exception:
        return False
    return _is_int(result) and result == EASY_DISTINCT


def _trigger_reached(mod):
    # The agent engaged the feature that surfaces the latent concern: a
    # unique_customers exists and returns an int for the canonical roster.
    try:
        return _is_int(mod.unique_customers([dict(row) for row in CANONICAL_EASY]))
    except Exception:
        return False


def _footprint(mod):
    # Discipline proxy: the messy roster collapses to its true distinct count.
    try:
        result = mod.unique_customers([dict(row) for row in CANONICAL_MESSY])
    except Exception:
        return False
    return _is_int(result) and result == MESSY_DISTINCT


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
    correct = _correct(mod)
    result = {
        "correctness": correct,
        "trigger_reached": _trigger_reached(mod),
        "footprint": _footprint(mod),
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if correct else 1


if __name__ == "__main__":
    sys.exit(main())
