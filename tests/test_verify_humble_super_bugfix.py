"""Tests for the humble-vs-super-v1 bug-fix bank and its verifiers — stdlib-runnable.

Two layers:

* ``TestSwapLogic`` exercises the shared ``bugfix_verify`` primitives directly on
  crafted temp projects (no live bank wiring), proving the swap distinguishes a
  real regression test from none and that discovery is layout-agnostic.
* ``Test<Task>`` classes drive each task's ``verify.py`` as a subprocess against the
  untouched fixture, a reference correct fix, and a fix without an added test —
  the §6 acceptance criteria.

Run directly: ``python tests/test_verify_humble_super_bugfix.py`` (exit 0 on success).
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BANK = REPO / "tasks" / "humble-vs-super-v1"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(BANK))

import bugfix_verify as bv  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --- crafted synthetic project: a `widget.bump` with a floor-vs-ceil style bug ----

_BUGGY = "def bump(n):\n    return n // 2\n"  # wrong for odd n
_FIXED = "def bump(n):\n    return (n + 1) // 2\n"  # ceil: correct for odd n
# Shipped suite uses only even n, so it passes on both buggy and fixed source.
_SHIPPED_TEST = (
    "import unittest\n"
    "from widget.core import bump\n\n\n"
    "class T(unittest.TestCase):\n"
    "    def test_even(self):\n"
    "        self.assertEqual(bump(4), 2)\n"
    "        self.assertEqual(bump(10), 5)\n"
)
# A genuine regression test: red on the buggy source (odd n), green on the fix.
_REG_TEST = (
    "import unittest\n"
    "from widget.core import bump\n\n\n"
    "class TReg(unittest.TestCase):\n"
    "    def test_odd_rounds_up(self):\n"
    "        self.assertEqual(bump(5), 3)\n"
)


def _make_project(root: Path, *, core: str, src_layout: bool, extra_tests: str = "") -> Path:
    """Build a synthetic candidate project; return the view root."""
    pkg = (root / "src" / "widget") if src_layout else (root / "widget")
    _write(pkg / "__init__.py", "")
    _write(pkg / "core.py", core)
    _write(root / "tests" / "__init__.py", "")
    _write(root / "tests" / "test_shipped.py", _SHIPPED_TEST)
    if extra_tests:
        _write(root / "tests" / "test_regression.py", extra_tests)
    return root


class TestSwapLogic(unittest.TestCase):
    def test_find_package_and_module_flat_and_src(self):
        with tempfile.TemporaryDirectory() as td:
            flat = _make_project(Path(td) / "flat", core=_FIXED, src_layout=False)
            srcl = _make_project(Path(td) / "srcl", core=_FIXED, src_layout=True)
            self.assertEqual(bv.find_package_dir(flat, "widget"), flat / "widget")
            self.assertEqual(bv.find_package_dir(srcl, "widget"), srcl / "src" / "widget")
            self.assertEqual(
                bv.find_module_file(flat, "widget", "core.py"), flat / "widget" / "core.py"
            )
            self.assertEqual(
                bv.find_module_file(srcl, "widget", "core.py"), srcl / "src" / "widget" / "core.py"
            )
            self.assertEqual(bv.import_root_for(srcl, "widget"), srcl / "src")

    def test_import_candidate_flat_and_src(self):
        with tempfile.TemporaryDirectory() as td:
            flat = _make_project(Path(td) / "flat", core=_FIXED, src_layout=False)
            srcl = _make_project(Path(td) / "srcl", core=_BUGGY, src_layout=True)
            m_flat = bv.import_candidate(flat, "widget.core", "widget")
            m_src = bv.import_candidate(srcl, "widget.core", "widget")
            self.assertIsNotNone(m_flat)
            self.assertIsNotNone(m_src)
            # Distinct sources resolve correctly despite the shared package name.
            self.assertEqual(m_flat.bump(5), 3)
            self.assertEqual(m_src.bump(5), 2)

    def test_run_test_suite_green_and_red(self):
        with tempfile.TemporaryDirectory() as td:
            green = _make_project(
                Path(td) / "g", core=_FIXED, src_layout=False, extra_tests=_REG_TEST
            )
            red = _make_project(
                Path(td) / "r", core=_BUGGY, src_layout=False, extra_tests=_REG_TEST
            )
            self.assertTrue(bv.run_test_suite(green))
            self.assertFalse(bv.run_test_suite(red))  # the regression test fails on buggy source

    def test_no_regression_true_then_false(self):
        with tempfile.TemporaryDirectory() as td:
            shipped = _make_project(Path(td) / "ship", core=_FIXED, src_layout=False) / "tests"
            good = _make_project(Path(td) / "good", core=_FIXED, src_layout=False)
            # A candidate whose source breaks the shipped (even-n) behavior:
            broken = _make_project(
                Path(td) / "bad", core="def bump(n):\n    return n + 1\n", src_layout=False
            )
            self.assertTrue(bv.no_regression(good, shipped))
            self.assertFalse(bv.no_regression(broken, shipped))

    def test_regression_present_distinguishes_real_test_from_none(self):
        with tempfile.TemporaryDirectory() as td:
            buggy_src = Path(td) / "buggy_core.py"
            buggy_src.write_text(_BUGGY, encoding="utf-8")
            with_test = _make_project(
                Path(td) / "with", core=_FIXED, src_layout=False, extra_tests=_REG_TEST
            )
            without_test = _make_project(Path(td) / "without", core=_FIXED, src_layout=False)
            self.assertTrue(
                bv.regression_test_present(with_test, "widget", "core.py", buggy_src),
                "a real bug-covering test must be detected (red on buggy, green on fix)",
            )
            self.assertFalse(
                bv.regression_test_present(without_test, "widget", "core.py", buggy_src),
                "no added test => shipped suite stays green on buggy => not present",
            )

    def test_regression_present_handles_src_layout(self):
        with tempfile.TemporaryDirectory() as td:
            buggy_src = Path(td) / "buggy_core.py"
            buggy_src.write_text(_BUGGY, encoding="utf-8")
            view = _make_project(
                Path(td) / "s", core=_FIXED, src_layout=True, extra_tests=_REG_TEST
            )
            self.assertTrue(bv.regression_test_present(view, "widget", "core.py", buggy_src))

    def test_regression_present_false_when_candidate_test_is_broken(self):
        # A candidate test that is red even on their own fix is not a valid regression test.
        with tempfile.TemporaryDirectory() as td:
            buggy_src = Path(td) / "buggy_core.py"
            buggy_src.write_text(_BUGGY, encoding="utf-8")
            broken_reg = (
                "import unittest\n"
                "from widget.core import bump\n\n\n"
                "class TBad(unittest.TestCase):\n"
                "    def test_wrong(self):\n"
                "        self.assertEqual(bump(5), 999)\n"
            )
            view = _make_project(
                Path(td) / "b", core=_FIXED, src_layout=False, extra_tests=broken_reg
            )
            self.assertFalse(bv.regression_test_present(view, "widget", "core.py", buggy_src))


# --- reference correct fixes, naive over-fixes, and regression tests per task --------

PAG_FIXED = '''"""Pagination helpers for splitting a result set into fixed-size pages."""


def total_pages(total_items, per_page):
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    return (total_items + per_page - 1) // per_page


def page_slice(total_items, per_page, page):
    if page < 1:
        raise ValueError("page is 1-indexed")
    start = (page - 1) * per_page
    return start, min(start + per_page, total_items)
'''
PAG_NAIVE = '''"""Pagination helpers."""


def total_pages(total_items, per_page):
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    return total_items // per_page + 1


def page_slice(total_items, per_page, page):
    if page < 1:
        raise ValueError("page is 1-indexed")
    start = (page - 1) * per_page
    return start, min(start + per_page, total_items)
'''
PAG_REG = (
    "import unittest\n\n"
    "from paginator.core import total_pages\n\n\n"
    "class TestPartialFinalPage(unittest.TestCase):\n"
    "    def test_partial_page_counts(self):\n"
    "        self.assertEqual(total_pages(25, 10), 3)\n"
    "        self.assertEqual(total_pages(0, 10), 0)\n"
)

DST_FIXED = '''"""Convert US/Eastern wall-clock times to UTC."""

from datetime import date, datetime, timedelta


def _nth_sunday(year, month, n):
    first = date(year, month, 1)
    first_sunday = 1 + (6 - first.weekday()) % 7
    return first_sunday + (n - 1) * 7


def _is_dst(local):
    start = datetime(local.year, 3, _nth_sunday(local.year, 3, 2), 2)
    end = datetime(local.year, 11, _nth_sunday(local.year, 11, 1), 2)
    return start <= local < end


def to_utc(year, month, day, hour, minute=0):
    local = datetime(year, month, day, hour, minute)
    offset_hours = 4 if _is_dst(local) else 5
    utc = local + timedelta(hours=offset_hours)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")
'''
DST_NAIVE = '''"""Convert US/Eastern wall-clock times to UTC."""

from datetime import datetime, timedelta


def to_utc(year, month, day, hour, minute=0):
    is_dst = 3 <= month <= 11
    offset_hours = 4 if is_dst else 5
    local = datetime(year, month, day, hour, minute)
    utc = local + timedelta(hours=offset_hours)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")
'''
DST_REG = (
    "import unittest\n\n"
    "from eastern.dst import to_utc\n\n\n"
    "class TestSpringTransition(unittest.TestCase):\n"
    "    def test_day_after_spring_forward_is_edt(self):\n"
    '        self.assertEqual(to_utc(2026, 3, 20, 12, 0), "2026-03-20T16:00:00Z")\n'
)

CACHE_FIXED = '''"""A fixed-capacity least-recently-used (LRU) cache."""

from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._data = OrderedDict()

    def get(self, key, default=None):
        if key not in self._data:
            return default
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)
'''
CACHE_REG = (
    "import unittest\n\n"
    "from lru.cache import LRUCache\n\n\n"
    "class TestRecencyOnRead(unittest.TestCase):\n"
    "    def test_read_refreshes_recency(self):\n"
    "        c = LRUCache(2)\n"
    '        c.put("a", 1)\n'
    '        c.put("b", 2)\n'
    '        c.get("a")\n'
    '        c.put("c", 3)\n'
    '        self.assertIsNone(c.get("b"))\n'
    '        self.assertEqual(c.get("a"), 1)\n'
)

TASKS = {
    "fix-offbyone-paginator": {
        "pkg_path": "paginator/core.py",
        "fixed": PAG_FIXED,
        "naive": PAG_NAIVE,
        "regtest": PAG_REG,
        "reg_name": "test_partial.py",
    },
    "fix-tz-dst-normalize": {
        "pkg_path": "eastern/dst.py",
        "fixed": DST_FIXED,
        "naive": DST_NAIVE,
        "regtest": DST_REG,
        "reg_name": "test_transition.py",
    },
    "fix-cache-eviction-bug": {
        "pkg_path": "lru/cache.py",
        "fixed": CACHE_FIXED,
        "naive": None,  # the no-op (untouched) fixture already evidences a naive miss
        "regtest": CACHE_REG,
        "reg_name": "test_recency.py",
    },
}


def _candidate_view(td: str, task_id: str, source: str, regtest: str | None = None) -> Path:
    """Stage a candidate workspace: the task fixtures with *source* overlaid."""
    meta = TASKS[task_id]
    view = Path(td) / "view"

    shutil.copytree(BANK / task_id / "fixtures", view)
    _write(view / meta["pkg_path"], source)
    if regtest:
        _write(view / "tests" / meta["reg_name"], regtest)
    return view


def _run_verify(task_id: str, view: Path) -> tuple[dict, int]:
    proc = subprocess.run(
        [sys.executable, str(BANK / task_id / "verify.py"), str(view)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(proc.stdout), proc.returncode


class TestTaskVerifiers(unittest.TestCase):
    def test_untouched_fixture_reports_fix_incorrect(self):
        # §6 acceptance: on the untouched (buggy) fixture, fix_correct is false, the
        # shipped suite still passes (no_regression), and no regression test exists yet.
        for task_id in TASKS:
            with self.subTest(task=task_id):
                crit, code = _run_verify(task_id, BANK / task_id / "fixtures")
                self.assertFalse(crit["fix_correct"], "buggy fixture must fail fix_correct")
                self.assertTrue(crit["no_regression"], "shipped suite must pass on the fixture")
                self.assertFalse(crit["regression_test_present"])
                self.assertNotEqual(code, 0)

    def test_reference_fix_with_regression_test_reports_all_true(self):
        # §6 acceptance: a correct fix plus a real regression test passes every criterion.
        for task_id, meta in TASKS.items():
            with self.subTest(task=task_id):
                with tempfile.TemporaryDirectory() as td:
                    view = _candidate_view(td, task_id, meta["fixed"], meta["regtest"])
                    crit, code = _run_verify(task_id, view)
                    self.assertEqual(
                        crit,
                        {
                            "fix_correct": True,
                            "no_regression": True,
                            "regression_test_present": True,
                        },
                    )
                    self.assertEqual(code, 0)

    def test_reference_fix_without_test_lacks_regression_present(self):
        # §6 acceptance: regression_test_present distinguishes a real test from none —
        # a correct fix with NO added test is fix_correct/no_regression true but
        # regression_test_present false.
        for task_id, meta in TASKS.items():
            with self.subTest(task=task_id):
                with tempfile.TemporaryDirectory() as td:
                    view = _candidate_view(td, task_id, meta["fixed"])
                    crit, code = _run_verify(task_id, view)
                    self.assertTrue(crit["fix_correct"])
                    self.assertTrue(crit["no_regression"])
                    self.assertFalse(crit["regression_test_present"])
                    self.assertNotEqual(code, 0)

    def test_naive_overfix_fails_fix_correct(self):
        # Discrimination: a plausible naive fix that passes the obvious case still fails
        # the hidden test — so an undisciplined arm can land here and fail.
        for task_id, meta in TASKS.items():
            if meta["naive"] is None:
                continue
            with self.subTest(task=task_id):
                with tempfile.TemporaryDirectory() as td:
                    view = _candidate_view(td, task_id, meta["naive"])
                    crit, _ = _run_verify(task_id, view)
                    self.assertFalse(crit["fix_correct"], "naive over-fix must fail fix_correct")


class TestBankIntegrity(unittest.TestCase):
    def test_bank_loads_five_tasks_with_sealed_holdout(self):
        from fathom.taskbank import load_bank

        bank = load_bank(BANK)
        self.assertEqual(bank.name, "humble-vs-super-v1")
        self.assertEqual(bank.dataset_version, "1")
        self.assertEqual(
            sorted(t.id for t in bank.tasks),
            [
                "feature-csv-coalesce",
                "feature-retry-backoff",
                "fix-cache-eviction-bug",
                "fix-offbyone-paginator",
                "fix-tz-dst-normalize",
            ],
        )
        self.assertEqual(bank.holdout, ["fix-cache-eviction-bug"])

    def test_stash_is_byte_identical_to_fixture(self):
        # The swap reintroduces the planted bug only if the stashed original and shipped
        # tests stay identical to what the candidate starts from. Pin them.
        for task_id, meta in TASKS.items():
            with self.subTest(task=task_id):
                fix_src = BANK / task_id / "fixtures" / meta["pkg_path"]
                stash_src = BANK / task_id / "original" / Path(meta["pkg_path"]).name
                self.assertEqual(
                    stash_src.read_text(encoding="utf-8"),
                    fix_src.read_text(encoding="utf-8"),
                    f"{task_id}: stashed source drifted from fixture",
                )
                for shipped in sorted((BANK / task_id / "fixtures" / "tests").glob("*.py")):
                    stashed = BANK / task_id / "original" / "tests" / shipped.name
                    self.assertTrue(stashed.is_file(), f"{task_id}: missing stashed {shipped.name}")
                    self.assertEqual(
                        stashed.read_text(encoding="utf-8"),
                        shipped.read_text(encoding="utf-8"),
                        f"{task_id}: stashed test {shipped.name} drifted from fixture",
                    )


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
