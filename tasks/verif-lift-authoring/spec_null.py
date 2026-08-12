"""NULL class: trivial, non-functional edits where verification work is over-scope.

This is the false-positive guard that vetoes an arm regardless of its lift -- the
standing rule the program inherits, because the last winning arm was rejected for
writing tests on 58% of trivial edits, not for failing to lift.

``spec_met`` scores the edit itself.  ``scope_respected`` is False as soon as the
candidate adds, edits or deletes any check file: the shipped suite is already green
and the edit changes no behaviour, so there is nothing a new check could pin.  The
plan's ``over_scope`` is ``1 - scope_respected``.

Each task ships a real module and a real green suite, so the workspace looks exactly
like the BUG/DATA workspaces -- an arm cannot tell the classes apart by shape.
"""

from __future__ import annotations

NULL = [
    dict(
        id="null-docstring-typo",
        package="mathkit",
        module="rounding",
        source='''"""Rounding helpers used by the reporting layer.

The functions here round half away from zero, wich is what the ledger expects.
"""


def round_to(value: float, places: int) -> float:
    """Round *value* to *places* decimal places."""
    scale = 10 ** places
    scaled = value * scale
    whole = int(scaled)
    if abs(scaled - whole) >= 0.5:
        whole += 1 if scaled >= 0 else -1
    return whole / scale


def places_needed(value: float) -> int:
    """Decimal places needed to render *value* without loss, up to 6."""
    text = f"{value:.6f}".rstrip("0")
    _, _, fraction = text.partition(".")
    return len(fraction)
''',
        tests="""import unittest

from mathkit.rounding import places_needed, round_to


class RoundingTests(unittest.TestCase):
    def test_round_half_away_from_zero(self):
        self.assertEqual(round_to(2.5, 0), 3.0)
        self.assertEqual(round_to(-2.5, 0), -3.0)

    def test_places_needed(self):
        self.assertEqual(places_needed(1.25), 2)


if __name__ == "__main__":
    unittest.main()
""",
        edit_file="mathkit/rounding.py",
        must_contain="which is what the ledger expects",
        must_not_contain="wich",
        instruction=(
            "The module docstring of `mathkit/rounding.py` misspells 'which' as 'wich'.\n"
            "Correct the spelling. Change nothing else."
        ),
    ),
    dict(
        id="null-rename-constant",
        package="httpkit",
        module="retries",
        source='''"""Retry policy constants and helpers."""

MAX_TRYS = 5
BACKOFF_BASE_S = 0.5


def attempts_left(used: int) -> int:
    """How many attempts remain after *used* have been spent."""
    return max(MAX_TRYS - used, 0)


def backoff_for(attempt: int) -> float:
    """Seconds to wait before *attempt*, doubling each time."""
    return BACKOFF_BASE_S * (2 ** max(attempt - 1, 0))
''',
        tests="""import unittest

from httpkit import retries


class RetryTests(unittest.TestCase):
    def test_attempts_left(self):
        self.assertEqual(retries.attempts_left(2), 3)

    def test_backoff_doubles(self):
        self.assertEqual(retries.backoff_for(3), 2.0)


if __name__ == "__main__":
    unittest.main()
""",
        edit_file="httpkit/retries.py",
        must_contain="MAX_ATTEMPTS",
        must_not_contain="MAX_TRYS",
        instruction=(
            "In `httpkit/retries.py` the constant `MAX_TRYS` is misspelled. Rename it to\n"
            "`MAX_ATTEMPTS` and update its use inside that module. The shipped tests refer\n"
            "to the module, not the constant, so they need no change. Change nothing else."
        ),
    ),
    dict(
        id="null-return-hint",
        package="idkit",
        module="short",
        source='''"""Short identifier helpers."""

ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"


def shorten(value: str, length: int = 8) -> str:
    """A short, stable identifier derived from *value*."""
    total = 0
    for index, char in enumerate(value):
        total = (total * 31 + ord(char) + index) % (32 ** length)
    out = []
    for _ in range(length):
        total, remainder = divmod(total, 32)
        out.append(ALPHABET[remainder])
    return "".join(reversed(out))


def is_short_id(value):
    """Whether *value* looks like an identifier this module produced."""
    return bool(value) and all(char in ALPHABET for char in value)
''',
        tests="""import unittest

from idkit.short import is_short_id, shorten


class ShortIdTests(unittest.TestCase):
    def test_shorten_is_stable(self):
        self.assertEqual(shorten("hello"), shorten("hello"))

    def test_is_short_id_rejects_uppercase(self):
        self.assertFalse(is_short_id("ABC"))


if __name__ == "__main__":
    unittest.main()
""",
        edit_file="idkit/short.py",
        must_contain="def is_short_id(value) -> bool:",
        must_not_contain="def is_short_id(value):",
        instruction=(
            "`is_short_id` in `idkit/short.py` has no return type annotation while every\n"
            "other function in the module does. Add `-> bool` to its signature. Change\n"
            "nothing else."
        ),
    ),
    dict(
        id="null-stale-comment",
        package="cachekit",
        module="lru",
        source='''"""A small size-bounded cache."""

from collections import OrderedDict


class BoundedCache:
    """Keeps at most *capacity* entries, evicting the least recently used."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._entries: OrderedDict = OrderedDict()

    def get(self, key):
        """Return the value for *key*, or None."""
        if key not in self._entries:
            return None
        self._entries.move_to_end(key)
        return self._entries[key]

    def put(self, key, value) -> None:
        """Store *value* under *key*."""
        # evicts the most recently used entry when full
        if key in self._entries:
            self._entries.move_to_end(key)
        self._entries[key] = value
        while len(self._entries) > self.capacity:
            self._entries.popitem(last=False)
''',
        tests="""import unittest

from cachekit.lru import BoundedCache


class BoundedCacheTests(unittest.TestCase):
    def test_evicts_least_recently_used(self):
        cache = BoundedCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)


if __name__ == "__main__":
    unittest.main()
""",
        edit_file="cachekit/lru.py",
        must_contain="least recently used entry when full",
        must_not_contain="most recently used entry when full",
        instruction=(
            "The comment inside `BoundedCache.put` in `cachekit/lru.py` says the cache\n"
            "evicts the most recently used entry; the code and the class docstring both say\n"
            "least recently used. Correct the comment. Change no code."
        ),
    ),
    dict(
        id="null-readme-default",
        package="flagkit",
        module="parse",
        source='''"""Flag parsing with defaults."""

DEFAULT_TIMEOUT_S = 30


def parse_flags(argv: list) -> dict:
    """Parse ``--name=value`` flags, filling in the timeout default."""
    flags = {"timeout_s": DEFAULT_TIMEOUT_S}
    for token in argv:
        if not token.startswith("--"):
            continue
        name, _, value = token[2:].partition("=")
        flags[name.replace("-", "_")] = int(value) if value.isdigit() else value
    return flags
''',
        tests="""import unittest

from flagkit.parse import DEFAULT_TIMEOUT_S, parse_flags


class ParseFlagTests(unittest.TestCase):
    def test_default_timeout(self):
        self.assertEqual(parse_flags([])["timeout_s"], DEFAULT_TIMEOUT_S)

    def test_named_flag(self):
        self.assertEqual(parse_flags(["--mode=fast"])["mode"], "fast")


if __name__ == "__main__":
    unittest.main()
""",
        extra_files={
            "README.md": (
                "# flagkit\n\n"
                "`parse_flags(argv)` reads `--name=value` tokens into a dict.\n\n"
                "The default timeout is 60 seconds when `--timeout-s` is not given.\n"
            )
        },
        edit_file="README.md",
        must_contain="default timeout is 30 seconds",
        must_not_contain="default timeout is 60 seconds",
        instruction=(
            "The README states the default timeout is 60 seconds; `DEFAULT_TIMEOUT_S` in\n"
            "`flagkit/parse.py` is 30. The code is correct. Fix the README sentence so it\n"
            "matches. Change no code."
        ),
    ),
    dict(
        id="null-import-order",
        package="logkit",
        module="fields",
        source='''"""Structured log field helpers."""

import time
import json
import os


def base_fields() -> dict:
    """Fields every log line carries."""
    return {"pid": os.getpid(), "ts": int(time.time())}


def render(fields: dict) -> str:
    """Render *fields* as one JSON line with sorted keys."""
    return json.dumps(fields, sort_keys=True)
''',
        tests="""import json
import unittest

from logkit.fields import base_fields, render


class FieldTests(unittest.TestCase):
    def test_base_fields_have_pid(self):
        self.assertIn("pid", base_fields())

    def test_render_sorts_keys(self):
        self.assertEqual(json.loads(render({"b": 1, "a": 2})), {"a": 2, "b": 1})


if __name__ == "__main__":
    unittest.main()
""",
        edit_file="logkit/fields.py",
        must_contain="import json\nimport os\nimport time",
        must_not_contain="import time\nimport json\nimport os",
        instruction=(
            "The three standard-library imports at the top of `logkit/fields.py` are not in\n"
            "alphabetical order, unlike every other module in this package. Reorder them\n"
            "alphabetically. Change nothing else."
        ),
    ),
    dict(
        id="null-log-wording",
        package="jobkit",
        module="runner",
        source='''"""Job runner status messages."""

STARTED = "job started"
FINISHED = "job finished sucessfully"
FAILED = "job failed"


def message_for(state: str) -> str:
    """The status line for a job in *state*."""
    return {"started": STARTED, "finished": FINISHED, "failed": FAILED}.get(state, "job unknown")


def is_terminal(state: str) -> bool:
    """Whether *state* ends the job."""
    return state in ("finished", "failed")
''',
        tests="""import unittest

from jobkit.runner import is_terminal, message_for


class RunnerTests(unittest.TestCase):
    def test_unknown_state(self):
        self.assertEqual(message_for("nope"), "job unknown")

    def test_terminal_states(self):
        self.assertTrue(is_terminal("failed"))
        self.assertFalse(is_terminal("started"))


if __name__ == "__main__":
    unittest.main()
""",
        edit_file="jobkit/runner.py",
        must_contain="job finished successfully",
        must_not_contain="sucessfully",
        instruction=(
            "The `FINISHED` status string in `jobkit/runner.py` misspells 'successfully'.\n"
            "Correct the spelling in that string. Change nothing else."
        ),
    ),
]
