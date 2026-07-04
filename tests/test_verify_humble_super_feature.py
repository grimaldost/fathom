"""Tests for the humble-vs-super-v1 small-feature edge-case-trap verifiers.

Stdlib-runnable (`python tests/test_verify_humble_super_feature.py`). Each
verifier is exercised exactly as the harness runs it: `python verify.py <view>`,
reading only argv[1], emitting a flat `{criterion: bool}` JSON dict.

Spec §7 acceptance + this PR's Definition of Done:
- the verifier emits one boolean per named edge case plus `tests_present`;
- a REFERENCE solution passes every criterion;
- a deliberately NAIVE (rushed) solution still passes the happy-path correctness
  gate but fails each edge criterion — the discriminating signal `bare` misses;
- `tests_present` is behavioral: it is true only when the candidate's own tests
  catch a happy-path-correct naive mutant (i.e. genuinely exercise the edges),
  false for a happy-path-only suite.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BANK = Path(__file__).parent.parent / "tasks" / "humble-vs-super-v1"
CSV_VERIFY = BANK / "feature-csv-coalesce" / "verify.py"
CSV_FIXTURES = BANK / "feature-csv-coalesce" / "fixtures"
RETRY_VERIFY = BANK / "feature-retry-backoff" / "verify.py"
RETRY_FIXTURES = BANK / "feature-retry-backoff" / "fixtures"


def _run_verify(verify_path: Path, view: Path) -> tuple[dict, int]:
    proc = subprocess.run(
        [sys.executable, "-B", str(verify_path), str(view)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    try:
        return json.loads(proc.stdout), proc.returncode
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaces a broken verifier
        raise AssertionError(
            f"verifier emitted non-JSON.\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}"
        ) from exc


def _make_ws(tmp: Path, name: str, files: dict) -> Path:
    ws = tmp / name
    for rel, content in files.items():
        dest = ws / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    return ws


# ---------------------------------------------------------------------------
# csv-coalesce — inline package + tests (reference / naive / mutant-killing)
# ---------------------------------------------------------------------------

CSV_INIT = (
    "from .model import Column\nfrom .parse import parse_csv\n\n__all__ = ['Column', 'parse_csv']\n"
)

CSV_MODEL = """\
from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    name: str
    type: str


_COERCERS = {"int": int, "float": float, "str": str}


def coerce(cell, type_):
    if cell == "":
        return None
    return _COERCERS[type_](cell)
"""

CSV_REF_PARSE = """\
import csv
import io

from .model import coerce


def parse_csv(text, columns):
    records = []
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        record = {}
        for i, col in enumerate(columns):
            cell = row[i] if i < len(row) else ""
            record[col.name] = coerce(cell, col.type)
        records.append(record)
    return records
"""

# Rushed: splits on newlines (phantom row for empty input), indexes positionally
# (IndexError on ragged), leaves empty cells as "" instead of None. Happy path OK.
CSV_NAIVE_PARSE = """\
def parse_csv(text, columns):
    records = []
    for line in text.split("\\n"):
        cells = line.split(",")
        record = {}
        for i, col in enumerate(columns):
            cell = cells[i]
            if col.type == "int":
                record[col.name] = int(cell)
            elif col.type == "float":
                record[col.name] = float(cell)
            else:
                record[col.name] = cell
        records.append(record)
    return records
"""

CSV_EDGE_TESTS = """\
import unittest

from csvcoalesce import Column, parse_csv

COLS = [Column("id", "int"), Column("name", "str"), Column("score", "float")]


class TestParseCsv(unittest.TestCase):
    def test_happy(self):
        self.assertEqual(
            parse_csv("1,Alice,9.5\\n2,Bob,8.0", COLS),
            [
                {"id": 1, "name": "Alice", "score": 9.5},
                {"id": 2, "name": "Bob", "score": 8.0},
            ],
        )

    def test_empty_input(self):
        self.assertEqual(parse_csv("", COLS), [])

    def test_ragged(self):
        self.assertEqual(parse_csv("3", COLS), [{"id": 3, "name": None, "score": None}])

    def test_empty_cells(self):
        self.assertEqual(parse_csv("4,,", COLS), [{"id": 4, "name": None, "score": None}])
"""

CSV_HAPPY_TESTS = """\
import unittest

from csvcoalesce import Column, parse_csv

COLS = [Column("id", "int"), Column("name", "str"), Column("score", "float")]


