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


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
