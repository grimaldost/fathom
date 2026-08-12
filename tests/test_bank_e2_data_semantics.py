"""Validity gate for the e2-data-semantics bank -- stdlib-runnable.

Three properties, checked against reference sources before any spend:

* ``TestFixturesLeaveSomethingToDo`` -- the untouched fixture leaves a criterion
  false, so the bank cannot ceiling and score every arm 100%.
* ``TestSolutionsAreSatisfiable`` -- ``solution/`` overlaid on the fixture passes
  every criterion, so a null from a task is a real null and not an unsatisfiable
  verifier.
* ``TestNaiveFixesMissTheSubtleCriterion`` -- **the one neither `fathom validate`
  nor any prior bank checked.** ``refs/naive/`` is the fix a competent agent
  reaches for first; it must satisfy the easy criterion and MISS the
  discriminating one. A task whose naive overlay already scores the subtle
  criterion cannot tell two arms apart, which is how ``e1-data`` resolved to one
  discriminating trial per arm after the money was spent.

The contract each task declares in its own ``task.toml`` drives the assertions,
so the test cannot drift from the bank:

    [naive]
    must_pass = ["..."]
    must_fail = ["..."]

``control = true`` declares a task with no trap by design (the benign control);
it must then satisfy everything and declare no ``must_fail``.

Run directly: ``python tests/test_bank_e2_data_semantics.py`` (exit 0 on success).
"""

import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fathom.taskbank import load_bank  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
BANK_DIR = REPO / "tasks" / "e2-data-semantics"

DEV_TASKS = [
    "benign-control",
    "distinct-as-fanout-repair",
    "null-vs-zero",
    "oracle-capture",
    "time-window-misalignment",
    "two-producer-drift",
]
HOLDOUT_TASKS = ["predicate-loss", "watermark-frozen-partition"]
ALL_TASKS = sorted(DEV_TASKS + HOLDOUT_TASKS)


def _naive_contract(task_id):
    with (BANK_DIR / task_id / "task.toml").open("rb") as fh:
        naive = tomllib.load(fh).get("naive", {})
    return (
        [str(c) for c in naive.get("must_pass", [])],
        [str(c) for c in naive.get("must_fail", [])],
        bool(naive.get("control", False)),
    )


def _verify(task_id, *overlays):
    """Run the task's verifier over fixtures/ with *overlays* copied on top."""
    task_dir = BANK_DIR / task_id
    with tempfile.TemporaryDirectory(prefix="e2-view-") as tmp:
        view = Path(tmp) / "view"
        shutil.copytree(task_dir / "fixtures", view)
        for overlay in overlays:
            shutil.copytree(task_dir / overlay, view, dirs_exist_ok=True)
        proc = subprocess.run(
            [sys.executable, str(task_dir / "verify.py"), str(view)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    if not proc.stdout.strip():
        raise AssertionError(f"{task_id}: verifier printed nothing. stderr={proc.stderr[:400]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TestBankIntegrity(unittest.TestCase):
    def test_bank_loads_eight_tasks(self):
        bank = load_bank(BANK_DIR)
        self.assertEqual(bank.name, "e2-data-semantics")
        self.assertEqual(sorted(t.id for t in bank.tasks), ALL_TASKS)

    def test_holdout_is_sealed(self):
        bank = load_bank(BANK_DIR)
        self.assertEqual(sorted(bank.holdout), sorted(HOLDOUT_TASKS))

    def test_every_task_ships_a_solution_and_a_naive_overlay(self):
        for task_id in ALL_TASKS:
            with self.subTest(task=task_id):
                self.assertTrue((BANK_DIR / task_id / "solution").is_dir())
                self.assertTrue((BANK_DIR / task_id / "refs" / "naive").is_dir())

    def test_every_task_declares_its_discrimination_contract(self):
        for task_id in ALL_TASKS:
            with self.subTest(task=task_id):
                must_pass, must_fail, control = _naive_contract(task_id)
                self.assertTrue(must_pass, "must_pass names the easy criterion")
                if control:
                    self.assertEqual(must_fail, [], "a control declares no trap")
                else:
                    self.assertTrue(must_fail, "must_fail names the discriminating criterion")

    def test_verifiers_read_only_argv_one(self):
        """Blindness (ADR-0003): no scenario identity may reach a verifier."""
        for task_id in ALL_TASKS:
            with self.subTest(task=task_id):
                source = (BANK_DIR / task_id / "verify.py").read_text(encoding="utf-8")
                self.assertNotIn("os.environ", source)
                self.assertNotIn("sys.argv[2]", source)


class TestFixturesLeaveSomethingToDo(unittest.TestCase):
    def test_untouched_fixture_fails_the_subtle_criterion(self):
        for task_id in ALL_TASKS:
            with self.subTest(task=task_id):
                criteria = _verify(task_id)
                self.assertTrue(criteria, "the verifier emitted no criteria")
                self.assertFalse(
                    all(criteria.values()),
                    f"{task_id}: every criterion is already true on the untouched fixture, "
                    "so this task scores every arm 100%",
                )
                # There is work to do on the easy path too, so a per-criterion table
                # can show the easy/subtle split rather than one all-or-nothing cell.
                must_pass, _, control = _naive_contract(task_id)
                self.assertFalse(
                    all(criteria[name] for name in must_pass),
                    f"{task_id}: the fixture already satisfies every easy criterion",
                )
                if control:
                    # A preservation criterion legitimately starts TRUE: it can only be
                    # lost. `oracle-capture`'s sealed-baseline criterion is the same shape.
                    self.assertTrue(criteria["no_semantic_change"])


class TestSolutionsAreSatisfiable(unittest.TestCase):
    def test_reference_solution_passes_every_criterion(self):
        for task_id in ALL_TASKS:
            with self.subTest(task=task_id):
                criteria = _verify(task_id, "solution")
                failed = sorted(k for k, v in criteria.items() if not v)
                self.assertEqual(
                    failed,
                    [],
                    f"{task_id}: the reference solution misses {failed}, so no arm can "
                    "satisfy this verifier and every result it produces is a manufactured null",
                )


class TestNaiveFixesMissTheSubtleCriterion(unittest.TestCase):
    def test_naive_overlay_honours_the_declared_contract(self):
        for task_id in ALL_TASKS:
            with self.subTest(task=task_id):
                must_pass, must_fail, control = _naive_contract(task_id)
                criteria = _verify(task_id, "refs/naive")

                for name in must_pass:
                    self.assertIn(name, criteria)
                    self.assertTrue(
                        criteria[name],
                        f"{task_id}: the naive fix does not satisfy {name}, so the overlay "
                        "is too weak to bound the easy path",
                    )
                for name in must_fail:
                    self.assertIn(name, criteria)
                    self.assertFalse(
                        criteria[name],
                        f"{task_id}: the naive fix SATISFIES {name} -- this task is not a "
                        "trap and cannot tell two arms apart. Re-author it before spending.",
                    )
                if control:
                    self.assertTrue(all(criteria.values()))


if __name__ == "__main__":
    unittest.main()
