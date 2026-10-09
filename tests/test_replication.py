"""Tests for fathom.replication: the bank's ``[plan]`` table and the replication status.

Run via pytest or directly:  python tests/test_replication.py
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom import replication

_MANIFEST = 'name = "b"\ndataset_version = "1"\nholdout = []\n'


def _trial(arm: str, task: str, repeat: int, *, status: str = "completed", **extra) -> dict:
    row = {
        "kind": "trial",
        "bank": "b",
        "scenario": arm,
        "config_hash": extra.pop("config_hash", arm * 4),
        "task_id": task,
        "repeat": repeat,
        "status": status,
        "dataset_version": extra.pop("dataset_version", "1"),
    }
    row.update(extra)
    return row


class ParsePlan(unittest.TestCase):
    def test_absent_table_and_absent_key_are_undeclared(self) -> None:
        self.assertIsNone(replication.parse_plan({"name": "b"}))
        self.assertIsNone(replication.parse_plan({"plan": {}}))

    def test_a_positive_integer_is_the_declared_value(self) -> None:
        self.assertEqual(replication.parse_plan({"plan": {"repeats_per_cell": 1}}), 1)
        self.assertEqual(replication.parse_plan({"plan": {"repeats_per_cell": 5}}), 5)

    def test_malformed_plans_raise(self) -> None:
        cases = {
            "not a table": {"plan": "3"},
            "zero": {"plan": {"repeats_per_cell": 0}},
            "negative": {"plan": {"repeats_per_cell": -2}},
            "bool": {"plan": {"repeats_per_cell": True}},
            "string": {"plan": {"repeats_per_cell": "3"}},
            "float": {"plan": {"repeats_per_cell": 3.0}},
            "typo": {"plan": {"repeats_per_cel": 3}},
            "extra key": {"plan": {"repeats_per_cell": 3, "notes": "x"}},
        }
        for name, manifest in cases.items():
            with self.subTest(name), self.assertRaises(replication.PlanError) as ctx:
                replication.parse_plan(manifest)
            self.assertIn("plan", str(ctx.exception))

    def test_a_typo_names_the_unknown_key(self) -> None:
        with self.assertRaises(replication.PlanError) as ctx:
            replication.parse_plan({"plan": {"repeats_per_cel": 3}})
        self.assertIn("repeats_per_cel", str(ctx.exception))
        self.assertIn("repeats_per_cell", str(ctx.exception))


class ReadPlan(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.bank_dir = Path(self._tmp.name) / "b"
        self.bank_dir.mkdir()

    def _write(self, text: str) -> None:
        (self.bank_dir / "bank.toml").write_text(text, encoding="utf-8")

    def test_a_declared_plan(self) -> None:
        self._write(_MANIFEST + "[plan]\nrepeats_per_cell = 3\n")
        reading = replication.read_plan(self.bank_dir)
        self.assertEqual(reading.repeats_per_cell, 3)
        self.assertIsNone(reading.problem)
        self.assertEqual(reading.path, self.bank_dir / "bank.toml")

    def test_an_undeclared_plan(self) -> None:
        self._write(_MANIFEST)
        reading = replication.read_plan(self.bank_dir)
        self.assertIsNone(reading.repeats_per_cell)
        self.assertIsNone(reading.problem)
        self.assertFalse(reading.missing)

    def test_a_missing_manifest_reads_as_undeclared_and_says_so(self) -> None:
        reading = replication.read_plan(self.bank_dir)
        self.assertIsNone(reading.repeats_per_cell)
        self.assertTrue(reading.missing)
        self.assertIn("no tasks/b/bank.toml", replication.undeclared_reason(reading, "tasks/b"))

    def test_a_malformed_plan_reads_as_undeclared_with_its_problem(self) -> None:
        self._write(_MANIFEST + "[plan]\nrepeats_per_cell = 0\n")
        reading = replication.read_plan(self.bank_dir)
        self.assertIsNone(reading.repeats_per_cell)
        self.assertIsNotNone(reading.problem)
        reason = replication.undeclared_reason(reading, "tasks/b")
        self.assertIn("malformed", reason)
        self.assertIn(reading.problem or "", reason)

    def test_an_unparseable_manifest_is_a_problem_not_an_exception(self) -> None:
        self._write("name = \n")
        reading = replication.read_plan(self.bank_dir)
        self.assertIsNone(reading.repeats_per_cell)
        self.assertIsNotNone(reading.problem)


class Labels(unittest.TestCase):
    def test_the_row_label_describes_the_plan(self) -> None:
        self.assertEqual(replication.label(None), "directional")
        self.assertEqual(replication.label(1), "directional")
        self.assertEqual(replication.label(2), "replicated")
        self.assertEqual(replication.label(7), "replicated")

    def test_underpowered_is_strictly_below(self) -> None:
        self.assertTrue(replication.underpowered(1, 2))
        self.assertFalse(replication.underpowered(2, 2))
        self.assertFalse(replication.underpowered(0, 0))


class PlanLine(unittest.TestCase):
    def test_directional_states(self) -> None:
        for declared, run in ((None, 2), (None, 5), (1, 1), (1, 3), (3, 1), (3, 2)):
            with self.subTest(declared=declared, run=run):
                line = replication.plan_line(declared, run)
                self.assertTrue(line.startswith("replication: "), line)
                self.assertIn("repeats_per_cell", line)
                self.assertIn("directional", line)

    def test_a_run_that_buys_the_plan_is_not_directional(self) -> None:
        for declared, run in ((2, 2), (3, 3), (3, 4)):
            with self.subTest(declared=declared, run=run):
                line = replication.plan_line(declared, run)
                self.assertIn("repeats_per_cell = ", line)
                self.assertNotIn("directional", line)

    def test_pinned_text(self) -> None:
        self.assertEqual(
            replication.plan_line(None, 2),
            "replication: no [plan] repeats_per_cell in bank.toml; any contrast from this run "
            "is directional",
        )
        self.assertEqual(
            replication.plan_line(3, 1),
            "replication: repeats_per_cell = 3 in bank.toml, and this run asks for 1 repeat "
            "per cell: a screen; any contrast from it is directional",
        )
        self.assertEqual(
            replication.plan_line(3, 3),
            "replication: repeats_per_cell = 3 in bank.toml; this run asks for 3 repeats per cell",
        )


class CellCounts(unittest.TestCase):
    def test_completed_trials_per_arm_and_task(self) -> None:
        rows = [
            _trial("bare", "add", 0),
            _trial("bare", "add", 1, status="errored"),
            _trial("bare", "sub", 0),
            _trial("nudge", "add", 0),
            _trial("nudge", "add", 1),
            {"kind": "run", "config_hash": "x", "task_id": "add", "repeat": 0},
        ]
        self.assertEqual(
            replication.cell_counts(rows),
            {("bare", "add"): 1, ("bare", "sub"): 1, ("nudge", "add"): 2},
        )

    def test_a_cell_rerun_counts_its_last_row(self) -> None:
        rows = [_trial("bare", "add", 0, status="errored"), _trial("bare", "add", 0)]
        self.assertEqual(replication.cell_counts(rows), {("bare", "add"): 1})
        rows = [_trial("bare", "add", 0), _trial("bare", "add", 0, status="errored")]
        self.assertEqual(replication.cell_counts(rows), {("bare", "add"): 0})

    def test_the_arm_name_is_the_last_one_its_hash_carries(self) -> None:
        rows = [
            _trial("old", "add", 0, config_hash="h"),
            _trial("new", "add", 1, config_hash="h"),
        ]
        self.assertEqual(replication.cell_counts(rows), {("new", "add"): 2})

    def test_current_version_rows_apply_voids_and_keep_the_last_version(self) -> None:
        rows = [
            _trial("bare", "add", 0, dataset_version="1"),
            _trial("bare", "add", 0, dataset_version="2"),
            _trial("bare", "add", 1, dataset_version="2"),
            {
                "kind": "void",
                "bank": "b",
                "dataset_version": "2",
                "task_id": "add",
                "config_hash": "barebarebarebare",
                "repeat": 1,
            },
        ]
        kept = [r for r in replication.current_version_rows(rows) if r["kind"] == "trial"]
        self.assertEqual([(r["dataset_version"], r["repeat"]) for r in kept], [("2", 0)])


class Assess(unittest.TestCase):
    def test_undeclared_and_one_are_directional_whatever_the_cells_hold(self) -> None:
        counts = {("bare", "add"): 5}
        self.assertTrue(replication.assess(None, counts).directional)
        self.assertTrue(replication.assess(1, counts).directional)
        self.assertEqual(replication.assess(1, counts).short, ())

    def test_a_declared_plan_lists_the_short_cells(self) -> None:
        counts = {("bare", "add"): 3, ("nudge", "add"): 1, ("nudge", "sub"): 0}
        result = replication.assess(3, counts)
        self.assertTrue(result.directional)
        self.assertEqual(result.short, ((("nudge", "add"), 1), (("nudge", "sub"), 0)))
        self.assertEqual(result.cells, 3)

    def test_a_met_plan_is_not_directional(self) -> None:
        result = replication.assess(2, {("bare", "add"): 2, ("nudge", "add"): 4})
        self.assertFalse(result.directional)
        self.assertEqual(result.short, ())


class ScorecardLine(unittest.TestCase):
    def _reading(self, repeats: int | None, **kw) -> replication.PlanReading:
        return replication.PlanReading(
            repeats_per_cell=repeats, path=Path("unused") / "bank.toml", **kw
        )

    def test_undeclared(self) -> None:
        line = replication.scorecard_line(self._reading(None), {}, "tasks/b")
        self.assertTrue(line.startswith("> **Directional:** "), line)
        self.assertIn("repeats_per_cell", line)
        self.assertTrue(line.endswith("directional, not replicated."), line)

    def test_malformed_says_so_and_missing_reads_as_undeclared(self) -> None:
        line = replication.scorecard_line(self._reading(None, problem="bad"), {}, "tasks/b")
        self.assertTrue(line.startswith("> **Directional:** "))
        self.assertIn("malformed", line)
        missing = replication.scorecard_line(self._reading(None, missing=True), {}, "tasks/b")
        undeclared = replication.scorecard_line(self._reading(None), {}, "tasks/b")
        self.assertEqual(missing, undeclared, "a scorecard without tasks/ renders the same")

    def test_one(self) -> None:
        line = replication.scorecard_line(self._reading(1), {("a", "t"): 1}, "tasks/b")
        self.assertTrue(line.startswith("> **Directional:** "))
        self.assertIn("1 repeat", line)

    def test_short(self) -> None:
        counts = {("a", "t"): 3, ("c", "t"): 1}
        line = replication.scorecard_line(self._reading(3), counts, "tasks/b")
        self.assertTrue(line.startswith("> **Directional:** "))
        self.assertIn("1 of 2", line)
        self.assertIn("3", line)

    def test_met(self) -> None:
        counts = {("a", "t"): 3, ("c", "t"): 4}
        line = replication.scorecard_line(self._reading(3), counts, "tasks/b")
        self.assertFalse(line.startswith(">"), line)
        self.assertNotIn("irectional", line)
        self.assertIn("repeats_per_cell = 3", line)


if __name__ == "__main__":
    unittest.main()
