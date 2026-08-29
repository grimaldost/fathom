"""§11 — the per-spawn budget cap is threadable from the CLI to the runner.

Before §11 the runner's ``default_max_budget_usd`` (5.0) was unreachable from
``fathom run`` (FM-N5): the DoD's "set the cap from the pilot's observed cost" had no
seam. These stub-only tests (no spawn) assert the value reaches ``ClaudeCliRunner``
and that omitting the flag preserves the 5.0 default.
"""

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
    sc_file = REPO / "scenarios" / "model-tier" / "haiku.toml"
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


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)


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