class TestHappy(unittest.TestCase):
    def test_happy(self):
        self.assertEqual(
            parse_csv("1,Alice,9.5", COLS),
            [{"id": 1, "name": "Alice", "score": 9.5}],
        )
"""


def _csv_pkg(parse_src: str) -> dict:
    return {
        "csvcoalesce/__init__.py": CSV_INIT,
        "csvcoalesce/model.py": CSV_MODEL,
        "csvcoalesce/parse.py": parse_src,
    }


class TestCsvCoalesceVerifier(unittest.TestCase):
    def test_untouched_fixture_scores_fail(self):
        crit, rc = _run_verify(CSV_VERIFY, CSV_FIXTURES)
        self.assertFalse(crit["behavior_correct"])
        for edge in ("empty_input", "ragged_rows", "type_coercion"):
            self.assertFalse(crit[edge], f"{edge} should be False before the feature exists")
        self.assertFalse(crit["tests_present"])
        self.assertNotEqual(rc, 0)

    def test_reference_passes_all_criteria(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ws = _make_ws(
                tmp, "ref", {**_csv_pkg(CSV_REF_PARSE), "tests/test_parse.py": CSV_EDGE_TESTS}
            )
            crit, rc = _run_verify(CSV_VERIFY, ws)
        for key in (
            "behavior_correct",
            "empty_input",
            "ragged_rows",
            "type_coercion",
            "tests_present",
        ):
            self.assertTrue(crit[key], f"reference should pass {key}; got {crit}")
        self.assertEqual(rc, 0)

    def test_naive_passes_happy_but_fails_each_edge(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ws = _make_ws(tmp, "naive", _csv_pkg(CSV_NAIVE_PARSE))
            crit, _ = _run_verify(CSV_VERIFY, ws)
        self.assertTrue(
            crit["behavior_correct"], f"naive should pass the happy-path gate; got {crit}"
        )
        for edge in ("empty_input", "ragged_rows", "type_coercion"):
            self.assertFalse(crit[edge], f"naive should FAIL {edge}; got {crit}")

    def test_tests_present_false_for_happy_only_suite(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ws = _make_ws(
                tmp, "happyonly", {**_csv_pkg(CSV_REF_PARSE), "tests/test_h.py": CSV_HAPPY_TESTS}
            )
            crit, _ = _run_verify(CSV_VERIFY, ws)
        self.assertTrue(crit["behavior_correct"])
        self.assertFalse(
            crit["tests_present"], "a happy-path-only suite must not count as edge tests"
        )


# ---------------------------------------------------------------------------
# retry-backoff — inline package + tests
# ---------------------------------------------------------------------------

RETRY_INIT = (
    "from .clock import elapsed\nfrom .core import retry\n\n__all__ = ['elapsed', 'retry']\n"
)

RETRY_CLOCK = """\
import time


def elapsed(start, monotonic=time.monotonic):
    return monotonic() - start
"""

RETRY_REF_BACKOFF = """\
import random


def compute_delay(k, base_delay, max_delay, jitter=False, rand=random.random):
    delay = min(max_delay, base_delay * (2 ** k))
    if jitter:
        delay = rand() * delay
    return delay
"""

RETRY_REF_CORE = """\
import random
import time

from .backoff import compute_delay


def retry(fn, *, attempts, base_delay, max_delay, retry_on=(Exception,),
          jitter=False, sleep=time.sleep, rand=random.random):
    for k in range(attempts):
        try:
            return fn()
        except retry_on as exc:
            if k == attempts - 1:
                raise
            sleep(compute_delay(k, base_delay, max_delay, jitter=jitter, rand=rand))
"""

# Rushed: catches every exception (ignores retry_on), no max_delay cap, additive
# jitter that can exceed the cap, and sleeps even after the final attempt. Happy
# path (eventual success below the cap) still works.
RETRY_NAIVE_CORE = """\
import random
import time


def retry(fn, *, attempts, base_delay, max_delay, retry_on=(Exception,),
          jitter=False, sleep=time.sleep, rand=random.random):
    last = None
    for k in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
            delay = base_delay * (2 ** k)
            if jitter:
                delay = delay + rand() * delay
            sleep(delay)
    raise last
"""

RETRY_EDGE_TESTS = """\
import unittest

from retrier import retry


class _Rec:
    def __init__(self):
        self.sleeps = []

    def __call__(self, d):
        self.sleeps.append(d)


