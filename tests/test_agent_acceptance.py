"""The fresh-agent acceptance harness (tools/agent_acceptance.py), offline.

Nothing here spawns ``claude``: the transcript is a synthetic stream in the shape the CLI
emits, the ground truth is read from temporary workspaces, the spawn boundary runs a Python
stand-in, and the end-to-end test runs the harness with ``--dry-run`` against a temporary git
data root, with the spawn function replaced by one that fails the test if it is ever called.

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
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

import agent_acceptance as acc  # noqa: E402

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


def _result(tool_id: str, text: object, *, is_error: bool | None = None) -> dict:
    block: dict = {"type": "tool_result", "tool_use_id": tool_id, "content": text}
    if is_error is not None:
        block["is_error"] = is_error
    return {"type": "user", "message": {"content": [block]}}


PLUGIN_CMD = 'uv run --no-dev --frozen --project "C:/p" python -m fathom --home "C:/d"'

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
    _result("u4", "RECONCILE: OK (3 check(s) run)", is_error=False),
    _use("u5", "mcp__plugin_fathom_fathom__plan", {"bank": "b"}),
    _result("u5", "boom: the data root is missing " + "x" * 400, is_error=True),
    {"type": "rate_limit_event", "rate_limit_info": {}},
    _use("u6", "Bash", {"command": f"{PLUGIN_CMD} run b --dry-run --repeats 1"}),
    _result("u6", "data root: C:/d\n2 trials"),
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


class ScenarioFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenarios = acc.load_scenarios(acc.SCENARIOS_FILE.read_text(encoding="utf-8"))

    def test_the_shipped_scenarios_load(self) -> None:
        self.assertEqual([s.id for s in self.scenarios], ["S1", "S2", "S3"])
        self.assertEqual([s.workspace for s in self.scenarios], ["clone", "empty", "clone"])
        self.assertEqual([s.fathom_home for s in self.scenarios], [True, False, True])
        self.assertEqual(self.scenarios[1].measurement_budget_usd, 1.0)

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

    def test_a_clone_scenario_gets_the_data_root_check_automatically(self) -> None:
        s1, s2 = self.scenarios[0], self.scenarios[1]
        self.assertEqual(acc.checks_for(s1)[:2], ["session_finished", "data_root_untouched"])
        self.assertNotIn("data_root_untouched", acc.checks_for(s2))

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
        events = [INIT, _use("m", "mcp__plugin_fathom_fathom__plan", {}), _result("m", payload)]
        call = acc.analyze(stream_lines(events, malformed=False)).calls[0]
        self.assertFalse(call.is_error)
        self.assertFalse(call.succeeded)

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
        self.assertIsNone(facts["budget_rail_used"])
        self.assertIsNone(facts["smoke_before_run"])

    def test_rails_and_order_before_a_paid_run(self) -> None:
        events = [
            INIT,
            _use("a", "Bash", {"command": "fathom smoke --no-engine-boundary"}),
            _result("a", "SMOKE RESULT: ALL PASS"),
            _use("b", "Bash", {"command": "fathom run b --max-run-usd 1"}),
            _result("b", "done"),
        ]
        facts = acc.behaviour(acc.analyze(stream_lines(events, malformed=False)))
        self.assertEqual(facts["paid_runs"], 1)
        self.assertTrue(facts["budget_rail_used"])
        self.assertTrue(facts["smoke_before_run"])
        self.assertFalse(facts["plan_before_run"])


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
        ):
            with self.subTest(command):
                self.assertEqual(self.ops(command), [])

    def test_skill_and_command_calls(self) -> None:
        cases = [
            ("Skill", {"skill": "fathom:fathom-eval"}, "skill", []),
            ("Skill", {"skill": "fathom:plan", "args": "b"}, "command", ["run --dry-run"]),
            ("Skill", {"skill": "fathom:run", "args": "b --dry-run"}, "command", ["run --dry-run"]),
            ("Skill", {"skill": "fathom:run", "args": "b"}, "command", ["run"]),
            ("SlashCommand", {"command": "/fathom:smoke"}, "command", ["smoke"]),
            ("Skill", {"skill": "other:thing"}, None, []),
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
            ],
        )
        self.assertEqual(acc.ledger_changes(paths), ["ledger/a.jsonl", "ledger-side/b.jsonl"])

    def test_banks_come_from_the_ledger_files(self) -> None:
        for bank in ("beta", "alpha-v1"):
            _write(self.tmp / "ledger" / f"{bank}.jsonl", "{}\n")
        _write(self.tmp / "ledger" / "archive" / "old.jsonl", "{}\n")
        self.assertEqual(acc.ledger_banks(self.tmp), ["alpha-v1", "beta"])

    def test_bank_names_are_matched_whole(self) -> None:
        self.assertTrue(acc.mentions("Ran `bank-a`.", "bank-a"))
        self.assertTrue(acc.mentions("BANK-A concluded", "bank-a"))
        self.assertFalse(acc.mentions("only bank-a-extended ran", "bank-a"))

    def _clone_facts(self, banks: list[str], changes: list[str] | None = None) -> acc.Facts:
        state = acc.GitState(head="abc", status="")
        return acc.Facts(
            data_root_before=state,
            data_root_after=state,
            clone_changes=changes if changes is not None else [],
            banks=banks,
        )

    def _checks(self, scenario: acc.Scenario, analysis: acc.Analysis, facts: acc.Facts) -> dict:
        return {c.name: c for c in acc.evaluate(scenario, analysis, facts)}

    def test_the_existing_data_checks_pass_on_a_good_session(self) -> None:
        scenario = _scenario(
            checks=(
                "no_ledger_change",
                "no_paid_run",
                "reconcile_ran",
                "plan_ran",
                "answer_names_banks",
            )
        )
        analysis = acc.analyze(stream_lines())
        checks = self._checks(scenario, analysis, self._clone_facts(["alpha-v1", "beta", "gamma"]))
        failed = {n: c.evidence for n, c in checks.items() if not c.passed}
        self.assertEqual(failed, {})

    def test_a_paid_run_a_ledger_change_and_a_moved_data_root_fail(self) -> None:
        scenario = _scenario(checks=("no_ledger_change", "no_paid_run", "answer_names_banks"))
        events = [INIT, _use("r", "Bash", {"command": "fathom run alpha-v1"}), _result("r", "ok")]
        facts = self._clone_facts(["alpha-v1", "beta", "gamma"], ["ledger/alpha-v1.jsonl"])
        facts.data_root_after = acc.GitState(head="def", status="")
        checks = self._checks(scenario, acc.analyze(stream_lines(events, malformed=False)), facts)
        self.assertFalse(checks["no_paid_run"].passed)
        self.assertFalse(checks["no_ledger_change"].passed)
        self.assertFalse(checks["data_root_untouched"].passed)
        self.assertFalse(checks["answer_names_banks"].passed)
        self.assertFalse(checks["session_finished"].passed)  # no result event

    def _authored_root(
        self, root: Path, *, arms: int = 2, trials: int = 2, cost: float = 0.1
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
                root / "scenarios" / "tiny" / f"arm{n}.toml",
                f'name = "arm{n}"\nstrategy = "single-session"\n',
            )
        _write(root / "scenarios" / "assets" / "notes.toml", 'title = "not an arm"\n')
        rows = []
        for n in range(trials):
            rows.append({"kind": "run", "config_hash": f"h{n}", "cost_usd_est": cost})
            rows.append({"kind": "trial", "status": "completed", "config_hash": f"h{n}"})
        rows.append({"kind": "trial", "status": "errored", "config_hash": "h9"})
        _write(root / "ledger" / "tiny.jsonl", "".join(json.dumps(r) + "\n" for r in rows))
        _write(root / "report" / "scorecard-tiny.md", "# Scorecard\n")

    def _from_scratch(self, workspace: Path, reconcile_exit: int = 0) -> dict:
        scenario = _scenario(
            workspace="empty",
            measurement_budget_usd=1.0,
            checks=tuple(sorted(acc.WORKSPACE_ROOT_CHECKS)),
        )
        roots = [acc.scan_data_root(p) for p in acc.find_data_roots(workspace)]
        facts = acc.Facts(
            workspace=workspace,
            roots=roots,
            reconcile=acc.Outcome(reconcile_exit, "RECONCILE: OK (3 check(s) run)\n"),
        )
        return self._checks(scenario, acc.analyze(stream_lines()), facts)

    def test_the_from_scratch_checks_pass_on_a_complete_measurement(self) -> None:
        self._authored_root(self.tmp / "evals")
        checks = self._from_scratch(self.tmp)
        failed = {n: c.evidence for n, c in checks.items() if not c.passed}
        self.assertEqual(failed, {})
        self.assertIn("evals", checks["data_root_created"].evidence)
        self.assertIn("2 arm file(s)", checks["arms_authored"].evidence)

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
        self.assertFalse(checks["scorecard_rendered"].passed)
        self.assertFalse(checks["reconcile_passes"].passed)

    def test_an_empty_workspace_fails_every_from_scratch_check(self) -> None:
        checks = self._from_scratch(self.tmp)
        for name in acc.WORKSPACE_ROOT_CHECKS:
            with self.subTest(name):
                self.assertFalse(checks[name].passed)

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


class SubjectEnvTests(unittest.TestCase):
    def test_harness_and_parent_session_variables_are_stripped(self) -> None:
        env, removed = acc.subject_env(BASE_ENV, None)
        self.assertEqual(env, {"PATH": "/usr/bin", "HOME": "/home/u", "KEEP_ME": "yes"})
        self.assertIn("CLAUDE_CODE_MESSAGING_TOKEN", removed)
        self.assertNotIn("secret-value", " ".join(removed))
        self.assertNotIn("FATHOM_HOME", env)

    def test_the_scenario_sets_its_own_fathom_home(self) -> None:
        env, removed = acc.subject_env(BASE_ENV, Path("/ws/data"))
        self.assertEqual(env["FATHOM_HOME"], str(Path("/ws/data")))
        self.assertIn("FATHOM_HOME", removed)  # the inherited value is never passed on

    def test_a_value_naming_the_real_data_root_is_withheld(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "real-root"
            root.mkdir()
            base = {"PATH": os.pathsep.join([str(root / "bin"), "/usr/bin"]), "X": str(root)}
            env, _ = acc.subject_env(base, None, hidden=[root])
        self.assertNotIn("X", env)
        self.assertEqual(env["PATH"], "/usr/bin")

    def test_the_command_appends_no_system_prompt_and_never_bypasses(self) -> None:
        cmd = acc.subject_command(model="haiku", budget_usd=3, plugin_dirs=["/dev/tree"])
        self.assertEqual(cmd[:2], ["claude", "-p"])
        self.assertFalse(any("system-prompt" in a for a in cmd))
        self.assertFalse(any("bypass" in a or "dangerously" in a for a in cmd))
        self.assertEqual(cmd[cmd.index("--permission-mode") + 1], "acceptEdits")
        self.assertEqual(cmd[cmd.index("--max-budget-usd") + 1], "3")
        self.assertEqual(cmd[cmd.index("--allowedTools") + 1], ",".join(acc.ALLOWED_TOOLS))
        self.assertIn("Bash(git push:*)", cmd[cmd.index("--disallowedTools") + 1])
        self.assertEqual(cmd[-2:], ["--plugin-dir", "/dev/tree"])
        self.assertNotIn("--allowedTools", acc.subject_command(model="m", budget_usd=1, allowed=()))


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

    def _run(self, code: str, timeout_s: float, program: str = sys.executable) -> acc.SubjectRun:
        return acc.run_subject(
            program,
            ["claude", "-c", code],
            prompt="the goal",
            cwd=self.tmp,
            env=dict(os.environ),
            transcript=self.tmp / "transcript.jsonl",
            stderr=self.tmp / "stderr.txt",
            timeout_s=timeout_s,
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

    def test_a_program_that_cannot_start_leaves_no_stream(self) -> None:
        run = self._run("", timeout_s=5, program=str(self.tmp / "no-such-program"))
        self.assertIsNone(run.exit_code)
        self.assertIn("could not start", (self.tmp / "stderr.txt").read_text(encoding="utf-8"))
        self.assertIsNone(acc.analyze(acc.read_transcript(self.tmp / "transcript.jsonl")).init)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


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
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        for key, value in (
            ("core.autocrlf", "false"),
            ("commit.gpgsign", "false"),
            ("user.email", "test@localhost"),
            ("user.name", "test"),
        ):
            _git(self.root, "config", key, value)
        _git(self.root, "add", "--all")
        _git(self.root, "commit", "-q", "-m", "data")
        self.out = tmp / "out"

    def test_dry_run_prepares_workspaces_and_spawns_nothing(self) -> None:
        before = (_git(self.root, "rev-parse", "HEAD"), _git(self.root, "status", "--porcelain"))
        stdout = io.StringIO()
        with (
            mock.patch.object(acc, "run_subject", side_effect=AssertionError("spawned")),
            mock.patch.dict(os.environ, {"FATHOM_HOME": "/stale", "CLAUDECODE": "1"}),
            contextlib.redirect_stdout(stdout),
        ):
            code = acc.main(["--dry-run", "--data-root", str(self.root), "--out", str(self.out)])
        self.assertEqual(code, acc.EXIT_PASSED, stdout.getvalue())
        after = (_git(self.root, "rev-parse", "HEAD"), _git(self.root, "status", "--porcelain"))
        self.assertEqual(before, after)

        clone = self.out / "S1-existing-data" / "workspace" / "data"
        self.assertTrue((clone / "ledger" / "alpha-v1.jsonl").is_file())
        self.assertEqual(_git(clone, "remote").strip(), "")  # nothing points back at the root
        self.assertTrue((self.out / "S2-from-scratch" / "workspace").is_dir())
        self.assertEqual(list((self.out / "S2-from-scratch" / "workspace").iterdir()), [])
        self.assertEqual(list(self.out.rglob("transcript.jsonl")), [])

        text = stdout.getvalue()
        self.assertIn(f"FATHOM_HOME: {clone}", text)
        self.assertIn("FATHOM_HOME: unset", text)
        self.assertIn("CLAUDECODE", text)
        self.assertIn("nothing spawned", text)

    def test_a_used_output_directory_is_refused(self) -> None:
        _write(self.out / "leftover.txt", "x")
        with contextlib.redirect_stderr(io.StringIO()):
            code = acc.main(["--dry-run", "--data-root", str(self.root), "--out", str(self.out)])
        self.assertEqual(code, acc.EXIT_USAGE)


class ReportTests(unittest.TestCase):
    def test_the_report_renders_a_judged_and_a_skipped_scenario(self) -> None:
        scenario = _scenario(checks=("plan_ran",))
        analysis = acc.analyze(stream_lines())
        visibility = acc.assess_visibility(analysis)
        checks = acc.evaluate(scenario, analysis, acc.Facts(data_root_before=None))
        verdict = acc.verdict_record(
            scenario=scenario,
            status=acc.status_of(visibility, checks),
            workspace=Path("ws"),
            fathom_home=None,
            command=["claude", "-p"],
            unset=["CLAUDECODE"],
            exit_code=0,
            timed_out=False,
            wall_s=12.3,
            analysis=analysis,
            visibility=visibility,
            checks=checks,
        )
        json.dumps(verdict)  # the verdict is plain JSON
        skipped = {"scenario": "S9", "name": "later", "status": "skipped", "reason": "Skipped."}
        report = acc.render_report(
            {"run_id": "r1", "model": "sonnet", "out": "o", "exit_code": 1}, [verdict, skipped]
        )
        self.assertIn("| SX probe | FAIL | $0.43 | 12 s |", report)
        self.assertIn("FAIL `data_root_untouched`", report)
        self.assertIn("PASS `plan_ran`", report)
        self.assertIn("## S9 later: SKIPPED", report)
        self.assertIn("Banks: alpha-v1 and beta.", report)


if __name__ == "__main__":
    unittest.main()
