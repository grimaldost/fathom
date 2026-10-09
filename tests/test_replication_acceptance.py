"""Acceptance test: a study plan declares repeats per cell, and a plan that declares none, or one,
marks the report and the ledger "directional" and draws a reconcile warning.

It drives the real command line end to end (`run --dry-run`, `run`, `report`, `index --write`,
`reconcile`) against a copy of `examples/data-root`, with the agent spawn stubbed the way
`tests/test_cli_data_root.py` stubs it, so it spends nothing.

The contract it holds:

- `tasks/<bank>/bank.toml` may carry `[plan] repeats_per_cell = N` (an integer, 1 or more). It is
  not hashed: it changes no `config_hash` and no resume key.
- The dry-run plan says "directional" when the plan declares no `repeats_per_cell`, declares 1, or
  declares more than the run buys, and does not say it when the run buys what the plan declares.
- Every new trial row carries `plan_repeats_per_cell` (the declared value, or null) and
  `plan_replication` ("directional" when the plan declares none or 1, "replicated" when it
  declares 2 or more). Earlier rows are never rewritten.
- The scorecard carries a `> **Directional:**` line between its title and its first section when
  the plan declares none or 1, or when an arm x task cell holds fewer completed trials than the
  plan declares, and no such line once every cell holds what the plan declares.
- `fathom reconcile` prints `[WARNING] [replication] <bank> (<key>): ...` for such a bank and
  still exits 0 with `RECONCILE: OK`; the key is `undeclared`, `one`, or starts with `short`.
- A malformed `[plan]` stops `run` before it plans anything.

Set FATHOM_ENGINE_UNDER_TEST to an engine checkout to test that checkout; otherwise the checkout
holding this file is tested.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

ENGINE = Path(os.environ.get("FATHOM_ENGINE_UNDER_TEST") or Path(__file__).resolve().parents[1])
FIXTURE = ENGINE / "examples" / "data-root"
sys.path.insert(0, str(ENGINE / "src"))
os.environ.pop("FATHOM_HOME", None)

from fathom.adapters.base import ExitStatus  # noqa: E402
from fathom.adapters.base import RunRecord as AdapterRunRecord  # noqa: E402
from fathom.cli import main  # noqa: E402
from fathom.strategies.base import PIN_STRONG, TrialResult, TrialStatus  # noqa: E402

BANK = "example"
WARNING = re.compile(r"^\[WARNING\] \[replication\] example \(([^)]+)\)", re.MULTILINE)


def _call(argv: list[str], *, cwd: Path) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with (
        contextlib.chdir(cwd),
        mock.patch.dict(os.environ, {}),
        contextlib.redirect_stdout(out),
        contextlib.redirect_stderr(err),
    ):
        os.environ.pop("FATHOM_HOME", None)
        try:
            code = main(argv)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class _SolvingExecutor:
    """What an agent and the adapter would leave behind, with nothing spawned."""

    def run_trial(self, task, workspace, scenario, runner):
        shutil.copy(Path(task.task_dir) / "solution" / "calc.py", Path(workspace) / "calc.py")
        run = AdapterRunRecord(
            status=ExitStatus.OK,
            tokens_in=100,
            tokens_out=50,
            num_turns=3,
            duration_s=10.0,
            cost_usd_est=0.01,
            cli_version="0.0.0 (stub)",
            usage={"input_tokens": 100, "output_tokens": 50},
            model_id="stub-model",
        )
        return TrialResult(
            status=TrialStatus.COMPLETED, runs=[run], pin_level=PIN_STRONG, wall_clock_s=10.0
        )


@contextlib.contextmanager
def _no_spawns():
    with (
        mock.patch("fathom.cli._default_executor_factory", lambda sc, **kw: _SolvingExecutor()),
        mock.patch("fathom.cli._default_runner_factory", lambda sc, **kw: object()),
    ):
        yield


def _fresh_root(base: Path, name: str, plan: str | None) -> Path:
    """A copy of the example data root with an empty ledger, no reconcile exceptions, and the
    bank manifest's three keys followed by *plan* (TOML text) when given."""
    root = base / name
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("__pycache__", "report"))
    (root / "ledger" / f"{BANK}.jsonl").unlink()
    (root / "fathom.toml").write_text("[data_root]\nschema = 1\n", encoding="utf-8")
    _set_plan(root, plan)
    return root


