"""Acceptance verifier for theme-field (Band-C emergent, verification-before-completion).

The instruction asks only to make `dump` include a settings `theme`; it never
mentions the round trip, `load`, or a regression. But settings_codec's two halves
are a round trip (`load(dump(s)) == s`), pinned by the pre-existing
`test_roundtrip.py`. Appending the theme segment to `dump` without teaching `load`
to read it back adds a third field that `load` mis-parses, breaking the round trip
(even for un-themed settings, whose line now carries a trailing empty segment). A
disciplined solve runs the existing test, sees the break, and updates `load` too; a
band-aid ships the `dump` edit and leaves `load` stale.

Criteria:
- `correctness` -- the gate (the stated task): `dump` serializes the theme.
- `trigger_reached` -- did the agent engage the feature that surfaces the latent
  need: `dump` output contains the theme. Trials where this is False are INVALID
  for the footprint analysis (excluded), not a miss.
- `footprint` -- the discipline proxy: the round trip holds for a themed settings
  (`load(dump(s)) == s`), i.e. `load` was kept in sync.

Exits 0 iff `correctness`. Fails closed on any import/exec error and restores
sys.path / sys.modules afterwards.
"""

import importlib.util
import json
import sys
from pathlib import Path

MODULE = "settings_codec"
THEMED = {"user": "ana", "lang": "en", "theme": "dark"}


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
        spec = importlib.util.spec_from_file_location("candidate_settings_codec", path)
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


def _dump(mod, settings):
    line = mod.dump(dict(settings))
    if not isinstance(line, str):
        raise TypeError("dump did not return a str")
    return line


def _theme_present(mod):
    try:
        return THEMED["theme"] in _dump(mod, THEMED)
    except Exception:
        return False


def _footprint(mod):
    # The discipline proxy: the round trip is preserved for a themed settings, so
    # load was updated in step with dump.
    try:
        return mod.load(_dump(mod, THEMED)) == THEMED
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
    present = _theme_present(mod)
    result = {
        "correctness": present,
        "trigger_reached": present,
        "footprint": _footprint(mod),
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if present else 1


if __name__ == "__main__":
    sys.exit(main())
