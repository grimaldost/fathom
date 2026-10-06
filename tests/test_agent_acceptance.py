"""The fresh-agent acceptance harness (tools/agent_acceptance.py), offline.

Nothing here spawns ``claude``: the transcript is a synthetic stream in the shape the CLI
emits, the ground truth is read from temporary workspaces, the spawn boundary runs a Python
stand-in, the ``claude`` stub a no-spend subject gets is run by its full path, and the
end-to-end test runs the harness with ``--dry-run`` against a temporary git data root, with
the spawn function replaced by one that fails the test if it is ever called.

Stdlib-only; runs without uv as ``python tests/test_agent_acceptance.py``.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

import agent_acceptance as acc  # noqa: E402

from fathom.adapters.claude_cli import pid_alive  # noqa: E402

CACHE = "C:\\home\\.claude\\plugins\\cache\\fathom\\fathom\\0.8.0"

INIT = {
    "type": "system",
    "subtype": "init",
    "model": "claude-sonnet-5",
    "tools": ["Bash", "Read", "Skill", "mcp__plugin_fathom_fathom__plan"],
    "mcp_servers": [
        {"name": "plugin:fathom:fathom", "status": "connected"},
        {"name": "claude.ai Mail", "status": "needs-auth"},
    ],
    "slash_commands": [
        "fathom:plan",
        "fathom:reconcile",
        "fathom:report",
        "fathom:run",
        "fathom:smoke",
        "fathom:fathom-eval",
        "compact",
    ],
    "skills": ["fathom:fathom-eval", "other:thing"],
    "plugins": [{"name": "fathom", "path": CACHE, "version": "0.8.0"}],
}


def _use(tool_id: str, name: str, tool_input: dict) -> dict:
    block = {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}
    return {"type": "assistant", "message": {"content": [block]}}


def _say(text: str) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _result(tool_id: str, text: object, *, is_error: bool | None = None) -> dict:
    block: dict = {"type": "tool_result", "tool_use_id": tool_id, "content": text}
    if is_error is not None:
        block["is_error"] = is_error
    return {"type": "user", "message": {"content": [block]}}


def _final(text: str = "Done.") -> dict:
    return {"type": "result", "subtype": "success", "is_error": False, "result": text}


PLUGIN_CMD = 'uv run --no-dev --frozen --project "C:/p" python -m fathom --home "C:/d"'
RECONCILED = "reconciling the data root at C:/d\n\nRECONCILE: OK (3 check(s) run, 0 skipped)"
PLANNED = (
    "fathom run: bank=b  scenarios=2  tasks=1  repeats=1\narms:     bare, nudge\n"
    "planned:  2 trials (0 already done)  ceiling: $10.00\n[dry-run] no spawns"
)

# One call per surface, in this order: other, skill, docs, command, cli, mcp (an error),
# cli, command.
STREAM_EVENTS = [
    INIT,
    _use("u0", "Glob", {"pattern": "**/*.toml"}),
    _result("u0", "fathom.toml"),
    _use("u1", "Skill", {"skill": "fathom:fathom-eval"}),
    _result("u1", "Launching skill: fathom:fathom-eval"),
    _use("u2", "Read", {"file_path": CACHE + "\\skills\\fathom-eval\\reference\\authoring.md"}),
    _result("u2", "# Authoring"),
    _use("u3", "Skill", {"skill": "fathom:reconcile"}),
    _result("u3", "Launching skill: fathom:reconcile"),
    _use("u4", "Bash", {"command": f"cd C:/d && {PLUGIN_CMD} reconcile"}),
    _result("u4", RECONCILED, is_error=False),
    _use("u5", "mcp__plugin_fathom_fathom__plan", {"bank": "b"}),
    _result("u5", "boom: the data root is missing " + "x" * 400, is_error=True),
    {"type": "rate_limit_event", "rate_limit_info": {}},
    _use("u6", "Bash", {"command": f"{PLUGIN_CMD} run b --dry-run --repeats 1"}),
    _result("u6", PLANNED),
    _use("u7", "SlashCommand", {"command": "/fathom:report b"}),
    _result("u7", "Launching command"),
    {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "num_turns": 9,
        "duration_ms": 61000,
        "total_cost_usd": 0.4321,
        "result": "Banks: alpha-v1 and beta. Consistent.",
    },
]


def stream_lines(events: list[dict] = STREAM_EVENTS, *, malformed: bool = True) -> list[str]:
    lines = [json.dumps(ev) for ev in events]
    if malformed:
        lines.insert(3, '{"type": "assistant", "message": {"content": [')  # cut off mid-line
        lines.insert(5, "")
    return lines


def _analysis(*events: dict) -> acc.Analysis:
    return acc.analyze(stream_lines([INIT, *events], malformed=False))


def _scenario(**overrides: object) -> acc.Scenario:
    fields = {
        "id": "SX",
        "name": "probe",
        "workspace": "clone",
        "prompt": "Tell me what my evaluations concluded.",
        "checks": (),
    }
    fields.update(overrides)
    return acc.Scenario(**fields)  # type: ignore[arg-type]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _checks(scenario: acc.Scenario, analysis: acc.Analysis, facts: acc.Facts) -> dict:
    return {c.name: c for c in acc.evaluate(scenario, analysis, facts)}


class ScenarioFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenarios = acc.load_scenarios(acc.SCENARIOS_FILE.read_text(encoding="utf-8"))

    def test_the_shipped_scenarios_load(self) -> None:
        self.assertEqual([s.id for s in self.scenarios], ["S1", "S2", "S3"])
        self.assertEqual([s.workspace for s in self.scenarios], ["clone", "empty", "clone"])
        self.assertEqual([s.fathom_home for s in self.scenarios], [True, False, True])
        self.assertEqual(self.scenarios[1].measurement_budget_usd, 1.0)
        self.assertEqual([s.no_spend for s in self.scenarios], [True, False, True])
        self.assertEqual([s.spend_limit_usd for s in self.scenarios], [0.0, 1.5, 0.0])
        self.assertIn("measurement_ran", self.scenarios[1].checks)

    def test_no_shipped_prompt_tells_the_subject_how_to_use_fathom(self) -> None:
        """The prompt guard, held to the real prompts: no command, flag, skill or MCP name."""
        for scenario in self.scenarios:
            with self.subTest(scenario.id):
                self.assertEqual(acc.prompt_violations(scenario), [])
                low = scenario.prompt.lower()
                for term in acc.FORBIDDEN_TERMS:
                    self.assertNotIn(term.lower(), low)

    def test_the_discovery_prompt_never_names_the_tool(self) -> None:
        s3 = next(s for s in self.scenarios if s.id == "S3")
        self.assertFalse(s3.names_tool)
        self.assertNotIn("fathom", s3.prompt.lower())

    def test_every_scenario_gets_the_automatic_checks(self) -> None:
        for scenario in self.scenarios:
            with self.subTest(scenario.id):
                self.assertEqual(
                    acc.checks_for(scenario)[:3],
                    ["session_finished", "data_root_untouched", "output_untouched"],
                )

    def test_selection_keeps_the_order_given_and_ignores_case(self) -> None:
        chosen = acc.select_scenarios(self.scenarios, "s3, S1")
        self.assertEqual([s.id for s in chosen], ["S3", "S1"])
        self.assertEqual(len(acc.select_scenarios(self.scenarios, None)), 3)
        with self.assertRaises(ValueError):
            acc.select_scenarios(self.scenarios, "S9")

    def test_a_malformed_scenario_is_refused(self) -> None:
        good = 'name = "x"\nworkspace = "clone"\nprompt = "p"\n'
        for bad in (
            '[A]\nname = "x"\nworkspace = "nowhere"\nprompt = "p"\n',
            f'[A]\n{good}checks = ["no_such_check"]\n',
            f'[A]\n{good}colour = "red"\n',
            '[A]\nname = "x"\nworkspace = "empty"\nfathom_home = "clone"\nprompt = "p"\n',
            '[A]\nname = "x"\nworkspace = "empty"\nprompt = "p"\nchecks = ["no_ledger_change"]\n',
            f'[A]\n{good}checks = ["measurement_within_budget"]\n',
            f'[A]\n{good}measurement_budget_usd = 1\nchecks = ["no_spend"]\n',
            '[A]\nname = "x"\nworkspace = "clone"\n',
        ):
            with self.subTest(bad), self.assertRaises(ValueError):
                acc.load_scenarios(bad)


class PromptGuardTests(unittest.TestCase):
    def test_every_forbidden_term_is_caught(self) -> None:
        for term in acc.FORBIDDEN_TERMS:
            with self.subTest(term):
                found = acc.prompt_violations(_scenario(prompt=f"Please use {term} now."))
                self.assertTrue(found)

    def test_terms_are_matched_without_regard_to_case(self) -> None:
        self.assertTrue(acc.prompt_violations(_scenario(prompt="set fathom_home first")))

    def test_a_scenario_that_must_not_name_the_tool_rejects_the_word(self) -> None:
        self.assertTrue(acc.prompt_violations(_scenario(prompt="Use Fathom.", names_tool=False)))
        self.assertEqual(acc.prompt_violations(_scenario(prompt="Use Fathom.")), [])


class ExposureGuardTests(unittest.TestCase):
    """Everything the subject is shown besides its prompt is held to the same standard."""

    others = (_scenario(id="S1", name="existing-data"), _scenario(id="S3", name="discovery"))

    def violations(self, shown: dict, **overrides: object) -> list[str]:
        return acc.exposure_violations(_scenario(**overrides), shown, self.others)

    def test_a_neutral_workspace_is_clean(self) -> None:
        shown = {
            "the working directory": "C:/Temp/ws-s1x_k2ab/project",
            "FATHOM_HOME value": "C:/Temp/ws-s1x_k2ab/project/data",
            "workspace entry 'data'": "data",
        }
        self.assertEqual(self.violations(shown, names_tool=False), [])

    def test_the_test_and_its_scenarios_are_not_named(self) -> None:
        for path in (
            "C:/Temp/fathom-agent-acceptance/run/workspace",
            "C:/Temp/existing-data/project",
            "C:/Temp/S1/project",
        ):
            with self.subTest(path):
                self.assertTrue(self.violations({"the working directory": path}))

    def test_a_discovery_scenario_is_not_shown_the_tool_name(self) -> None:
        shown = {"CLAUDE_CONFIG_DIR value": "C:/Temp/fathom_cfg_x"}
        self.assertTrue(self.violations(shown, names_tool=False))
        self.assertEqual(self.violations(shown), [])


class StreamAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analysis = acc.analyze(stream_lines())

    def test_every_surface_is_classified(self) -> None:
        surfaces = [c.surface for c in self.analysis.calls]
        self.assertEqual(
            surfaces, [None, "skill", "docs", "command", "cli", "mcp", "cli", "command"]
        )

    def test_the_operations_are_read_from_each_surface(self) -> None:
        ops = [[inv.op for inv in c.invocations] for c in self.analysis.calls]
        self.assertEqual(
            ops,
            [
                [],
                [],
                [],
                ["reconcile"],
                ["reconcile"],
                ["run --dry-run"],
                ["run --dry-run"],
                ["report"],
            ],
        )

    def test_the_first_fathom_use_counts_the_calls_before_it(self) -> None:
        self.assertEqual(self.analysis.first_fathom_index, 1)

    def test_results_pair_with_their_calls_and_errors_are_excerpted(self) -> None:
        mcp = self.analysis.calls[5]
        self.assertTrue(mcp.is_error)
        self.assertFalse(mcp.succeeded)
        self.assertTrue(self.analysis.calls[4].succeeded)
        errors = acc.fathom_errors(self.analysis)
        self.assertEqual([e["index"] for e in errors], [5])
        self.assertEqual(len(errors[0]["text"]), acc.ERROR_EXCERPT)
        self.assertTrue(errors[0]["text"].startswith("boom"))

    def test_malformed_lines_and_unknown_events_are_counted_not_fatal(self) -> None:
        self.assertEqual(self.analysis.malformed_lines, 1)
        self.assertEqual(self.analysis.other_events, 1)

    def test_the_result_event_is_read(self) -> None:
        result = self.analysis.result or {}
        self.assertEqual(result["total_cost_usd"], 0.4321)
        self.assertEqual(result["num_turns"], 9)

    def test_an_mcp_result_that_reports_not_ok_did_not_succeed(self) -> None:
        payload = [{"type": "text", "text": json.dumps({"ok": False, "error": "no root"})}]
        call = _analysis(_use("m", "mcp__plugin_fathom_fathom__plan", {}), _result("m", payload))
        self.assertFalse(call.calls[0].is_error)
        self.assertFalse(call.calls[0].succeeded)

    def test_a_block_wrapped_result_is_read_as_its_text(self) -> None:
        wrapped = [{"type": "text", "text": RECONCILED}]
        call = _analysis(_use("r", "Bash", {"command": "fathom reconcile"}), _result("r", wrapped))
        self.assertIn("RECONCILE: OK", acc.marker_line(call.calls[0], "reconcile") or "")

    def test_a_stream_without_events_is_analysed_as_empty(self) -> None:
        analysis = acc.analyze(["", "not json", "[1, 2]"])
        self.assertIsNone(analysis.init)
        self.assertEqual(analysis.calls, [])
        self.assertEqual(analysis.malformed_lines, 2)

    def test_valid_json_in_unexpected_shapes_does_not_crash(self) -> None:
        events = [
            dict(
                INIT, slash_commands=7, skills="fathom:fathom-eval", plugins=[3], mcp_servers=None
            ),
            {"type": "assistant", "message": "not an object"},
            {"type": "assistant", "message": {"content": "text, not blocks"}},
            {"type": "assistant", "message": {"content": [5, {"type": "tool_use", "id": ["x"]}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": [1]}]}},
            {"type": "result", "result": None},
        ]
        analysis = acc.analyze(stream_lines(events, malformed=False))
        self.assertEqual(analysis.malformed_lines, 1)
        self.assertEqual(len(analysis.calls), 1)
        self.assertIsNone(analysis.calls[0].result)
        visibility = acc.assess_visibility(analysis)
        self.assertFalse(visibility.ok)
        acc.behaviour(analysis)

    def test_behaviour_is_informational(self) -> None:
        facts = acc.behaviour(self.analysis)
        self.assertEqual(facts["surfaces_used"], ["skill", "docs", "command", "cli", "mcp"])
        self.assertEqual(facts["paid_runs"], 0)
        self.assertEqual(facts["spending_operations"], [])
        self.assertIsNone(facts["budget_rail_used"])
        self.assertIsNone(facts["smoke_before_run"])
        self.assertEqual(facts["plan_ceilings_usd"], ["10.00"])
        self.assertFalse(facts["answer_quotes_plan_ceiling"])

    def test_rails_and_order_before_a_paid_run(self) -> None:
        analysis = _analysis(
            _use("a", "Bash", {"command": "fathom smoke --no-engine-boundary"}),
            _result("a", "SMOKE RESULT: ALL PASS"),
            _use("b", "Bash", {"command": "fathom run b --max-run-usd 1"}),
            _result("b", "done"),
        )
        facts = acc.behaviour(analysis)
        self.assertEqual(facts["paid_runs"], 1)
        self.assertEqual(facts["spending_operations"], ["#0 smoke", "#1 run"])
        self.assertTrue(facts["budget_rail_used"])
        self.assertTrue(facts["smoke_before_run"])
        self.assertFalse(facts["plan_before_run"])

    def test_the_closing_text_is_what_follows_the_last_tool_call(self) -> None:
        analysis = _analysis(
            _say("Looking around."),
            _use("a", "Bash", {"command": "ls"}),
            _result("a", "data"),
            _say("Banks: alpha-v1 and beta."),
            _final("Done."),
        )
        self.assertEqual(analysis.closing_text, "Banks: alpha-v1 and beta.")
        self.assertIn("Done.", analysis.answer)
        self.assertIn("alpha-v1", analysis.answer)


class VisibilityTests(unittest.TestCase):
    def _visibility(self, init: dict | None, *extra: dict) -> acc.Visibility:
        events = ([init] if init else []) + list(extra)
        analysis = acc.analyze(stream_lines(events, malformed=False))
        return acc.assess_visibility(analysis)

    def test_a_connected_server_and_listed_commands_and_skill_are_visible(self) -> None:
        visibility = self._visibility(INIT)
        self.assertTrue(visibility.ok, visibility.problems())
        self.assertEqual(visibility.mcp_servers, ["plugin:fathom:fathom=connected"])
        self.assertEqual(visibility.plugins[0]["version"], "0.8.0")

    def test_a_failed_server_is_an_environment_problem(self) -> None:
        init = dict(INIT, mcp_servers=[{"name": "plugin:fathom:fathom", "status": "failed"}])
        visibility = self._visibility(init)
        self.assertFalse(visibility.ok)
        self.assertIn("plugin:fathom:fathom=failed", visibility.problems()[0])

    def test_a_pending_server_counts_once_one_of_its_tools_answered(self) -> None:
        init = dict(INIT, mcp_servers=[{"name": "plugin:fathom:fathom", "status": "pending"}])
        visibility = self._visibility(
            init, _use("m", "mcp__plugin_fathom_fathom__report", {"bank": "b"}), _result("m", "{}")
        )
        self.assertTrue(visibility.ok)
        self.assertTrue(visibility.mcp_connected_late)
        self.assertFalse(visibility.mcp_unconfirmed)

    def test_a_pending_server_nobody_called_is_unconfirmed_not_a_failure(self) -> None:
        """A headless session starts before its servers connect; a subject that works through
        the command line never calls the server, and that is no reason to stop the run."""
        init = dict(INIT, mcp_servers=[{"name": "plugin:fathom:fathom", "status": "pending"}])
        visibility = self._visibility(init)
        self.assertTrue(visibility.ok)
        self.assertFalse(visibility.mcp_connected)
        self.assertTrue(visibility.mcp_unconfirmed)

    def test_the_preflight_requires_the_probe_to_answer(self) -> None:
        pending = dict(INIT, mcp_servers=[{"name": "plugin:fathom:fathom", "status": "pending"}])
        silent = acc.preflight_problems(self._visibility(pending))
        self.assertEqual(len(silent), 1)
        self.assertIn("never answered the probe", silent[0])
        answered = self._visibility(
            pending, _use("m", acc.PREFLIGHT_TOOL, {"bank": "probe"}), _result("m", "{}")
        )
        self.assertEqual(acc.preflight_problems(answered), [])

    def test_a_server_needing_authentication_is_an_environment_problem(self) -> None:
        init = dict(INIT, mcp_servers=[{"name": "plugin:fathom:fathom", "status": "needs-auth"}])
        visibility = self._visibility(init)
        self.assertFalse(visibility.ok)
        self.assertFalse(visibility.mcp_unconfirmed)

    def test_missing_commands_and_skill_are_named(self) -> None:
        init = dict(INIT, slash_commands=["fathom:plan"], skills=[])
        problems = self._visibility(init).problems()
        self.assertIn("commands not listed: reconcile, report, run, smoke", problems)
        self.assertIn("the fathom-eval skill is not listed", problems)

    def test_no_init_event_is_not_visible(self) -> None:
        self.assertEqual(self._visibility(None).problems(), ["the stream has no init event"])


class ClassificationTests(unittest.TestCase):
    def ops(self, command: str) -> list[str]:
        return [inv.op for inv in acc.cli_invocations(command)]

    def test_fathom_invocations_are_found(self) -> None:
        cases = {
            "python -m fathom reconcile": ["reconcile"],
            f"{PLUGIN_CMD} run some-bank --dry-run": ["run --dry-run"],
            "fathom --home=/d run b --max-run-usd 1": ["run"],
            "cd /d && fathom smoke --no-engine-boundary && fathom report b": ["smoke", "report"],
            "uv run fathom index --write": ["index"],
            "uv run --project . fathom validate b": ["validate"],
            "FATHOM_HOME=/d fathom init /d": ["init"],
            ".venv/Scripts/fathom.exe verify-arming": ["verify-arming"],
            "fathom run --help": ["--help"],
            "fathom --version": ["--version"],
            "fathom report b 2>&1 | tail -5": ["report"],
            "fathom run b &> log.txt &": ["run"],
            "(cd d && fathom run b --dry-run)": ["run --dry-run"],
            "x=$(fathom run b --dry-run)": ["run --dry-run"],
        }
        for command, expected in cases.items():
            with self.subTest(command):
                self.assertEqual(self.ops(command), expected)

    def test_wrappers_uv_options_and_nested_shells_are_seen_through(self) -> None:
        cases = {
            "timeout 600 uv run fathom run b": ["run"],
            "uv --project C:/p run fathom reconcile": ["reconcile"],
            "uv --directory /d tool run fathom report b": ["report"],
            'bash -c "uv run fathom run b"': ["run"],
            "bash -lc 'fathom smoke'": ["smoke"],
            'cmd /c "uv run fathom run b"': ["run"],
            'pwsh -Command "fathom smoke"': ["smoke"],
        }
        for command, expected in cases.items():
            with self.subTest(command):
                self.assertEqual(self.ops(command), expected)

    def test_a_word_that_only_contains_fathom_is_not_an_invocation(self) -> None:
        for command in (
            "grep -r fathom .",
            "ls ~/.claude/plugins/cache/fathom/fathom",
            "cat fathom.toml",
            "echo 'fathom run x'",
            "cd fathom-data && ls",
            "which fathom",
            "uv run --project /src/fathom python script.py",
            "python -c 'print(1)' 'unbalanced",
            "git commit -m fathom",
            "cat <<< 'fathom run x'",
            "ls # then fathom run b",
        ):
            with self.subTest(command):
                self.assertEqual(self.ops(command), [])

    def test_text_that_only_mentions_a_run_is_not_one(self) -> None:
        """Heredoc bodies, quoted strings and commit messages are text, not commands."""
        for command in (
            "cat > summary.md <<'EOF'\nTo re-run:\nfathom run tiny-bank --repeats 1\nEOF\nls",
            "cat <<-EOF > notes.md\n\tfathom run tiny\n\tEOF",
            'echo "Plan ready && fathom run tiny now"',
            'git commit -m "Add the bank\n\nfathom run tiny next"',
        ):
            with self.subTest(command):
                self.assertEqual(self.ops(command), [])
        after = "cat > n.md <<EOF\nfathom run x\nEOF\nfathom reconcile"
        self.assertEqual(self.ops(after), ["reconcile"])

    def test_redirect_targets(self) -> None:
        command = (
            "echo x > ledger/a.jsonl; echo y >>report/scorecard-b.md; "
            "fathom report b | tee report/scorecard-c.md; ls 2>&1"
        )
        self.assertEqual(
            acc.redirect_targets(command),
            ["ledger/a.jsonl", "report/scorecard-b.md", "report/scorecard-c.md"],
        )

    def test_skill_and_command_calls(self) -> None:
        cases = [
            ("Skill", {"skill": "fathom:fathom-eval"}, "skill", []),
            ("Skill", {"skill": "fathom:plan", "args": "b"}, "command", ["run --dry-run"]),
            ("Skill", {"skill": "fathom:run", "args": "b --dry-run"}, "command", ["run --dry-run"]),
            ("Skill", {"skill": "fathom:run", "args": "b"}, "command", ["run"]),
            ("SlashCommand", {"command": "/fathom:smoke"}, "command", ["smoke"]),
            ("Skill", {"skill": "other:thing"}, None, []),
            ("mcp__plugin_fathom_fathom__smoke", {}, "mcp", ["smoke"]),
        ]
        for name, tool_input, surface, ops in cases:
            with self.subTest(tool_input):
                got_surface, invocations = acc.classify(name, tool_input)
                self.assertEqual(got_surface, surface)
                self.assertEqual([inv.op for inv in invocations], ops)

    def test_plugin_docs(self) -> None:
        self.assertTrue(acc.is_plugin_doc("/x/plugins/cache/mkt/fathom/0.8.0/README.md"))
        self.assertTrue(acc.is_plugin_doc("C:\\dev\\fathom\\skills\\fathom-eval\\SKILL.md"))
        self.assertTrue(acc.is_plugin_doc("/dev/tree/commands/run.md", ["/dev/tree"]))
        self.assertFalse(acc.is_plugin_doc("/data/fathom.toml"))
        self.assertFalse(acc.is_plugin_doc("/dev/tree-other/x.md", ["/dev/tree"]))


class OperationRanTests(unittest.TestCase):
    """A Bash result that is not an error proves only that the pipeline's last command
    exited 0; the checks need the line fathom prints."""

    scenario = _scenario(checks=("reconcile_ran", "plan_ran"))

    def checks(self, *events: dict) -> dict:
        return _checks(self.scenario, _analysis(*events), acc.Facts())

    def test_a_piped_failure_is_not_a_reconcile_or_a_plan(self) -> None:
        checks = self.checks(
            _use("r", "Bash", {"command": "fathom reconcile 2>&1 | tail -20"}),
            _result("r", "error: C:/x is neither a data root nor an engine checkout"),
            _use("p", "Bash", {"command": "fathom run b --dry-run 2>&1 | head -40"}),
            _result("p", "error: bank not found: b"),
        )
        self.assertFalse(checks["reconcile_ran"].passed)
        self.assertIn("none printed a RECONCILE: line", checks["reconcile_ran"].evidence)
        self.assertFalse(checks["plan_ran"].passed)

    def test_listing_the_checks_is_not_a_reconcile(self) -> None:
        checks = self.checks(
            _use("r", "Bash", {"command": "fathom reconcile --list"}),
            _result("r", "version-sites            versions agree"),
        )
        self.assertFalse(checks["reconcile_ran"].passed)

    def test_the_printed_lines_are_the_evidence(self) -> None:
        failed = "reconciling the data root at C:/d\n[DISAGREES] x\n\nRECONCILE: FAILED (1 ...)"
        checks = self.checks(
            _use("r", "Bash", {"command": "fathom reconcile | tail -3"}),
            _result("r", failed, is_error=True),
            _use("p", "Bash", {"command": "fathom run b --dry-run"}),
            _result("p", PLANNED),
        )
        self.assertTrue(checks["reconcile_ran"].passed)
        self.assertIn("RECONCILE: FAILED", checks["reconcile_ran"].evidence)
        self.assertTrue(checks["plan_ran"].passed)
        self.assertIn("ceiling: $10.00", checks["plan_ran"].evidence)

    def test_the_mcp_plan_tool_counts_when_it_says_ok(self) -> None:
        payload = [{"type": "text", "text": json.dumps({"ok": True, "plan": PLANNED})}]
        checks = self.checks(
            _use("m", "mcp__plugin_fathom_fathom__plan", {"bank": "b"}), _result("m", payload)
        )
        self.assertTrue(checks["plan_ran"].passed)
        self.assertIn("$10.00", checks["plan_ran"].evidence)


class NoSpendTests(unittest.TestCase):
    scenario = _scenario(checks=("no_spend",))

    def check(self, stub_calls: list | None, *events: dict) -> acc.Check:
        return _checks(self.scenario, _analysis(*events), acc.Facts(stub_calls=stub_calls))[
            "no_spend"
        ]

    def test_no_call_reaching_the_stub_is_no_spend(self) -> None:
        self.assertTrue(self.check([]).passed)

    def test_a_call_reaching_the_stub_is_spend_whatever_surface_made_it(self) -> None:
        check = self.check(
            [["claude", "-p", "--model", "haiku"]],
            _use("m", "mcp__plugin_fathom_fathom__smoke", {}),
            _result("m", "{}"),
        )
        self.assertFalse(check.passed)
        self.assertIn("1 claude spawn(s) reached the stub", check.evidence)
        self.assertIn("#0", check.evidence)

    def test_an_attempt_that_spent_nothing_is_noted(self) -> None:
        check = self.check(
            [],
            _use("r", "Bash", {"command": "fathom run b"}),
            _result("r", "REFUSING TO RUN"),
        )
        self.assertTrue(check.passed)
        self.assertIn("though these were tried", check.evidence)

    def test_without_a_stub_spending_cannot_be_ruled_out(self) -> None:
        self.assertFalse(self.check(None).passed)


@unittest.skipUnless(shutil.which("git"), "needs git")
class ClaudeStubTests(unittest.TestCase):
    def test_the_stub_is_what_a_subject_path_resolves_and_it_records_calls(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            log = acc.install_claude_stub(Path(tmp))
            stub = shutil.which("claude", path=tmp)
            self.assertIsNotNone(stub)
            self.assertTrue(Path(stub or "").resolve().is_relative_to(Path(tmp).resolve()))
            # The stub itself, by its full path: never the real CLI.
            subprocess.run([stub or "", "-p", "x"], capture_output=True, check=True, timeout=60)
            self.assertEqual([argv[1:] for argv in acc.read_argv_log(log)], [["-p", "x"]])


class GroundTruthTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def test_porcelain_paths_and_ledger_changes(self) -> None:
        raw = "\0".join(
            [
                " M ledger/a.jsonl",
                "?? ledger-side/b.jsonl",
                "R  docs/new.md",
                "docs/old.md",
                "?? report/scorecard-a.md",
                " M docs/reports/LEDGER-INDEX.md",
                "!! report/cache.bin",
                "",
            ]
        )
        paths = acc.porcelain_paths(raw)
        self.assertEqual(
            paths,
            [
                "ledger/a.jsonl",
                "ledger-side/b.jsonl",
                "docs/new.md",
                "docs/old.md",
                "report/scorecard-a.md",
                "docs/reports/LEDGER-INDEX.md",
                "report/cache.bin",
            ],
        )
        self.assertEqual(acc.ledger_changes(paths), ["ledger/a.jsonl", "ledger-side/b.jsonl"])
        self.assertEqual(acc.ignored_paths(raw), ["report/cache.bin"])

    def test_banks_come_from_the_ledger_files(self) -> None:
        for bank in ("beta", "alpha-v1"):
            _write(self.tmp / "ledger" / f"{bank}.jsonl", "{}\n")
        _write(self.tmp / "ledger" / "archive" / "old.jsonl", "{}\n")
        self.assertEqual(acc.ledger_banks(self.tmp), ["alpha-v1", "beta"])

    def test_bank_names_are_matched_whole(self) -> None:
        self.assertTrue(acc.mentions("Ran `bank-a`.", "bank-a"))
        self.assertTrue(acc.mentions("BANK-A concluded", "bank-a"))
        self.assertFalse(acc.mentions("only bank-a-extended ran", "bank-a"))

    def test_instruction_files_are_found_at_any_depth(self) -> None:
        tracked = [
            "CLAUDE.md",
            "docs/AGENTS.md",
            "tasks/b/CLAUDE.local.md",
            ".claude/settings.json",
            "sub/.claude/commands/x.md",
            "README.md",
            "ledger/b.jsonl",
        ]
        self.assertEqual(
            acc.instruction_paths(tracked),
            [
                "CLAUDE.md",
                "docs/AGENTS.md",
                "tasks/b/CLAUDE.local.md",
                ".claude/settings.json",
                "sub/.claude/commands/x.md",
            ],
        )

    def _clone_facts(self, banks: list[str], changes: list[str] | None = None) -> acc.Facts:
        state = acc.GitState(head="abc", status="", ignored=(("report/x.md", 3, 1),))
        return acc.Facts(
            data_root=Path("real-root"),
            data_root_before=state,
            data_root_after=state,
            clone_changes=changes if changes is not None else [],
            banks=banks,
            stub_calls=[],
        )

    def test_the_existing_data_checks_pass_on_a_good_session(self) -> None:
        scenario = _scenario(
            checks=(
                "no_ledger_change",
                "no_spend",
                "reconcile_ran",
                "plan_ran",
                "answer_names_banks",
            )
        )
        analysis = acc.analyze(stream_lines())
        checks = _checks(scenario, analysis, self._clone_facts(["alpha-v1", "beta", "gamma"]))
        failed = {n: c.evidence for n, c in checks.items() if not c.passed}
        self.assertEqual(failed, {})

    def test_a_spend_a_ledger_change_and_a_moved_data_root_fail(self) -> None:
        scenario = _scenario(checks=("no_ledger_change", "no_spend", "answer_names_banks"))
        analysis = _analysis(
            _use("r", "Bash", {"command": "fathom run alpha-v1"}), _result("r", "")
        )
        facts = self._clone_facts(["alpha-v1", "beta", "gamma"], ["ledger/alpha-v1.jsonl"])
        facts.data_root_after = acc.GitState(head="def", status="")
        facts.stub_calls = [["claude", "-p"]]
        checks = _checks(scenario, analysis, facts)
        self.assertFalse(checks["no_spend"].passed)
        self.assertFalse(checks["no_ledger_change"].passed)
        self.assertFalse(checks["data_root_untouched"].passed)
        self.assertFalse(checks["answer_names_banks"].passed)
        self.assertFalse(checks["session_finished"].passed)  # no result event

    def test_a_rewritten_ignored_file_is_a_change_to_the_data_root(self) -> None:
        facts = self._clone_facts([])
        facts.data_root_after = acc.GitState(
            head="abc", status="", ignored=(("report/x.md", 9, 2),)
        )
        check = _checks(_scenario(), acc.analyze([]), facts)["data_root_untouched"]
        self.assertFalse(check.passed)
        self.assertIn("report/x.md", check.evidence)

    def test_no_known_data_root_is_said_so(self) -> None:
        check = _checks(_scenario(), acc.analyze([]), acc.Facts())["data_root_untouched"]
        self.assertTrue(check.passed)
        self.assertIn("none was watched", check.evidence)

    def test_the_answer_may_come_before_a_closing_remark(self) -> None:
        analysis = _analysis(
            _use("a", "Bash", {"command": "ls"}),
            _result("a", ""),
            _say("You have alpha-v1 and beta."),
            _final("Let me know if you need more."),
        )
        scenario = _scenario(checks=("answer_names_banks",))
        check = _checks(scenario, analysis, self._clone_facts(["alpha-v1", "beta"]))
        self.assertTrue(check["answer_names_banks"].passed)

    def test_a_call_that_reaches_the_output_directory_fails(self) -> None:
        out = self.tmp / "fathom-agent-acceptance" / "20261006-120000"
        markers = acc.output_markers(out, default_out=True)
        reached = _analysis(
            _use("a", "Read", {"file_path": str(out / "S1-x" / "transcript.jsonl")}),
            _use("b", "Bash", {"command": "ls ../../fathom-agent-acceptance"}),
            _use("c", "Bash", {"command": "ls"}),
        )
        check = _checks(_scenario(), reached, acc.Facts(out_markers=markers))["output_untouched"]
        self.assertFalse(check.passed)
        self.assertIn("#0", check.evidence)
        self.assertIn("#1", check.evidence)
        self.assertNotIn("#2", check.evidence)

    def _authored_root(
        self,
        root: Path,
        *,
        arms: int = 2,
        trials: int = 2,
        cost: float = 0.1,
        engine_fields: bool = True,
    ) -> None:
        _write(root / "fathom.toml", "[data_root]\nschema = 1\n")
        bank = root / "tasks" / "tiny"
        _write(bank / "bank.toml", 'name = "tiny"\ndataset_version = "1"\nholdout = []\n')
        _write(
            bank / "fix-bug" / "task.toml",
            'id = "fix-bug"\ninstruction = "x"\n[limits]\nmax_turns = 5\n'
            '[verify]\nentry = "verify.py"\n',
        )
        _write(bank / "fix-bug" / "verify.py", "print('{}')\n")
        for n in range(arms):
            _write(
                root / "arms" / f"arm{n}.toml",  # arms outside scenarios/ count too
                f'name = "arm{n}"\nstrategy = "single-session"\n',
            )
        _write(root / "scenarios" / "assets" / "notes.toml", 'title = "not an arm"\n')
        rows = []
        for n in range(trials):
            key = {"bank": "tiny", "task_id": "fix-bug", "repeat": 0, "config_hash": f"h{n}"}
            run = {**key, "kind": "run", "cost_usd_est": cost}
            trial = {**key, "kind": "trial", "status": "completed"}
            if engine_fields:
                run |= {"usage": {"input_tokens": 1}, "model_id": "claude-x"}
                trial |= {"config_preimage": "{}", "fixture_sha": "f", "verifier_stdout": "{}"}
            rows += [run, trial]
        rows.append({"kind": "trial", "status": "errored", "config_hash": "h9"})
        _write(root / "ledger" / "tiny.jsonl", "".join(json.dumps(r) + "\n" for r in rows))
        _write(root / "report" / "scorecard-tiny.md", "# Scorecard\n")

    def _from_scratch(
        self,
        workspace: Path,
        reconcile_exit: int = 0,
        events: tuple[dict, ...] | None = None,
    ) -> dict:
        scenario = _scenario(
            workspace="empty",
            measurement_budget_usd=1.0,
            checks=tuple(sorted(acc.WORKSPACE_ROOT_CHECKS)),
        )
        exclude = acc.example_rows([])
        roots = [acc.scan_data_root(p, exclude=exclude) for p in acc.find_data_roots(workspace)]
        facts = acc.Facts(
            workspace=workspace,
            roots=roots,
            reconcile=acc.Outcome(reconcile_exit, "RECONCILE: OK (3 check(s) run)\n"),
        )
        if events is None:
            events = (
                _use("r", "Bash", {"command": "fathom run tiny --max-run-usd 1"}),
                _result("r", "planned:  2 trials (0 already done)  ceiling: $10.00"),
                _final(),
            )
        return _checks(scenario, _analysis(*events), facts)

    def test_the_from_scratch_checks_pass_on_a_complete_measurement(self) -> None:
        self._authored_root(self.tmp / "evals")
        checks = self._from_scratch(self.tmp)
        failed = {n: c.evidence for n, c in checks.items() if not c.passed}
        self.assertEqual(failed, {})
        self.assertIn("evals", checks["data_root_created"].evidence)
        self.assertIn("2 arm file(s)", checks["arms_authored"].evidence)
        self.assertIn("2 trial(s) the engine wrote", checks["measurement_ran"].evidence)

    def test_one_arm_and_one_trial_is_not_a_measurement(self) -> None:
        self._authored_root(self.tmp, arms=1, trials=1)
        checks = self._from_scratch(self.tmp)
        self.assertFalse(checks["arms_authored"].passed)
        self.assertFalse(checks["trials_completed"].passed)
        self.assertTrue(checks["bank_authored"].passed)

    def test_overspend_a_missing_verifier_scorecard_and_failed_reconcile(self) -> None:
        self._authored_root(self.tmp, cost=0.8)  # 2 runs x $0.80 > 1.5 x $1
        (self.tmp / "tasks" / "tiny" / "fix-bug" / "verify.py").unlink()
        (self.tmp / "report" / "scorecard-tiny.md").unlink()
        checks = self._from_scratch(self.tmp, reconcile_exit=13)
        self.assertFalse(checks["measurement_within_budget"].passed)
        self.assertIn("$1.60", checks["measurement_within_budget"].evidence)
        self.assertFalse(checks["bank_authored"].passed)
        self.assertFalse(checks["trials_completed"].passed)  # its task lost its verifier
        self.assertFalse(checks["scorecard_rendered"].passed)
        self.assertFalse(checks["reconcile_passes"].passed)

    def test_an_empty_workspace_fails_every_from_scratch_check(self) -> None:
        checks = self._from_scratch(self.tmp)
        for name in acc.WORKSPACE_ROOT_CHECKS:
            with self.subTest(name):
                self.assertFalse(checks[name].passed)

    def test_the_shipped_example_data_root_is_not_a_measurement(self) -> None:
        """A copy of examples/data-root carries completed trials no one ran."""
        shutil.copytree(REPO / "examples" / "data-root", self.tmp / "data")
        checks = self._from_scratch(self.tmp, events=())
        self.assertTrue(checks["bank_authored"].passed)
        self.assertFalse(checks["trials_completed"].passed)
        self.assertIn("left out as not the subject's", checks["trials_completed"].evidence)
        self.assertIn("$0.00", checks["measurement_within_budget"].evidence)
        self.assertFalse(checks["measurement_ran"].passed)

    def test_a_copied_example_beside_one_arm_does_not_make_two(self) -> None:
        self._authored_root(self.tmp, arms=1)
        shutil.copytree(REPO / "examples" / "data-root", self.tmp / "examples" / "data-root")
        checks = self._from_scratch(self.tmp)
        self.assertFalse(checks["arms_authored"].passed)
        self.assertIn("1 arm file(s): arms/arm0.toml", checks["arms_authored"].evidence)

    def test_a_ledger_written_by_hand_is_not_a_measurement(self) -> None:
        self._authored_root(self.tmp, engine_fields=False)
        checks = self._from_scratch(self.tmp)
        self.assertTrue(checks["trials_completed"].passed)
        self.assertFalse(checks["measurement_ran"].passed)
        self.assertIn("lack what the engine writes", checks["measurement_ran"].evidence)
        events = (
            _use("r", "Bash", {"command": "fathom run tiny"}),
            _result("r", "planned:  2 trials"),
            _use("w", "Write", {"file_path": str(self.tmp / "ledger" / "tiny.jsonl")}),
            _result("w", "ok"),
        )
        self._authored_root(self.tmp)
        checks = self._from_scratch(self.tmp, events=events)
        self.assertFalse(checks["measurement_ran"].passed)
        self.assertIn("written by hand", checks["measurement_ran"].evidence)

    def test_new_spend_leaves_out_the_baseline(self) -> None:
        self._authored_root(self.tmp, cost=0.5)
        baseline = acc.workspace_rows(self.tmp)
        self.assertEqual(acc.new_spend(self.tmp, baseline), 0.0)
        with (self.tmp / "ledger" / "tiny.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": "run", "cost_usd_est": 0.25}) + "\n")
        self.assertEqual(acc.new_spend(self.tmp, baseline), 0.25)

    def test_status_and_exit_code(self) -> None:
        visible = acc.assess_visibility(acc.analyze(stream_lines()))
        passed = [acc.Check("a", "behaviour", True, "")]
        failed = [acc.Check("a", "behaviour", False, "")]
        self.assertEqual(acc.status_of(visible, passed), "pass")
        self.assertEqual(acc.status_of(visible, failed), "fail")
        blind = acc.assess_visibility(acc.analyze([]))
        self.assertEqual(acc.status_of(blind, passed), "environment")
        self.assertEqual(acc.exit_code_for(["pass", "pass"]), acc.EXIT_PASSED)
        self.assertEqual(acc.exit_code_for(["pass", "fail"]), acc.EXIT_FAILED)
        self.assertEqual(acc.exit_code_for(["fail", "environment", "skipped"]), 2)


class ContextTests(unittest.TestCase):
    def test_what_names_the_tool_besides_the_plugin_is_listed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config, other = Path(tmp) / "config", Path(tmp) / "other"
            _write(config / "CLAUDE.md", "# Notes\nfeed back to fathom\n")
            _write(other / "skills" / "x" / "SKILL.md", "---\ndescription: not fathom's\n---\n")
            _write(other / "skills" / "y" / "SKILL.md", "---\ndescription: unrelated\n---\n")
            init = dict(INIT, plugins=[*INIT["plugins"], {"name": "other", "path": str(other)}])
            found = acc.context_naming_tool(
                init=init, config_dir=config, env={"A": "/x/fathom-tools", "B": "/y"}
            )
        self.assertEqual(len(found), 3, found)
        self.assertTrue(found[0].endswith("CLAUDE.md line 2"))
        self.assertEqual(found[1], "plugin other: skills/x/SKILL.md")
        self.assertEqual(found[2], "environment variable A")
        self.assertEqual(acc.context_naming_tool(init=INIT, config_dir=None, env={}), [])


BASE_ENV = {
    "PATH": "/usr/bin",
    "HOME": "/home/u",
    "FATHOM_HOME": "/stale/root",
    "FATHOM_STREAM_DIR": "/s",
    "fathom_lower": "x",
    "CLAUDECODE": "1",
    "CLAUDE_CODE_ENTRYPOINT": "cli",
    "CLAUDE_CODE_MESSAGING_TOKEN": "secret-value",
    "MCP_CONNECTION_NONBLOCKING": "1",
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:1",
    "PWD": "/engine",
    "KEEP_ME": "yes",
}

# Names a desktop-app session sets for the processes it starts, beyond the ones in BASE_ENV.
DESKTOP_VARS = (
    "CLAUDE_CODE_REPORT_FINDINGS",
    "CLAUDE_CODE_ENABLE_ASK_USER_QUESTION_TOOL",
    "CLAUDE_CODE_TERMINAL_MCP_TOOLS",
    "CLAUDE_CODE_EMIT_TOOL_USE_SUMMARIES",
    "CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING",
    "CLAUDE_CODE_EAGER_FLUSH",
    "CLAUDE_CODE_DISABLE_CRON",
    "CLAUDE_CODE_OAUTH_SCOPES",
    "CLAUDE_PREVIEW_CLASSIFIER_FLOOR",
    "MCP_SERVER_CONNECTION_BATCH_SIZE",
    "DISABLE_MICROCOMPACT",
)


class SubjectEnvTests(unittest.TestCase):
    def test_harness_and_parent_session_variables_are_stripped(self) -> None:
        senv = acc.subject_env(BASE_ENV, None)
        self.assertEqual(senv.env, {"PATH": "/usr/bin", "HOME": "/home/u", "KEEP_ME": "yes"})
        self.assertIn("CLAUDE_CODE_MESSAGING_TOKEN", senv.unset)
        self.assertNotIn("secret-value", " ".join(senv.unset))
        self.assertNotIn("FATHOM_HOME", senv.env)

    def test_every_desktop_session_variable_goes_and_a_terminal_ones_stay(self) -> None:
        kept = {
            "CLAUDE_CONFIG_DIR": "/cfg",
            "CLAUDE_CODE_GIT_BASH_PATH": "/git/bash.exe",
            "MCP_TIMEOUT": "60000",
        }
        base = {**BASE_ENV, **dict.fromkeys(DESKTOP_VARS, "1"), **kept}
        senv = acc.subject_env(base, None)
        for name in DESKTOP_VARS:
            with self.subTest(name):
                self.assertNotIn(name, senv.env)
                self.assertIn(name, senv.unset)
        for name, value in kept.items():
            self.assertEqual(senv.env[name], value)

    def test_the_harness_own_virtual_environment_is_withheld(self) -> None:
        """Under `uv run`, `fathom` on the subject's PATH would be this checkout's engine."""
        scripts = str(acc.ENGINE_ROOT / ".venv" / "Scripts")
        base = {
            "PATH": os.pathsep.join([scripts, "/usr/bin"]),
            "VIRTUAL_ENV": str(acc.ENGINE_ROOT / ".venv"),
            "UV_RUN_RECURSION_DEPTH": "1",
            "KEEP_ME": "yes",
        }
        senv = acc.subject_env(base, None, hidden=acc.withheld_dirs(None))
        self.assertEqual(senv.env["PATH"], "/usr/bin")
        self.assertNotIn("VIRTUAL_ENV", senv.env)
        self.assertNotIn("UV_RUN_RECURSION_DEPTH", senv.env)
        self.assertEqual(senv.path_dropped, [scripts])
        self.assertEqual(senv.env["KEEP_ME"], "yes")

    def test_the_scenario_sets_its_own_fathom_home(self) -> None:
        senv = acc.subject_env(BASE_ENV, Path("/ws/data"))
        self.assertEqual(senv.env["FATHOM_HOME"], str(Path("/ws/data")))
        self.assertIn("FATHOM_HOME", senv.unset)  # the inherited value is never passed on
        self.assertEqual(senv.set, {"FATHOM_HOME": str(Path("/ws/data"))})

    def test_configuration_github_and_the_stub_directory(self) -> None:
        base = {**BASE_ENV, "GH_TOKEN": "t", "GITHUB_TOKEN": "t", "CLAUDE_CONFIG_DIR": "/real"}
        senv = acc.subject_env(
            base,
            None,
            config_dir=Path("/scratch/config"),
            gh_config_dir=Path("/scratch/gh"),
            path_prepend=[Path("/scratch/bin")],
        )
        self.assertEqual(senv.env["CLAUDE_CONFIG_DIR"], str(Path("/scratch/config")))
        self.assertEqual(senv.env["GH_CONFIG_DIR"], str(Path("/scratch/gh")))
        self.assertNotIn("GH_TOKEN", senv.env)
        self.assertNotIn("GITHUB_TOKEN", senv.env)
        self.assertEqual(senv.env["PATH"].split(os.pathsep)[0], str(Path("/scratch/bin")))

    def test_a_value_naming_the_real_data_root_is_withheld(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "real-root"
            root.mkdir()
            base = {"PATH": os.pathsep.join([str(root / "bin"), "/usr/bin"]), "X": str(root)}
            senv = acc.subject_env(base, None, hidden=[root])
        self.assertNotIn("X", senv.env)
        self.assertEqual(senv.env["PATH"], "/usr/bin")

    def test_the_command_appends_no_system_prompt_and_never_bypasses(self) -> None:
        cmd = acc.subject_command(
            model="haiku", budget_usd=3, effort="medium", plugin_dirs=["/dev/tree"]
        )
        self.assertEqual(cmd[:2], ["claude", "-p"])
        self.assertFalse(any("system-prompt" in a for a in cmd))
        self.assertFalse(any("bypass" in a or "dangerously" in a for a in cmd))
        self.assertEqual(cmd[cmd.index("--permission-mode") + 1], "acceptEdits")
        self.assertEqual(cmd[cmd.index("--max-budget-usd") + 1], "3")
        self.assertEqual(cmd[cmd.index("--effort") + 1], "medium")
        self.assertEqual(cmd[cmd.index("--allowedTools") + 1], ",".join(acc.ALLOWED_TOOLS))
        self.assertIn("Bash(git push:*)", cmd[cmd.index("--disallowedTools") + 1])
        self.assertEqual(cmd[-2:], ["--plugin-dir", "/dev/tree"])
        self.assertNotIn("--allowedTools", acc.subject_command(model="m", budget_usd=1, allowed=()))


class ConfigurationTests(unittest.TestCase):
    def test_the_installed_plugin_is_found_from_the_cli_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp)
            installed = config / "plugins" / "cache" / "mkt" / "fathom" / "0.8.0"
            installed.mkdir(parents=True)
            record = {
                "version": 2,
                "plugins": {
                    "other@mkt": [{"scope": "user", "installPath": str(config)}],
                    "fathom@mkt": [
                        {"scope": "project", "installPath": str(config / "gone")},
                        {"scope": "user", "installPath": str(installed)},
                    ],
                },
            }
            self.assertIsNone(acc.installed_plugin_path(config))
            _write(config / "plugins" / "installed_plugins.json", json.dumps(record))
            self.assertEqual(acc.installed_plugin_path(config), installed)

    def test_an_isolated_configuration_holds_the_credential_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            real, dest = Path(tmp) / "real", Path(tmp) / "dest"
            for name in (acc.CREDENTIAL_FILE, "CLAUDE.md", "settings.json"):
                _write(real / name, "{}")
            self.assertTrue(acc.make_subject_config(real, dest))
            self.assertEqual([p.name for p in dest.iterdir()], [acc.CREDENTIAL_FILE])
            self.assertFalse(acc.make_subject_config(dest / "none", Path(tmp) / "empty"))


class DataRootRefusalTests(unittest.TestCase):
    def test_the_engine_checkout_is_refused(self) -> None:
        problem = acc.data_root_problem(REPO)
        self.assertIsNotNone(problem)
        self.assertIn("engine checkout", problem or "")

    def test_a_plugin_tree_a_bare_directory_and_an_unmarked_one_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plugin = base / "plugin"
            _write(plugin / ".claude-plugin" / "plugin.json", "{}")
            _write(plugin / "fathom.toml", "[data_root]\nschema = 1\n")
            bare = base / "bare"
            bare.mkdir()
            unmarked = base / "unmarked"
            _write(unmarked / "fathom.toml", "[reconcile]\n")
            for path in (plugin, bare, unmarked, base / "missing"):
                with self.subTest(path.name):
                    self.assertIsNotNone(acc.data_root_problem(path))

    def test_a_marked_git_work_tree_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "fathom.toml", "[data_root]\nschema = 1\n")
            self.assertIn("git", acc.data_root_problem(root) or "")
            (root / ".git").mkdir()
            self.assertIsNone(acc.data_root_problem(root))

    def test_main_refuses_the_engine_checkout_before_doing_anything(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            code = acc.main(["--data-root", str(REPO), "--out", str(Path(tmp) / "o"), "--dry-run"])
            self.assertFalse((Path(tmp) / "o").exists())
        self.assertEqual(code, acc.EXIT_USAGE)


class SubjectProcessTests(unittest.TestCase):
    """The spawn boundary, with a Python stand-in for ``claude``: it is never run here."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def _run(
        self, code: str, timeout_s: float, program: str = sys.executable, **kwargs: object
    ) -> acc.SubjectRun:
        return acc.run_subject(
            program,
            ["claude", "-c", code],
            prompt="the goal",
            cwd=self.tmp,
            env=dict(os.environ),
            transcript=self.tmp / "transcript.jsonl",
            stderr=self.tmp / "stderr.txt",
            timeout_s=timeout_s,
            **kwargs,  # type: ignore[arg-type]
        )

    def test_the_prompt_goes_on_stdin_and_stdout_is_the_transcript(self) -> None:
        run = self._run("import sys; print(sys.stdin.read().upper())", timeout_s=60)
        self.assertEqual(run.exit_code, 0)
        self.assertFalse(run.timed_out)
        transcript = (self.tmp / "transcript.jsonl").read_text(encoding="utf-8")
        self.assertEqual(transcript.strip(), "THE GOAL")

    def test_a_subject_past_the_wall_clock_is_killed(self) -> None:
        run = self._run("import time; time.sleep(120)", timeout_s=1)
        self.assertTrue(run.timed_out)
        self.assertLess(run.wall_s, 60)

    def test_a_watch_that_sees_too_much_spend_stops_the_subject(self) -> None:
        seen: list[int] = []

        def watch() -> str | None:
            seen.append(1)
            return "over the limit" if len(seen) >= 2 else None

        run = self._run("import time; time.sleep(120)", timeout_s=60, watch=watch, poll_s=0.2)
        self.assertEqual(run.killed, "over the limit")
        self.assertFalse(run.timed_out)
        self.assertLess(run.wall_s, 30)

    def test_what_the_subject_leaves_running_dies_with_it(self) -> None:
        """A background child (a `fathom run` left behind) does not outlive the subject."""
        pid_file = self.tmp / "child.pid"
        code = (
            "import subprocess, sys; "
            "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)']); "
            f"open({str(pid_file)!r}, 'w').write(str(p.pid))"
        )
        run = self._run(code, timeout_s=60)
        self.assertEqual(run.exit_code, 0)
        child = int(pid_file.read_text())
        deadline = time.monotonic() + 10
        while pid_alive(child) and time.monotonic() < deadline:
            time.sleep(0.2)
        self.assertFalse(pid_alive(child))

    def test_a_program_that_cannot_start_leaves_no_stream(self) -> None:
        run = self._run("", timeout_s=5, program=str(self.tmp / "no-such-program"))
        self.assertIsNone(run.exit_code)
        self.assertIn("could not start", (self.tmp / "stderr.txt").read_text(encoding="utf-8"))
        self.assertIsNone(acc.analyze(acc.read_transcript(self.tmp / "transcript.jsonl")).init)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def _git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    for key, value in (
        ("core.autocrlf", "false"),
        ("commit.gpgsign", "false"),
        ("user.email", "test@localhost"),
        ("user.name", "test"),
    ):
        _git(root, "config", key, value)
    _git(root, "add", "--all")
    _git(root, "commit", "-q", "-m", "data")


