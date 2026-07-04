"""Tests for the model-tier-v1 difficulty-ladder bank and its graded verifiers (§3).

Stdlib-runnable. Proves the bank is graded and discriminating **before** any paid
spend (the spec's §3 acceptance):

* ``TestBankIntegrity`` — the bank loads 8 tasks, the holdout resolves, every task
  declares ≥2 ``hard_criteria`` in ``[verify]``, and every ``original/`` stash is
  byte-identical to its fixture (so the regression-swap reintroduces the planted bug).
* ``TestUntouchedFixtures`` — for ALL 8 tasks the buggy fixture emits a valid
  ``{criterion: bool}`` dict (the partial-credit gradient that reaches the ledger via
  ``verifier_results``), with at least one declared hard criterion FALSE (the bug is
  graded) and no regression test yet.
* ``TestNewLowTasks`` — for the two authored low rungs (fix-clamp, fix-titlecase):
  the reference fix flips every correctness criterion true; a deliberately-naive
  shortcut flips a specific hard criterion false while the anchor stays true.

The reused mid/high tasks carry their own discrimination tests in their origin banks
(``test_verify_humble_super_v3`` / ``test_verify_humble_super_v4``); here they are
covered by the integrity + untouched-fixture checks.

Run directly: ``python tests/test_verify_model_tier.py`` (exit 0 on success).
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BANK = REPO / "tasks" / "model-tier-v1"
sys.path.insert(0, str(REPO / "src"))

EXPECTED_TASKS = {
    "fix-clamp",
    "fix-titlecase",
    "feature-csv-coalesce",
    "fix-interval-merge",
    "fix-money-split",
    "fix-dedup-records",
    "fix-nonlocal-parse",
    "fix-nonlocal-urlkey",
}
HOLDOUT = ["fix-dedup-records"]

# --- reference + naive sources for the two authored low rungs ----------------------

CLAMP_FIXED = '''"""Clamp a value to an inclusive range."""


def clamp(x, lo, hi):
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
'''
# Naive: mirror of the planted bug — clamps the high bound only, so clamp_low fails.
CLAMP_NAIVE_HIGH = '''"""Clamp a value to an inclusive range."""


def clamp(x, lo, hi):
    return hi if x > hi else x
'''
CLAMP_REG = (
    "import unittest\n\n"
    "from numkit.core import clamp\n\n\n"
    "class TestBounds(unittest.TestCase):\n"
    "    def test_high(self):\n"
    "        self.assertEqual(clamp(99, 0, 10), 10)\n"
    "    def test_low(self):\n"
    "        self.assertEqual(clamp(-3, 0, 10), 0)\n"
)

TITLE_FIXED = '''"""Title-case a string."""


def title_case(s):
    return " ".join(w[:1].upper() + w[1:].lower() for w in s.split())
'''
# Naive: guards empty (so title_empty passes) but never lowercases the remainder,
# so title_mixed_case still fails.
TITLE_NAIVE_NOLOWER = '''"""Title-case a string."""


def title_case(s):
    return " ".join(w[:1].upper() + w[1:] for w in s.split())
'''
TITLE_REG = (
    "import unittest\n\n"
    "from textkit.core import title_case\n\n\n"
    "class TestTitle(unittest.TestCase):\n"
    "    def test_mixed(self):\n"
    '        self.assertEqual(title_case("hELLO"), "Hello")\n'
    "    def test_empty(self):\n"
    '        self.assertEqual(title_case(""), "")\n'
)

NEW_TASKS = {
    "fix-clamp": {
        "pkg_path": "numkit/core.py",
        "reg_name": "test_bounds.py",
        "fixed": CLAMP_FIXED,
        "reg": CLAMP_REG,
        "hard": {"clamp_low", "clamp_high"},
        "anchor": "clamp_in_range",
        "naive": [(CLAMP_NAIVE_HIGH, {"clamp_in_range", "clamp_high"}, {"clamp_low"})],
    },
    "fix-titlecase": {
        "pkg_path": "textkit/core.py",
        "reg_name": "test_title.py",
        "fixed": TITLE_FIXED,
        "reg": TITLE_REG,
        "hard": {"title_empty", "title_mixed_case"},
        "anchor": "title_basic",
        "naive": [(TITLE_NAIVE_NOLOWER, {"title_basic", "title_empty"}, {"title_mixed_case"})],
    },
}


def _run_verify(task_id: str, view: Path) -> tuple[dict, int]:
    proc = subprocess.run(
        [sys.executable, str(BANK / task_id / "verify.py"), str(view)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.stdout.strip(), f"{task_id}: verify emitted no JSON; stderr=\n{proc.stderr}"
    return json.loads(proc.stdout), proc.returncode


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _candidate_view(td: str, task_id: str, source: str, regtest: str | None = None) -> Path:
    meta = NEW_TASKS[task_id]
    view = Path(td) / "view"
    shutil.copytree(BANK / task_id / "fixtures", view)
    _write(view / meta["pkg_path"], source)
    if regtest:
        _write(view / "tests" / meta["reg_name"], regtest)
    return view


def _load():
    from fathom.taskbank import load_bank

    return load_bank(BANK)


class TestBankIntegrity(unittest.TestCase):
    def test_loads_eight_tasks_with_holdout(self):
        bank = _load()
        self.assertEqual(bank.name, "model-tier-v1")
        self.assertEqual(bank.dataset_version, "1")
        self.assertEqual(sorted(t.id for t in bank.tasks), sorted(EXPECTED_TASKS))
        self.assertEqual(bank.holdout, HOLDOUT)

    def test_every_task_declares_at_least_two_hard_criteria(self):
        for t in _load().tasks:
            with self.subTest(task=t.id):
                hard = t.verify.get("hard_criteria")
                self.assertIsInstance(hard, list, f"{t.id}: missing hard_criteria")
                self.assertGreaterEqual(len(hard), 2, f"{t.id}: needs >=2 hard criteria")

    def test_stash_is_byte_identical_to_fixture(self):
        # The stash is flat (original/core.py) while the fixture nests under the
        # package (fixtures/<pkg>/core.py), so match by basename. Feature tasks may
        # carry no original/ stash (no planted bug to swap) — skip those.
        for task_id in EXPECTED_TASKS:
            with self.subTest(task=task_id):
                orig = BANK / task_id / "original"
                fixtures = BANK / task_id / "fixtures"
                if not orig.is_dir():
                    self.skipTest(f"{task_id}: no original/ stash (feature task)")
                # module sources: top-level original/*.py matched by basename in fixtures/
                for stashed in sorted(orig.glob("*.py")):
                    twins = [m for m in fixtures.rglob(stashed.name) if "tests" not in m.parts]
                    self.assertEqual(
                        len(twins), 1, f"{task_id}: expected 1 fixture twin for {stashed.name}"
                    )
                    self.assertEqual(
                        stashed.read_text(encoding="utf-8"),
                        twins[0].read_text(encoding="utf-8"),
                        f"{task_id}: stashed {stashed.name} drifted from fixture",
                    )
                # shipped tests: original/tests/*.py vs fixtures/tests/*.py by name
                for stashed in sorted((orig / "tests").glob("*.py")):
                    twin = fixtures / "tests" / stashed.name
                    self.assertTrue(
                        twin.is_file(), f"{task_id}: missing fixture test {stashed.name}"
                    )
                    self.assertEqual(
                        stashed.read_text(encoding="utf-8"),
                        twin.read_text(encoding="utf-8"),
                        f"{task_id}: stashed test {stashed.name} drifted from fixture",
                    )


class TestUntouchedFixtures(unittest.TestCase):
    def test_buggy_fixture_emits_graded_dict_with_a_hard_failure(self):
        bank = _load()
        hard_by_task = {t.id: set(t.verify["hard_criteria"]) for t in bank.tasks}
        for task_id in EXPECTED_TASKS:
            with self.subTest(task=task_id):
                crit, code = _run_verify(task_id, BANK / task_id / "fixtures")
                self.assertIsInstance(crit, dict)
                # the declared hard criteria are present in the emitted dict
                for k in hard_by_task[task_id]:
                    self.assertIn(k, crit, f"{task_id}: hard criterion {k} not emitted")
                # at least one hard criterion FAILS on the un-fixed fixture (bug graded)
                self.assertTrue(
                    any(not crit[k] for k in hard_by_task[task_id]),
                    f"{task_id}: no hard criterion failed on the buggy fixture",
                )
                self.assertFalse(crit.get("regression_test_present", False))
                self.assertNotEqual(code, 0)


class TestNewLowTasks(unittest.TestCase):
    def test_reference_fix_with_test_passes_everything(self):
        for task_id, meta in NEW_TASKS.items():
            with self.subTest(task=task_id), tempfile.TemporaryDirectory() as td:
                view = _candidate_view(td, task_id, meta["fixed"], meta["reg"])
                crit, code = _run_verify(task_id, view)
                self.assertTrue(all(crit.values()), f"{task_id}: not all true: {crit}")
                self.assertEqual(code, 0)

    def test_naive_shortcut_flips_its_targeted_hard_criterion(self):
        for task_id, meta in NEW_TASKS.items():
            for i, (source, passes, fails) in enumerate(meta["naive"]):
                with self.subTest(task=task_id, naive=i), tempfile.TemporaryDirectory() as td:
                    view = _candidate_view(td, task_id, source)
                    crit, code = _run_verify(task_id, view)
                    for k in passes:
                        self.assertTrue(crit[k], f"{task_id} naive#{i}: {k} should pass")
                    for k in fails:
                        self.assertFalse(crit[k], f"{task_id} naive#{i}: {k} should FAIL")
                    self.assertNotEqual(code, 0)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
