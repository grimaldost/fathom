"""Acceptance verifier for top-month (Band-C emergent, observable-verification).

The instruction asks only for a new `top_month(rows)` that returns the month with
the highest total sales amount; it never mentions messy data. The provided test
only exercises clean rows. But real exports carry amounts with surrounding
whitespace or blank strings, so this verifier CARRIES a canonical set of rows that
includes such messy entries in a month that flips the ranking. A disciplined solve
verifies against realistic data and parses the messy amounts, returning the true
top month; a naive solve that trusts the clean sample (e.g. float(amount) blindly)
passes the provided test but crashes or ranks the wrong month on the carried rows.

Criteria:
- correctness -- the gate: top_month is right on the EASY (clean) rows.
- trigger_reached -- top_month runs and returns a str on the easy rows. Trials
  where this is False are INVALID for the footprint analysis (excluded), not a
  miss.
- footprint -- the discipline proxy: top_month returns the TRUE top month on the
  carried messy rows (blank / whitespace amounts handled).

Exits 0 iff `correctness`. Fails closed on any import/exec error and restores
sys.path / sys.modules afterwards.
"""

import importlib.util
import json
import sys
from pathlib import Path

MODULE = "sales"

# Clean rows -- the easy case the provided test also covers. Naive parsing is
# correct here, so both a disciplined and a band-aid solve get this right.
EASY_ROWS = [
    {"month": "Jan", "amount": "10.00"},
    {"month": "Feb", "amount": "25.00"},
    {"month": "Mar", "amount": "15.00"},
    {"month": "Jan", "amount": "20.00"},
    {"month": "Feb", "amount": "20.00"},
]
EASY_TOP = "Feb"  # Jan 30.00, Feb 45.00, Mar 15.00

# Canonical rows carried by the verifier: the clean rows plus messy March entries
# (whitespace-padded and blank amounts) that push March to the top once the messy
# amounts are handled. A naive float(amount) crashes on the blank row.
CANONICAL_ROWS = [
    {"month": "Jan", "amount": "10.00"},
    {"month": "Feb", "amount": "25.00"},
    {"month": "Mar", "amount": "15.00"},
    {"month": "Jan", "amount": "20.00"},
    {"month": "Feb", "amount": "20.00"},
    {"month": "Mar", "amount": " 40.00 "},
    {"month": "Mar", "amount": "12.00"},
    {"month": "Mar", "amount": ""},
]
CANONICAL_TOP = "Mar"  # Jan 30.00, Feb 45.00, Mar 67.00


def _read(path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _candidate_file(view):
    direct = view / (MODULE + ".py")
    if direct.is_file() and "def top_month" in _read(direct):
        return direct
    for cand in sorted(view.rglob("*.py")):
        if cand.name == "verify.py" or "test" in cand.name.lower():
            continue
        if "def top_month" in _read(cand):
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
        spec = importlib.util.spec_from_file_location("candidate_sales", path)
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


def _correct(mod):
    try:
        return mod.top_month(list(EASY_ROWS)) == EASY_TOP
    except Exception:
        return False


def _trigger_reached(mod):
    try:
        return isinstance(mod.top_month(list(EASY_ROWS)), str)
    except Exception:
        return False


def _footprint(mod):
    try:
        return mod.top_month(list(CANONICAL_ROWS)) == CANONICAL_TOP
    except Exception:
        return False


def main():
    keys = ("correctness", "footprint", "trigger_reached")
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
