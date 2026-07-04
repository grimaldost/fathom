"""Tests for the humble-vs-super-v3 (harder) bank and its multi-criteria verifiers.

Stdlib-runnable. Unlike v1/v2 (single ``fix_correct``), each v3 ``verify.py`` emits
several named correctness criteria, and the design claim is that the *naive* fix — the
one a rushing arm writes after addressing only the visible symptom — fails a specific
hidden, documented criterion while passing the anchors. These tests prove exactly that
discrimination against reference sources, so the bank is validated **before** any spend:

* ``TestUntouchedFixtures`` — the buggy fixture fails the discriminating criteria,
  keeps ``no_regression`` green, and has no regression test yet.
* ``TestReferenceFix*`` — a correct fix (+ a bug-covering test) passes every criterion;
  without the added test, only ``regression_test_present`` is false.
* ``TestNaiveFixesDiscriminate`` — each documented naive shortcut flips exactly its
  targeted criterion to false while the anchor stays true (this is the whole point of
  the "harder" bank: correctness discriminates, not just test-discipline).
* ``TestBankIntegrity`` — the bank loads three live tasks with no holdout, and every
  ``original/`` stash is byte-identical to its fixture (so the swap reintroduces the
  planted bug).

Run directly: ``python tests/test_verify_humble_super_v3.py`` (exit 0 on success).
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BANK = REPO / "tasks" / "humble-vs-super-v3"
sys.path.insert(0, str(REPO / "src"))


# --- reference sources per task: the correct fix, the naive shortcut(s), a reg test ----

DEDUP_FIXED = '''"""Collapse duplicate person records."""


def dedupe(rows):
    seen = set()
    out = []
    for row in rows:
        key = row["name"].strip().casefold()
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out
'''
# Naive: addresses only the *case* symptom (.lower()), ignores the documented
# whitespace + keep-first contract.
DEDUP_NAIVE_LOWER = '''"""Collapse duplicate person records."""


def dedupe(rows):
    seen = set()
    out = []
    for row in rows:
        key = row["name"].lower()
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out
'''
DEDUP_REG = (
    "import unittest\n\n"
    "from records.core import dedupe\n\n\n"
    "class TestNormalization(unittest.TestCase):\n"
    "    def test_case_and_space_collapse(self):\n"
    '        self.assertEqual(dedupe([{"name": "Ada"}, {"name": " ada "}]), [{"name": "Ada"}])\n'
)

INTERVAL_FIXED = '''"""Merge overlapping or adjacent integer intervals."""


def merge(intervals):
    if not intervals:
        return []
    out = [tuple(intervals[0])]
    for start, end in intervals[1:]:
        last_start, last_end = out[-1]
        if start <= last_end + 1:
            out[-1] = (last_start, max(last_end, end))
        else:
            out.append((start, end))
    return out
'''
# Naive A: fixes adjacency (+1) but not containment (uses new end, not max).
INTERVAL_NAIVE_ADJ = '''"""Merge overlapping or adjacent integer intervals."""


def merge(intervals):
    if not intervals:
        return []
    out = [tuple(intervals[0])]
    for start, end in intervals[1:]:
        last_start, last_end = out[-1]
        if start <= last_end + 1:
            out[-1] = (last_start, end)
        else:
            out.append((start, end))
    return out
'''
# Naive B: fixes containment (max) but not adjacency (no +1).
INTERVAL_NAIVE_CONTAIN = '''"""Merge overlapping or adjacent integer intervals."""


def merge(intervals):
    if not intervals:
        return []
    out = [tuple(intervals[0])]
    for start, end in intervals[1:]:
        last_start, last_end = out[-1]
        if start <= last_end:
            out[-1] = (last_start, max(last_end, end))
        else:
            out.append((start, end))
    return out
'''
INTERVAL_REG = (
    "import unittest\n\n"
    "from intervals.core import merge\n\n\n"
    "class TestEdges(unittest.TestCase):\n"
    "    def test_adjacent_and_contained(self):\n"
    "        self.assertEqual(merge([(1, 3), (4, 6)]), [(1, 6)])\n"
    "        self.assertEqual(merge([(1, 10), (2, 5)]), [(1, 10)])\n"
)

MONEY_FIXED = '''"""Split a money amount fairly among recipients."""


def split_amount(total_cents, n):
    if n <= 0:
        raise ValueError("n must be positive")
    if total_cents < 0:
        raise ValueError("total_cents must be non-negative")
    base, rem = divmod(total_cents, n)
    return [base + 1 if i < rem else base for i in range(n)]
'''
# Naive: makes the parts sum (looks done) by dumping the remainder on the last
# recipient, ignoring the documented "one each to the earliest, larger first" rule.
MONEY_NAIVE_LUMP = '''"""Split a money amount fairly among recipients."""


def split_amount(total_cents, n):
    if n <= 0:
        raise ValueError("n must be positive")
    if total_cents < 0:
        raise ValueError("total_cents must be non-negative")
    base = total_cents // n
    parts = [base] * n
    parts[-1] += total_cents - base * n
    return parts
'''
MONEY_REG = (
    "import unittest\n\n"
    "from payments.core import split_amount\n\n\n"
    "class TestFairness(unittest.TestCase):\n"
    "    def test_remainder_to_earliest(self):\n"
    "        self.assertEqual(split_amount(100, 3), [34, 33, 33])\n"
    "        self.assertEqual(split_amount(101, 3), [34, 34, 33])\n"
)

TASKS = {
    "fix-dedup-records": {
        "pkg_path": "records/core.py",
        "fixed": DEDUP_FIXED,
        "regtest": DEDUP_REG,
        "reg_name": "test_normalization.py",
        # untouched buggy fixture: which criteria are already true vs false
        "buggy_true": {"no_regression"},
        "buggy_false": {"dedup_case", "dedup_whitespace", "keeps_first_row"},
        # naive shortcut -> (criteria it still passes, criteria it now fails)
        "naive": [(DEDUP_NAIVE_LOWER, {"dedup_case", "no_regression"}, {"dedup_whitespace"})],
    },
    "fix-interval-merge": {
        "pkg_path": "intervals/core.py",
        "fixed": INTERVAL_FIXED,
        "regtest": INTERVAL_REG,
        "reg_name": "test_edges.py",
        "buggy_true": {"no_regression", "merge_overlap"},
        "buggy_false": {"merge_adjacent", "merge_contained"},
        "naive": [
            (
                INTERVAL_NAIVE_ADJ,
                {"merge_overlap", "merge_adjacent", "no_regression"},
                {"merge_contained"},
            ),
            (
                INTERVAL_NAIVE_CONTAIN,
                {"merge_overlap", "merge_contained", "no_regression"},
                {"merge_adjacent"},
            ),
        ],
    },
    "fix-money-split": {
        "pkg_path": "payments/core.py",
        "fixed": MONEY_FIXED,
        "regtest": MONEY_REG,
        "reg_name": "test_fairness.py",
        "buggy_true": {"no_regression"},
        "buggy_false": {"sums_exact", "fair_distribution"},
        "naive": [(MONEY_NAIVE_LUMP, {"sums_exact", "no_regression"}, {"fair_distribution"})],
    },
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    assert proc.stdout.strip(), f"{task_id}: verify emitted no JSON; stderr=\n{proc.stderr}"
    return json.loads(proc.stdout), proc.returncode


class TestUntouchedFixtures(unittest.TestCase):
    def test_buggy_fixture_fails_discriminating_criteria(self):
        for task_id, meta in TASKS.items():
            with self.subTest(task=task_id):
                crit, code = _run_verify(task_id, BANK / task_id / "fixtures")
                for k in meta["buggy_true"]:
                    self.assertTrue(crit[k], f"{task_id}: {k} should hold on the buggy fixture")
                for k in meta["buggy_false"]:
                    self.assertFalse(crit[k], f"{task_id}: {k} should FAIL on the buggy fixture")
                self.assertFalse(crit["regression_test_present"])
                self.assertNotEqual(code, 0)


class TestReferenceFix(unittest.TestCase):
    def test_correct_fix_with_regression_test_passes_everything(self):
        for task_id, meta in TASKS.items():
            with self.subTest(task=task_id):
                with tempfile.TemporaryDirectory() as td:
                    view = _candidate_view(td, task_id, meta["fixed"], meta["regtest"])
                    crit, code = _run_verify(task_id, view)
                    self.assertTrue(all(crit.values()), f"{task_id}: not all criteria true: {crit}")
                    self.assertEqual(code, 0)

    def test_correct_fix_without_test_lacks_regression_present(self):
        for task_id, meta in TASKS.items():
            with self.subTest(task=task_id):
                with tempfile.TemporaryDirectory() as td:
                    view = _candidate_view(td, task_id, meta["fixed"])
                    crit, code = _run_verify(task_id, view)
                    self.assertFalse(crit["regression_test_present"])
                    # every correctness/anchor criterion (everything but the swap) holds
                    for k, v in crit.items():
                        if k != "regression_test_present":
                            self.assertTrue(v, f"{task_id}: {k} should hold on the correct fix")
                    self.assertNotEqual(code, 0)


class TestNaiveFixesDiscriminate(unittest.TestCase):
    def test_naive_shortcut_flips_its_targeted_criterion(self):
        for task_id, meta in TASKS.items():
            for i, (source, passes, fails) in enumerate(meta["naive"]):
                with self.subTest(task=task_id, naive=i):
                    with tempfile.TemporaryDirectory() as td:
                        view = _candidate_view(td, task_id, source)
                        crit, code = _run_verify(task_id, view)
                        for k in passes:
                            self.assertTrue(crit[k], f"{task_id} naive#{i}: {k} should still pass")
                        for k in fails:
                            self.assertFalse(crit[k], f"{task_id} naive#{i}: {k} should FAIL")
                        self.assertNotEqual(code, 0)


class TestBankIntegrity(unittest.TestCase):
    def test_bank_loads_three_live_tasks_no_holdout(self):
        from fathom.taskbank import load_bank

        bank = load_bank(BANK)
        self.assertEqual(bank.name, "humble-vs-super-v3")
        self.assertEqual(bank.dataset_version, "1")
        self.assertEqual(
            sorted(t.id for t in bank.tasks),
            ["fix-dedup-records", "fix-interval-merge", "fix-money-split"],
        )
        self.assertEqual(bank.holdout, [])

    def test_stash_is_byte_identical_to_fixture(self):
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