def _set_plan(root: Path, plan: str | None) -> None:
    manifest = root / "tasks" / BANK / "bank.toml"
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    holdout = ", ".join(json.dumps(h) for h in data["holdout"])
    text = (
        f"name = {json.dumps(data['name'])}\n"
        f"dataset_version = {json.dumps(data['dataset_version'])}\n"
        f"holdout = [{holdout}]\n"
    )
    if plan is not None:
        text += "\n" + plan.strip() + "\n"
    manifest.write_text(text, encoding="utf-8")


def _run_args(repeats: int) -> list[str]:
    return [
        "run",
        BANK,
        "--repeats",
        str(repeats),
        "--skip-arming-check",
        "--skip-credential-check",
    ]


def _dry_run(root: Path, repeats: int) -> tuple[int, str, str]:
    return _call(["run", BANK, "--repeats", str(repeats), "--dry-run"], cwd=root)


def _buy(root: Path, repeats: int) -> None:
    with _no_spawns():
        code, out, err = _call(_run_args(repeats), cwd=root)
    if code != 0:
        raise AssertionError(f"run exited {code}:\n{out}\n{err}")


def _ledger_lines(root: Path) -> list[str]:
    path = root / "ledger" / f"{BANK}.jsonl"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def _trial_rows(lines: list[str]) -> list[dict]:
    rows = [json.loads(line) for line in lines if line.strip()]
    return [row for row in rows if row.get("kind") == "trial"]


def _scorecard(root: Path) -> str:
    code, out, err = _call(["report", BANK], cwd=root)
    if code != 0:
        raise AssertionError(f"report exited {code}:\n{out}\n{err}")
    return (root / "report" / f"scorecard-{BANK}.md").read_text(encoding="utf-8")


def _banner(scorecard: str) -> str | None:
    """The `> **Directional:**` line between the title and the first section, if any."""
    lines = scorecard.splitlines()
    title = next(i for i, line in enumerate(lines) if line.startswith("# Scorecard"))
    end = next(
        (i for i, line in enumerate(lines) if i > title and line.startswith("## ")), len(lines)
    )
    for line in lines[title + 1 : end]:
        if line.startswith("> **Directional:**"):
            return line
    return None


def _reconcile(root: Path) -> tuple[int, str]:
    code, out, err = _call(["index", "--write"], cwd=root)
    if code != 0:
        raise AssertionError(f"index --write exited {code}:\n{out}\n{err}")
    code, out, err = _call(["reconcile"], cwd=root)
    return code, out + err


