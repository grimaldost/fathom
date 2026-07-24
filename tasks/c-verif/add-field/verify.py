"""Acceptance verifier for add-field (Band-C emergent, verification-before-completion).

The instruction asks only to make `to_line` include a record's `tag`; it never
mentions the round trip, `from_line`, or a regression. But `record.py` is a
serializer whose two halves are a round trip (`from_line(to_line(rec)) == rec`),
pinned by the pre-existing `test_roundtrip.py`. A change to `to_line` alone --
appending the tag segment without teaching `from_line` to read it back -- adds a
fourth field that `from_line` mis-parses, breaking the round trip. A disciplined
solve runs the existing test, sees the break, and updates `from_line` too; a
band-aid ships the `to_line` edit and leaves `from_line` stale.

Criteria (a tagged record is the probe):
- `correctness` -- the gate (the stated task): `to_line` serializes the tag and
  still carries the base fields (name / email / phone).
- `trigger_reached` -- did the agent engage the feature that surfaces the latent
  need: `to_line` runs and its output contains the tag. Trials where this is
  False are INVALID for the footprint analysis (excluded), not a miss.
- `footprint` -- the discipline proxy: the round trip holds for a tagged record
  (`from_line(to_line(rec)) == rec`), i.e. `from_line` was kept in sync.

Exits 0 iff `correctness`. Fails closed on any import/exec error and restores
sys.path / sys.modules afterwards.
"""

import importlib.util
import json
import sys
from pathlib import Path

MODULE = "record"
TAGGED = {"name": "Ada", "email": "ada@example.com", "phone": "555-0100", "tag": "vip"}


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
        spec = importlib.util.spec_from_file_location("candidate_record", path)
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


def _to_line(mod, rec):
    line = mod.to_line(dict(rec))
    if not isinstance(line, str):
        raise TypeError("to_line did not return a str")
    return line


def _trigger_reached(mod):
    # The agent engaged the feature that surfaces the latent need: to_line runs
    # for a tagged record and its output carries the tag value.
    try:
        return TAGGED["tag"] in _to_line(mod, TAGGED)
    except Exception:
        return False


def _correct(mod):
    # The stated task done right: the serialized line carries the tag AND still
    # carries every base field.
    try:
        line = _to_line(mod, TAGGED)
        return all(TAGGED[k] in line for k in ("name", "email", "phone", "tag"))
    except Exception:
        return False


def _footprint(mod):
    # The discipline proxy: the round trip is preserved for a tagged record, so
    # from_line was updated in step with to_line.
    try:
        return mod.from_line(_to_line(mod, TAGGED)) == TAGGED
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
