"""The per-spawn budget cap is threadable from the CLI to the runner.

The runner's ``default_max_budget_usd`` (5.0) was once unreachable from ``fathom run``,
so there was no way to set the cap from a pilot's observed cost. These stub-only tests
(no spawn) assert the value reaches ``ClaudeCliRunner`` and that omitting the flag
preserves the 5.0 default.
"""

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from fathom.cli import _default_runner_factory  # noqa: E402
from fathom.scenario import load_scenario, resolve_scenario  # noqa: E402


class _Resolver:
    def resolve_model_id(self, model):
        return None

    def resolve_tool_repo_sha(self, repo):
        return "x"

    def build_tool_invocation_cmd(self, repo):
        return "x"

    def resolve_plugin_meta(self, plugin_dir):
        return ("n", "v", "s")


def _scenario():
    sc_file = REPO / "tests" / "fixtures" / "scenarios" / "bare.toml"
    return resolve_scenario(load_scenario(sc_file), _Resolver())


class TestBudgetCapThreading(unittest.TestCase):
    def test_flag_value_reaches_the_runner(self):
        runner = _default_runner_factory(_scenario(), max_budget_usd=1.5)
        self.assertEqual(runner.default_max_budget_usd, 1.5)

    def test_omitting_preserves_the_5_dollar_default(self):
        runner = _default_runner_factory(_scenario())
        self.assertEqual(runner.default_max_budget_usd, 5.0)

    def test_the_planned_ceiling_is_computed_from_the_cap_that_will_bind(self):
        """The plan's ceiling must move when the cap moves, or it is not a ceiling.

        `--max-budget-usd` is per-spawn, so a value above the default LOOSENS the only
        runaway guard. While the ceiling was a hardcoded $2/trial it printed the same
        total either way, and a 20x loosening read in the plan as a rail.
        """
        from fathom.cli import _DEFAULT_SPAWN_BUDGET_USD

        self.assertEqual(
            _DEFAULT_SPAWN_BUDGET_USD,
            _default_runner_factory(_scenario()).default_max_budget_usd,
            "the mirrored default drifted from the adapter's real cap",
        )


class TestZeroCapIsHonoured(unittest.TestCase):
    """A cap of 0 is the most restrictive request there is, and it was the one dropped.

    ``if max_budget_usd:`` is false for 0, so "spend nothing on this spawn" fell through
    to the adapter's $5 default — the one value where a silent fallback costs money.
    """

    def _argv(self, cap):
        from fathom.adapters.claude_cli import build_command

        return build_command(
            model="m", effort="high", max_turns=1, max_budget_usd=cap, allowed_tools=()
        )

    def test_a_zero_cap_reaches_the_spawn(self):
        argv = self._argv(0)
        self.assertIn("--max-budget-usd", argv, "a 0 cap was silently dropped")
        self.assertEqual(argv[argv.index("--max-budget-usd") + 1], "0")

    def test_an_ordinary_cap_still_reaches_the_spawn(self):
        argv = self._argv(2.5)
        self.assertEqual(argv[argv.index("--max-budget-usd") + 1], "2.5")


class TestSpendRailFlags(unittest.TestCase):
    """Two spellings for the per-spawn cap, and a separate per-invocation rail."""

    def _parse(self, *argv):
        from fathom.cli import _build_parser

        return _build_parser().parse_args(["run", "b", *argv])

    def test_the_rail_is_a_separate_flag_from_the_per_spawn_cap(self):
        args = self._parse("--max-spawn-usd", "2", "--max-run-usd", "30")
        self.assertEqual(args.max_spawn_usd, 2.0)
        self.assertEqual(args.max_run_usd, 30.0)
        self.assertIsNone(args.legacy_max_budget_usd)

    def test_the_legacy_spelling_parses_into_its_own_dest(self):
        """It must keep working: it appears in published reports and in hashed plugin trees,
        where an edit would fork a committed ledger's resume key."""
        args = self._parse("--max-budget-usd", "3")
        self.assertEqual(args.legacy_max_budget_usd, 3.0)
        self.assertIsNone(args.max_spawn_usd)

    def test_both_spellings_land_in_distinct_dests_so_neither_silently_wins(self):
        args = self._parse("--max-spawn-usd", "2", "--max-budget-usd", "9")
        self.assertEqual((args.max_spawn_usd, args.legacy_max_budget_usd), (2.0, 9.0))


# ---------------------------------------------------------------------------
# Expected spend beside the ceiling (FATH-B80)
# ---------------------------------------------------------------------------


