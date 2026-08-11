"""Tests for the scorecard's spread / N / health rendering (FATH-B05).

The scorecard rendered point estimates it already had the data to qualify, and
verdicts flipped as a result:

* the Economy table's per-arm mean misled the direction on 3 of 5 banks, and the
  ledger was hand-parsed per trial on all four runs to recover the real signal
  (one bimodal control arm, one single blow-up run);
* the same means reversed sign between n=2 and n=3 on the same arms and bank, and
  the Pareto star moved with them;
* an arm's mean turns (41.1) exceeded the task's ``max_turns`` (40) with nothing
  marking it — an arm sitting at the cap has a pass rate that is a lower bound,
  not a score.

Stdlib-only: ``python tests/test_report_spread.py`` runs without uv.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import fathom.report as report  # noqa: E402


def _ch(sc: str) -> str:
    """A distinct config_hash per arm — arms sharing one collapse into a single row."""
    import hashlib

    return hashlib.sha256(sc.encode()).hexdigest()


def _trial(sc: str, tid: str, rep: int, *, ok: bool = True, status: str = "completed") -> dict:
    return {
        "kind": "trial",
        "bank": "b",
        "scenario": sc,
        "task_id": tid,
        "repeat": rep,
        "status": status,
        "dataset_version": "1",
        "config_hash": _ch(sc),
        "tool_git_sha": "",
        "cli_version": "1",
        "pin_level": "strong",
        "verifier_results": {"ok": ok} if status == "completed" else None,
        "detail": "",
        "holdout": False,
    }


def _run(sc: str, tid: str, rep: int, *, tokens: int, turns: int, wall: float = 1.0) -> dict:
    return {
        "kind": "run",
        "bank": "b",
        "task_id": tid,
        "repeat": rep,
        "usage": {"input_tokens": tokens // 2, "output_tokens": tokens - tokens // 2},
        "turns": turns,
        "duration": wall,
        "exit_code": 0,
        "dataset_version": "1",
        "config_hash": _ch(sc),
        "tool_git_sha": "",
        "cli_version": "1",
        "pin_level": "strong",
        "cost_usd_est": 0.1,
        "model_id": "m",
    }


class _Rendered:
    """Write a ledger to a temp dir and render it."""

    def __init__(self, rows: list[dict], task_toml: dict[str, str] | None = None) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.ledger_dir = root / "ledger"
        self.ledger_dir.mkdir()
        (self.ledger_dir / "b.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
        )
        self.out_dir = root / "report"
        self.tasks_dir = root / "tasks"
        for tid, body in (task_toml or {}).items():
            d = self.tasks_dir / "b" / tid
            d.mkdir(parents=True)
            (d / "task.toml").write_text(body, encoding="utf-8")

    def text(self) -> str:
        path = report.render(
            "b",
            ledger_dir=self.ledger_dir,
            report_dir=self.out_dir,
            tasks_dir=self.tasks_dir,
        )
        return Path(path).read_text(encoding="utf-8")

    def __enter__(self):  # noqa: ANN204
        return self

    def __exit__(self, *a) -> None:  # noqa: ANN002
        self.tmp.cleanup()


class SpreadTests(unittest.TestCase):
    def test_economy_reports_per_cell_N(self) -> None:
        rows = []
        for rep in range(3):
            rows += [_trial("arm", "t1", rep), _run("arm", "t1", rep, tokens=100, turns=5)]
        with _Rendered(rows) as r:
            text = r.text()
        self.assertIn("| N |", text.replace("|N|", "| N |"))
        self.assertRegex(text, r"\|\s*arm\s*\|\s*3\s*\|")

    def test_a_bimodal_arm_shows_its_spread_not_just_its_mean(self) -> None:
        # The recorded failure: one arm's mean was dragged by a single blow-up run
        # and the direction of the verdict flipped. min/median/max makes that visible
        # on the page instead of requiring a hand-parse of the ledger.
        rows = []
        for rep, tok in enumerate((100, 120, 5000)):
            rows += [_trial("arm", "t1", rep), _run("arm", "t1", rep, tokens=tok, turns=5)]
        with _Rendered(rows) as r:
            text = r.text()
        self.assertIn("5000", text, "the blow-up trial must be visible on the page")
        self.assertIn("120", text, "the median must be visible beside the mean")

    def test_turns_spread_is_rendered(self) -> None:
        rows = []
        for rep, turns in enumerate((2, 8, 40)):
            rows += [_trial("arm", "t1", rep), _run("arm", "t1", rep, tokens=100, turns=turns)]
        with _Rendered(rows) as r:
            text = r.text()
        self.assertIn("Turns (min/med/max)", text)
        self.assertIn("2/8/40", text)


class TurnCapHealthTests(unittest.TestCase):
    TASK = 'id = "t1"\ninstruction = "x"\n[limits]\nmax_turns = 10\n[verify]\nentry = "verify.py"\n'

    def test_an_arm_sitting_at_max_turns_is_flagged(self) -> None:
        # A pass rate from an arm truncated at the cap is a LOWER BOUND, not a score.
        rows = []
        for rep, turns in enumerate((10, 10, 3)):
            rows += [_trial("arm", "t1", rep), _run("arm", "t1", rep, tokens=100, turns=turns)]
        with _Rendered(rows, task_toml={"t1": self.TASK}) as r:
            text = r.text()
        self.assertIn("Arm Health", text)
        self.assertIn("2/3", text, "two of three trials hit the turn cap")
        self.assertIn("lower bound", text)

    def test_an_arm_well_under_the_cap_is_not_flagged(self) -> None:
        rows = []
        for rep in range(3):
            rows += [_trial("arm", "t1", rep), _run("arm", "t1", rep, tokens=100, turns=2)]
        with _Rendered(rows, task_toml={"t1": self.TASK}) as r:
            text = r.text()
        self.assertNotIn("lower bound", text)


class ParetoContestedTests(unittest.TestCase):
    def _rows(self, arm_a_tokens: list[int], arm_b_tokens: list[int]) -> list[dict]:
        rows = []
        for rep, tok in enumerate(arm_a_tokens):
            rows += [_trial("arm-a", "t1", rep), _run("arm-a", "t1", rep, tokens=tok, turns=5)]
        for rep, tok in enumerate(arm_b_tokens):
            rows += [_trial("arm-b", "t1", rep), _run("arm-b", "t1", rep, tokens=tok, turns=5)]
        return rows

    def test_a_pareto_star_is_qualified_when_the_arms_spreads_overlap(self) -> None:
        # Same quality, means differ, ranges overlap heavily: the star is an artefact
        # of where the means happened to land at this n.
        with _Rendered(self._rows([100, 900], [200, 800])) as r:
            text = r.text()
        self.assertIn("★?", text)
        self.assertIn("overlap", text.lower())

    def test_a_clean_separation_keeps_an_unqualified_star(self) -> None:
        with _Rendered(self._rows([100, 110], [900, 910])) as r:
            text = r.text()
        self.assertIn("★", text)
        self.assertNotIn("★?", text)


class InvalidTrialsExcludedTests(unittest.TestCase):
    def test_an_errored_trial_does_not_enter_the_spread(self) -> None:
        rows = [
            _trial("arm", "t1", 0),
            _run("arm", "t1", 0, tokens=100, turns=5),
            _trial("arm", "t1", 1, status="errored"),
            _run("arm", "t1", 1, tokens=99999, turns=999),
        ]
        with _Rendered(rows) as r:
            text = r.text()
        self.assertNotIn("99999", text)
        self.assertRegex(text, r"\|\s*arm\s*\|\s*1\s*\|")


if __name__ == "__main__":
    unittest.main()