class _Case(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class UndeclaredPlan(_Case):
    def test_dry_run_report_ledger_and_reconcile_say_directional(self) -> None:
        root = _fresh_root(self.base, "undeclared", None)

        code, out, err = _dry_run(root, 2)
        self.assertEqual(code, 0, out + err)
        self.assertIn("directional", out.lower())
        self.assertIn("repeats_per_cell", out)

        _buy(root, 2)
        trials = _trial_rows(_ledger_lines(root))
        self.assertEqual(len(trials), 4, "two arms x one task x two repeats")
        for row in trials:
            self.assertIn("plan_repeats_per_cell", row)
            self.assertIsNone(row["plan_repeats_per_cell"])
            self.assertEqual(row["plan_replication"], "directional")

        banner = _banner(_scorecard(root))
        self.assertIsNotNone(banner, "the scorecard opens with a Directional line")
        self.assertIn("repeats_per_cell", banner)

        code, text = _reconcile(root)
        self.assertEqual(code, 0, text)
        self.assertIn("RECONCILE: OK", text)
        self.assertEqual(WARNING.findall(text), ["undeclared"], text)


class OneRepeatPlan(_Case):
    def test_a_plan_of_one_is_directional_everywhere(self) -> None:
        root = _fresh_root(self.base, "one", "[plan]\nrepeats_per_cell = 1")

        code, out, err = _dry_run(root, 1)
        self.assertEqual(code, 0, out + err)
        self.assertIn("directional", out.lower())

        _buy(root, 1)
        trials = _trial_rows(_ledger_lines(root))
        self.assertEqual(len(trials), 2)
        for row in trials:
            self.assertEqual(row["plan_repeats_per_cell"], 1)
            self.assertEqual(row["plan_replication"], "directional")

        banner = _banner(_scorecard(root))
        self.assertIsNotNone(banner)
        self.assertIn("1 repeat", banner)

        code, text = _reconcile(root)
        self.assertEqual(code, 0, text)
        self.assertIn("RECONCILE: OK", text)
        self.assertEqual(WARNING.findall(text), ["one"], text)


class ReplicatedPlan(_Case):
    def test_a_short_pilot_is_directional_until_the_cells_fill(self) -> None:
        root = _fresh_root(self.base, "three", "[plan]\nrepeats_per_cell = 3")

        code, out, err = _dry_run(root, 1)
        self.assertEqual(code, 0, out + err)
        self.assertIn("directional", out.lower(), "a run below the plan is a screen")

        _buy(root, 1)
        pilot = _ledger_lines(root)
        trials = _trial_rows(pilot)
        self.assertEqual(len(trials), 2)
        for row in trials:
            self.assertEqual(row["plan_repeats_per_cell"], 3)
            self.assertEqual(row["plan_replication"], "replicated")
        self.assertIsNotNone(_banner(_scorecard(root)), "cells below the plan are directional")
        code, text = _reconcile(root)
        self.assertEqual(code, 0, text)
        keys = WARNING.findall(text)
        self.assertTrue(keys, text)
        self.assertTrue(all(key.startswith("short") for key in keys), keys)

        code, out, err = _dry_run(root, 3)
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("directional", out.lower(), "the run buys what the plan declares")

        _buy(root, 3)
        full = _ledger_lines(root)
        self.assertEqual(full[: len(pilot)], pilot, "earlier rows are never rewritten")
        self.assertEqual(len(_trial_rows(full)), 6)
        self.assertIsNone(_banner(_scorecard(root)), "every cell now holds three")
        code, text = _reconcile(root)
        self.assertEqual(code, 0, text)
        self.assertIn("RECONCILE: OK", text)
        self.assertEqual(WARNING.findall(text), [], text)


class PlanIsNotHashed(_Case):
    def test_config_hash_and_resume_key_do_not_move(self) -> None:
        keys = {}
        for name, plan in (("none", None), ("three", "[plan]\nrepeats_per_cell = 3")):
            root = _fresh_root(self.base, name, plan)
            _buy(root, 1)
            keys[name] = sorted(
                (r["task_id"], r["scenario"], r["config_hash"], r["dataset_version"], r["repeat"])
                for r in _trial_rows(_ledger_lines(root))
            )
        self.assertEqual(keys["none"], keys["three"])


class MalformedPlan(_Case):
    def test_run_refuses_a_malformed_plan(self) -> None:
        for i, plan in enumerate(
            (
                "[plan]\nrepeats_per_cell = 0",
                "[plan]\nrepeats_per_cell = true",
                '[plan]\nrepeats_per_cell = "3"',
                "[plan]\nrepeats_per_cel = 3",
                'plan = "3"',
            )
        ):
            with self.subTest(plan=plan):
                root = _fresh_root(self.base, f"bad{i}", plan)
                code, out, err = _dry_run(root, 2)
                self.assertNotEqual(code, 0, out + err)
                self.assertIn("plan", (out + err).lower())


class ShippedRoots(_Case):
    def test_the_example_data_root_still_reconciles(self) -> None:
        root = self.base / "example-copy"
        shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("__pycache__", "report"))
        code, out, err = _call(["reconcile"], cwd=root)
        self.assertEqual(code, 0, out + err)
        self.assertIn("RECONCILE: OK", out + err)

    def test_the_engine_checkout_draws_no_replication_warning(self) -> None:
        code, out, err = _call(["reconcile"], cwd=ENGINE)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(WARNING.findall(out + err), [])


if __name__ == "__main__":
    unittest.main()