def _expected_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.startswith("expected:")]


class TestExpectedSpend(unittest.TestCase):
    """The plan prints what a trial has cost in this ledger, beside the worst-case ceiling.

    Information only: the money rail stays on observed spend, so nothing here changes an
    exit code, and the ``planned:`` line (which the acceptance harness matches) is untouched.
    """

    BANK = "hist-bank"

    def setUp(self):
        import shutil
        import tempfile

        self._tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.ledger_dir = self._tmp / "ledger"
        self.tasks = [self._task("task-1"), self._task("task-2")]

    def _task(self, task_id):
        from fathom.taskbank import Task

        return Task(
            id=task_id,
            instruction="do it",
            limits={},
            verify={"entry": "verify.py"},
            task_dir=self._tmp,
        )

    def _scenario(self, strategy="single-session", model="example-model", config_hash="a" * 64):
        from fathom.scenario import LimitsOverride, ResolvedScenario, ToolsConfig

        return ResolvedScenario(
            name="bare",
            config_hash=config_hash,
            adapter="claude-cli",
            model=model,
            strategy=strategy,
            effort="high",
            tools=ToolsConfig(source="none"),
            limits=LimitsOverride(),
            model_id=None,
            tool_repo_sha=None,
            tool_invocation_cmd=None,
        )

    def _append(self, row):
        import fathom.ledger as ledger

        ledger.append_record(self.BANK, row, ledger_dir=self.ledger_dir)

    def _trial(
        self,
        task_id,
        costs,
        *,
        status="completed",
        strategy="single-session",
        model="example-model",
        repeat=0,
        config_hash="b" * 64,
        preimage=True,
        sources=None,
    ):
        """One recorded trial: a run row per entry of `costs`, then the trial row."""
        key = {
            "bank": self.BANK,
            "task_id": task_id,
            "repeat": repeat,
            "dataset_version": "v1",
            "config_hash": config_hash,
            "tool_git_sha": "x",
            "cli_version": "1.0",
            "pin_level": "strong",
        }
        pre = json.dumps({"strategy": strategy, "model": model}) if preimage else ""
        for i, cost in enumerate(costs):
            self._append(
                {
                    **key,
                    "kind": "run",
                    "usage": {},
                    "turns": 1,
                    "duration": 1.0,
                    "exit_code": 0,
                    "cost_usd_est": cost,
                    "cost_source": (sources or {}).get(i, "reported"),
                    "config_preimage": pre,
                }
            )
        self._append({**key, "kind": "trial", "status": status, "config_preimage": pre})

    def _history(self):
        self._trial("old-1", [0.10])
        self._trial("old-2", [0.05, 0.15])
        self._trial("old-3", [0.40])

    def _plan(self, scenarios=None, **kw):
        import io

        from fathom.cli import run_matrix
        from fathom.taskbank import Bank

        bank = Bank(name=self.BANK, dataset_version="v1", tasks=self.tasks, holdout=[])
        out = io.StringIO()
        code = run_matrix(
            bank,
            scenarios or [self._scenario()],
            2,
            dry_run=True,
            ledger_dir=self.ledger_dir,
            out=out,
            **kw,
        )
        return code, out.getvalue()

    def test_median_n_and_expected_spend_from_the_ledgers_own_trials(self):
        self._history()
        code, text = self._plan()
        self.assertEqual(code, 0)
        (line,) = _expected_lines(text)
        self.assertEqual(
            line,
            "expected: ~$0.80 for 4 planned trials (median per trial from 3 completed "
            "trials in this ledger: single-session $0.20 n=3); an estimate, not a cap",
        )

    def test_it_sits_after_the_planned_line_and_never_inside_it(self):
        self._history()
        _, text = self._plan()
        lines = text.splitlines()
        planned = next(i for i, ln in enumerate(lines) if ln.startswith("planned:"))
        self.assertNotIn("expected", lines[planned])
        self.assertTrue(lines[planned + 1].startswith("expected:"))

    def test_a_trial_with_a_run_that_reported_no_cost_is_excluded(self):
        """FATH-B79: a missing cost is not free, so the trial leaves the median out."""
        self._history()
        self._trial("old-4", [0.01, 0.0], sources={1: "none"})
        _, text = self._plan()
        (line,) = _expected_lines(text)
        self.assertIn("single-session $0.20 n=3", line)

    def test_errored_and_voided_trials_are_excluded(self):
        self._history()
        self._trial("old-4", [9.0], status="errored")
        self._trial("old-5", [9.0])
        self._append(
            {
                "kind": "void",
                "bank": self.BANK,
                "task_id": "old-5",
                "repeat": 0,
                "dataset_version": "v1",
                "config_hash": "b" * 64,
                "scenario": "bare",
                "reason": "instrument defect",
            }
        )
        _, text = self._plan()
        (line,) = _expected_lines(text)
        self.assertIn("single-session $0.20 n=3", line)

    def test_a_retried_trial_counts_only_the_completed_attempt(self):
        """An errored attempt's spawns are not part of what the retry cost."""
        self._history()
        self._trial("old-4", [9.0], status="errored")
        self._trial("old-4", [0.20])
        _, text = self._plan()
        (line,) = _expected_lines(text)
        self.assertIn("single-session $0.20 n=4", line)

    def test_a_trial_with_no_run_rows_is_skipped(self):
        self._history()
        self._trial("old-4", [])
        _, text = self._plan()
        (line,) = _expected_lines(text)
        self.assertIn("single-session $0.20 n=3", line)

    def test_an_empty_ledger_prints_no_expected_line(self):
        code, text = self._plan()
        self.assertEqual(code, 0)
        self.assertEqual(_expected_lines(text), [])

    def test_nothing_planned_prints_no_expected_line(self):
        self._history()
        _, text = self._plan(limit=0)
        self.assertEqual(_expected_lines(text), [])

    def test_history_changes_neither_the_exit_code_nor_the_planned_line(self):
        code_without, without = self._plan()
        self._history()
        code_with, with_history = self._plan()
        self.assertEqual(code_without, code_with)

        def planned(text):
            return next(ln for ln in text.splitlines() if ln.startswith("planned:"))

        self.assertEqual(planned(without).encode(), planned(with_history).encode())
        self.assertEqual(
            [ln for ln in with_history.splitlines() if not ln.startswith("expected:")],
            without.splitlines(),
        )

    def test_a_row_without_a_preimage_joins_a_resolved_scenario_by_config_hash(self):
        for i, cost in enumerate((0.10, 0.20, 0.40)):
            self._trial(f"old-{i}", [cost], preimage=False, config_hash="a" * 64)
        _, text = self._plan()
        (line,) = _expected_lines(text)
        self.assertIn("single-session $0.20 n=3", line)

    def test_a_row_with_neither_preimage_nor_scenario_is_skipped(self):
        self._trial("old-1", [0.50], preimage=False, config_hash="c" * 64)
        _, text = self._plan()
        self.assertEqual(_expected_lines(text), [])

    def test_a_model_with_five_trials_gets_its_own_median(self):
        for i in range(5):
            self._trial(f"m-{i}", [0.40], model="example-model")
        for i in range(6):
            self._trial(f"o-{i}", [0.10], model="other-model")
        _, text = self._plan()
        (line,) = _expected_lines(text)
        self.assertIn("single-session $0.10 n=11", line)
        self.assertIn("single-session/example-model $0.40 n=5", line)
        self.assertIn("expected: ~$1.60 for 4 planned trials", line)

    def test_a_model_with_four_trials_falls_back_to_the_strategy_median(self):
        for i in range(4):
            self._trial(f"m-{i}", [0.40], model="example-model")
        for i in range(6):
            self._trial(f"o-{i}", [0.10], model="other-model")
        _, text = self._plan()
        (line,) = _expected_lines(text)
        self.assertNotIn("single-session/example-model", line)
        self.assertIn("single-session $0.10 n=10", line)
        self.assertIn("expected: ~$0.40 for 4 planned trials", line)

    def test_a_planned_strategy_with_no_history_is_named_not_priced(self):
        self._history()
        scenarios = [
            self._scenario(),
            self._scenario(strategy="nudge", config_hash="d" * 64),
        ]
        _, text = self._plan(scenarios)
        (line,) = _expected_lines(text)
        self.assertIn("expected: ~$0.80 for 4 planned trials", line)
        self.assertIn("no history for strategy nudge (4 planned trials)", line)
        self.assertTrue(line.endswith("an estimate, not a cap"))

    def test_history_for_no_planned_strategy_prices_nothing(self):
        self._history()
        _, text = self._plan([self._scenario(strategy="nudge", config_hash="d" * 64)])
        (line,) = _expected_lines(text)
        self.assertNotIn("~$", line)
        self.assertIn("no history for strategy nudge (4 planned trials)", line)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