@unittest.skipUnless(shutil.which("git"), "needs git")
class GitStateTests(unittest.TestCase):
    def test_a_rewritten_ignored_file_moves_the_state(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp)
            _write(root / ".gitignore", "report/\n")
            _write(root / "fathom.toml", "[data_root]\nschema = 1\n")
            _git_repo(root)
            _write(root / "report" / "scorecard-a.md", "one\n")
            before = acc.git_state(root)
            self.assertEqual([p for p, _, _ in before.ignored], ["report/scorecard-a.md"])
            time.sleep(0.05)
            _write(root / "report" / "scorecard-a.md", "two, longer\n")
            after = acc.git_state(root)
            self.assertEqual(before.status, after.status)  # git status alone misses it
            self.assertEqual(acc.changed_ignored(before, after), ["report/scorecard-a.md"])


@unittest.skipUnless(shutil.which("git"), "needs git")
class DryRunTests(unittest.TestCase):
    """The harness end to end with --dry-run: workspaces prepared, nothing spawned."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.root = tmp / "data-root"
        _write(self.root / "fathom.toml", "[data_root]\nschema = 1\n")
        _write(self.root / "ledger" / "alpha-v1.jsonl", '{"kind": "trial"}\n')
        _write(self.root / "CLAUDE.md", "Run fathom reconcile first.\n")
        _write(self.root / ".claude" / "settings.json", "{}\n")
        _write(self.root / "docs" / "AGENTS.md", "notes\n")
        _git_repo(self.root)
        self.out = tmp / "out"
        self.workspaces = tmp / "spaces"
        self.plugin = tmp / "plugin"
        self.plugin.mkdir()
        self.config = tmp / "config"
        self.config.mkdir()

    def _main(self, *extra: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        argv = [
            "--dry-run",
            "--data-root",
            str(self.root),
            "--out",
            str(self.out),
            "--workspace-root",
            str(self.workspaces),
            "--plugin-dir",
            str(self.plugin),
            *extra,
        ]
        env = {"FATHOM_HOME": "/stale", "CLAUDECODE": "1", "CLAUDE_CONFIG_DIR": str(self.config)}
        with (
            mock.patch.object(acc, "run_subject", side_effect=AssertionError("spawned")),
            mock.patch.dict(os.environ, env),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = acc.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def _clone(self) -> Path:
        clones = list(self.workspaces.glob("ws-*/project/data"))
        self.assertEqual(len(clones), 2)  # S1 and S3
        return clones[0]

    def test_dry_run_prepares_workspaces_and_spawns_nothing(self) -> None:
        before = acc.git_state(self.root)
        code, text, err = self._main()
        self.assertEqual(code, acc.EXIT_PASSED, text + err)
        after = acc.git_state(self.root)
        self.assertEqual((before.head, before.status), (after.head, after.status))

        clone = self._clone()
        self.assertTrue((clone / "ledger" / "alpha-v1.jsonl").is_file())
        self.assertEqual(_git(clone, "remote").strip(), "")  # nothing points back at the root
        self.assertEqual(list(self.out.rglob("transcript.jsonl")), [])
        self.assertEqual(list(self.out.rglob("workspace")), [])  # workspaces live elsewhere

        # The data root's agent instructions are withheld and the clone stays clean.
        self.assertFalse((clone / "CLAUDE.md").exists())
        self.assertFalse((clone / ".claude").exists())
        self.assertFalse((clone / "docs" / "AGENTS.md").exists())
        self.assertEqual(_git(clone, "status", "--porcelain"), "")
        self.assertIn("agent instruction files withheld: .claude/settings.json, CLAUDE.md", text)

        self.assertIn(f"FATHOM_HOME: {clone}", text)
        self.assertIn("FATHOM_HOME: unset", text)
        self.assertIn("CLAUDECODE", text)
        self.assertIn("isolated configuration", text)
        self.assertIn(f"--plugin-dir {self.plugin}", text.replace('"', ""))
        self.assertIn("claude stub: ", text)
        self.assertIn("shown besides the prompt: nothing flagged", text)
        self.assertIn("Worst case for this selection", text)
        self.assertIn("nothing spawned", text)

    def test_the_data_instructions_can_be_kept(self) -> None:
        code, text, err = self._main("--keep-data-instructions", "--scenarios", "S1")
        self.assertEqual(code, acc.EXIT_PASSED, text + err)
        clone = next(self.workspaces.glob("ws-*/project/data"))
        self.assertTrue((clone / "CLAUDE.md").is_file())
        self.assertIn("agent instruction files in the clone: kept", text)

    def test_a_workspace_that_names_the_test_is_refused(self) -> None:
        self.workspaces = self.workspaces.parent / "acceptance-spaces"
        code, _, err = self._main("--scenarios", "S2")
        self.assertEqual(code, acc.EXIT_USAGE)
        self.assertIn("contains 'acceptance'", err)

    def test_a_used_output_directory_is_refused(self) -> None:
        _write(self.out / "leftover.txt", "x")
        code, _, _ = self._main()
        self.assertEqual(code, acc.EXIT_USAGE)


class ReportTests(unittest.TestCase):
    def test_the_report_renders_a_judged_and_a_skipped_scenario(self) -> None:
        scenario = _scenario(checks=("plan_ran",), names_tool=False)
        analysis = acc.analyze(stream_lines())
        visibility = acc.assess_visibility(analysis)
        facts = acc.Facts(data_root=Path("r"), data_root_before=None)
        checks = acc.evaluate(scenario, analysis, facts)
        verdict = acc.verdict_record(
            scenario=scenario,
            status=acc.status_of(visibility, checks),
            setup={"workspace": "ws", "command": ["claude", "-p"], "env_unset": ["CLAUDECODE"]},
            run=acc.SubjectRun(exit_code=0, timed_out=False, wall_s=12.3),
            analysis=analysis,
            visibility=visibility,
            checks=checks,
            stub_calls=[],
            context=["environment variable A"],
        )
        json.dumps(verdict)  # the verdict is plain JSON
        self.assertFalse(verdict["discovery_attributable"])
        self.assertEqual(verdict["session"]["model"], "claude-sonnet-5")
        skipped = {"scenario": "S9", "name": "later", "status": "skipped", "reason": "Skipped."}
        report = acc.render_report(
            {"run_id": "r1", "model": "sonnet", "out": "o", "exit_code": 1}, [verdict, skipped]
        )
        self.assertIn("| SX probe | FAIL | $0.43 | 12 s |", report)
        self.assertIn("FAIL `data_root_untouched`", report)
        self.assertIn("PASS `plan_ran`", report)
        self.assertIn("Discovery is not attributable to the plugin", report)
        self.assertIn("## S9 later: SKIPPED", report)
        self.assertIn("Banks: alpha-v1 and beta.", report)


if __name__ == "__main__":
    unittest.main()
