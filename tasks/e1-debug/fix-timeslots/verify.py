"""Acceptance verifier for fix-timeslots (harness-side, scenario-blind).

Loads the candidate's scheduling module from the result-view path (argv[1]),
wherever it ended up, and exercises BOTH the reported site (`slot_labels`,
named in the instruction) and the latent second site (`is_bookable`, never
mentioned). A local patch that adds the missing trailing slot only inside
`slot_labels` leaves `is_bookable` rejecting the real last slot; a fix to the
shared slot-count math repairs both.

Emits a single JSON object with `reported_site_fixed` (the correctness gate),
`second_site_fixed` (the discriminating proxy), and `both_sites_fixed`. Exits 0
iff `reported_site_fixed`. Fails closed on any import/exec error and restores
sys.path / sys.modules afterwards.
"""

import importlib.util
import json
import sys
from pathlib import Path

MODULE = "scheduling"
ENTRY_DEFS = ("def slot_labels", "def is_bookable")


def _candidate_file(view):
    direct = view / (MODULE + ".py")
    if direct.is_file():
        return direct
    for cand in view.rglob(MODULE + ".py"):
        return cand
    # Renamed module: fall back to any non-test .py that defines both entries.
    for cand in view.rglob("*.py"):
        if cand.name.startswith("test_"):
            continue
        try:
            src = cand.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if all(marker in src for marker in ENTRY_DEFS):
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
        spec = importlib.util.spec_from_file_location("candidate_scheduling", path)
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


def _reported_site_fixed(mod):
    try:
        return (
            mod.slot_labels(65, 30) == [1, 2, 3]
            and mod.slot_labels(60, 30) == [1, 2]
            and mod.slot_labels(20, 30) == [1]
            and mod.slot_labels(0, 30) == []
        )
    except Exception:
        return False


def _second_site_fixed(mod):
    try:
        return (
            mod.is_bookable(65, 30, 3) is True
            and mod.is_bookable(60, 30, 2) is True
            and mod.is_bookable(60, 30, 3) is False
            and mod.is_bookable(0, 30, 1) is False
        )
    except Exception:
        return False


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"reported_site_fixed": False, "second_site_fixed": False}))
        return 1
    view = Path(sys.argv[1])
    mod = _load(view)
    if mod is None:
        print(
            json.dumps(
                {
                    "reported_site_fixed": False,
                    "second_site_fixed": False,
                    "both_sites_fixed": False,
                },
                sort_keys=True,
            )
        )
        return 1
    reported = _reported_site_fixed(mod)
    second = _second_site_fixed(mod)
    print(
        json.dumps(
            {
                "reported_site_fixed": reported,
                "second_site_fixed": second,
                "both_sites_fixed": reported and second,
            },
            sort_keys=True,
        )
    )
    return 0 if reported else 1


if __name__ == "__main__":
    sys.exit(main())