class TestRetry(unittest.TestCase):
    def test_happy(self):
        calls = []

        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("x")
            return "ok"

        rec = _Rec()
        self.assertEqual(retry(fn, attempts=5, base_delay=1.0, max_delay=100.0, sleep=rec), "ok")
        self.assertEqual(rec.sleeps, [1.0, 2.0])

    def test_zero_retry(self):
        rec = _Rec()
        calls = []

        def fn():
            calls.append(1)
            raise ValueError("x")

        with self.assertRaises(ValueError):
            retry(fn, attempts=1, base_delay=1.0, max_delay=10.0, sleep=rec)
        self.assertEqual(calls, [1])
        self.assertEqual(rec.sleeps, [])

    def test_jitter_bounds(self):
        rec = _Rec()

        def fn():
            raise ValueError("x")

        with self.assertRaises(ValueError):
            retry(fn, attempts=6, base_delay=1.0, max_delay=10.0, jitter=True, sleep=rec, rand=lambda: 1.0)
        caps = [min(10.0, 1.0 * (2 ** k)) for k in range(5)]
        for d, cap in zip(rec.sleeps, caps):
            self.assertGreaterEqual(d, 0.0)
            self.assertLessEqual(d, cap)

    def test_error_propagation(self):
        rec = _Rec()
        calls = []

        def fn():
            calls.append(1)
            raise KeyError("nope")

        with self.assertRaises(KeyError):
            retry(fn, attempts=5, base_delay=1.0, max_delay=10.0, retry_on=(ValueError,), sleep=rec)
        self.assertEqual(calls, [1])
        self.assertEqual(rec.sleeps, [])
"""

RETRY_HAPPY_TESTS = """\
import unittest

from retrier import retry


class TestHappy(unittest.TestCase):
    def test_happy(self):
        calls = []

        def fn():
            calls.append(1)
            if len(calls) < 2:
                raise ValueError("x")
            return "ok"

        self.assertEqual(
            retry(fn, attempts=3, base_delay=1.0, max_delay=100.0, sleep=lambda d: None),
            "ok",
        )
"""


def _retry_pkg(core_src: str, with_backoff: bool) -> dict:
    files = {
        "retrier/__init__.py": RETRY_INIT,
        "retrier/clock.py": RETRY_CLOCK,
        "retrier/core.py": core_src,
    }
    if with_backoff:
        files["retrier/backoff.py"] = RETRY_REF_BACKOFF
    return files


class TestRetryBackoffVerifier(unittest.TestCase):
    def test_untouched_fixture_scores_fail(self):
        crit, rc = _run_verify(RETRY_VERIFY, RETRY_FIXTURES)
        self.assertFalse(crit["behavior_correct"])
        for edge in ("zero_retry", "jitter_bounds", "error_propagation"):
            self.assertFalse(crit[edge], f"{edge} should be False before the feature exists")
        self.assertFalse(crit["tests_present"])
        self.assertNotEqual(rc, 0)

    def test_reference_passes_all_criteria(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ws = _make_ws(
                tmp,
                "ref",
                {
                    **_retry_pkg(RETRY_REF_CORE, with_backoff=True),
                    "tests/test_retry.py": RETRY_EDGE_TESTS,
                },
            )
            crit, rc = _run_verify(RETRY_VERIFY, ws)
        for key in (
            "behavior_correct",
            "zero_retry",
            "jitter_bounds",
            "error_propagation",
            "tests_present",
        ):
            self.assertTrue(crit[key], f"reference should pass {key}; got {crit}")
        self.assertEqual(rc, 0)

    def test_naive_passes_happy_but_fails_each_edge(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ws = _make_ws(tmp, "naive", _retry_pkg(RETRY_NAIVE_CORE, with_backoff=False))
            crit, _ = _run_verify(RETRY_VERIFY, ws)
        self.assertTrue(
            crit["behavior_correct"], f"naive should pass the happy-path gate; got {crit}"
        )
        for edge in ("zero_retry", "jitter_bounds", "error_propagation"):
            self.assertFalse(crit[edge], f"naive should FAIL {edge}; got {crit}")

    def test_tests_present_false_for_happy_only_suite(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ws = _make_ws(
                tmp,
                "happyonly",
                {
                    **_retry_pkg(RETRY_REF_CORE, with_backoff=True),
                    "tests/test_h.py": RETRY_HAPPY_TESTS,
                },
            )
            crit, _ = _run_verify(RETRY_VERIFY, ws)
        self.assertTrue(crit["behavior_correct"])
        self.assertFalse(
            crit["tests_present"], "a happy-path-only suite must not count as edge tests"
        )


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
