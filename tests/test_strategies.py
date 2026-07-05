"""Tests for src/fathom/strategies/{base,single_session,series}.py.

Stdlib-runnable:
    python tests/test_strategies.py
Via pytest:
    uv run pytest tests/test_strategies.py

No real engine runs: the engine subprocess boundary is injected as a stub
everywhere (real-spawn / engine-boundary isolation is the smoke gate's job,
spec §11).  The one place real processes are spawned is the timeout test, which
builds a *stub* process tree (a python parent + grandchild sleeper) purely to
prove the whole-tree kill leaves no orphan — it never runs the engine or claude.
"""

import json
import os
import sys
import tempfile
import time
import tomllib
import types
import unittest
import warnings
from pathlib import Path

# Allow `python tests/test_strategies.py` from the project root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.adapters.base import ExitStatus, RunRecord
from fathom.adapters.claude_cli import cleanup_dir
from fathom.scenario import LimitsOverride, ResolvedScenario, ToolsConfig
from fathom.strategies.base import (
    PIN_SERIES,
    PIN_STRONG,
    StrategyExecutor,
    TrialResult,
    TrialStatus,
)
from fathom.strategies.series import (
    EngineOutcome,
    SeriesExecutor,
    _build_argv,
    _classify,
    _default_run_engine,
    _materialize_runs,
    _read_events,
    _select_run_id,
    dump_toml,
    pid_alive,
)
from fathom.strategies.single_session import SingleSessionExecutor
from fathom.taskbank import Task

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Shared fixtures / factories
# ---------------------------------------------------------------------------

# A committed series-asset template (convoy schema) with every field the executor
# must override: tier (dropped), bypassPermissions (replaced), inflated budgets
# (replaced), and a per-PR model/effort/budget override (stripped for parity).
_TEMPLATE = """\
[series]
id = "demo"
version = "1.0"

[branches]
base = "main"
integration = "demo/integration"

[paths]
prompts = "prompts"
outputs = "outputs"

[governance]
tier = "strong"
effort = "max"
permission_mode = "bypassPermissions"
timeout_seconds = 1800

[governance.budgets]
implementation = 99.0
review = 99.0
fix = 99.0

[governance.tools]
implementation = ["Read", "Write", "Edit", "Bash"]
review = ["Read"]
fix = ["Read", "Write", "Edit"]

[review]
blocking = true
max_fix_attempts = 2

[[checks]]
name = "ruff"
run = "ruff check ."
blocking = true
independent = false

[[prs]]
id = "PR01"
branch = "demo/pr01"
prompt = "pr01.md"
phase = "1"
depends_on = []
model = "claude-haiku-4-5"
effort = "low"
budget = 1.0

[[prs]]
id = "PR02"
branch = "demo/pr02"
prompt = "pr02.md"
phase = "1"
depends_on = ["PR01"]
"""

# One invocation's telemetry (convoy spawns.jsonl): a run_start + two current-run
# spawn_complete events (impl + review), one foreign-run-id spawn_complete (an
# accumulated earlier run, excluded), and a terminal run_complete. Lifecycle
# events are skipped by the materializer; only current-run spawn_complete counts.
_CURRENT_RUN = "20260610T143000Z-aaaa"
_FOREIGN_RUN = "20260609T120000Z-bbbb"
_SERIES_SPAWNS = (
    '{"schema_version": 1, "event": "run_start", "run_id": "%(cur)s", "series_id": "demo"}\n'
    '{"schema_version": 1, "event": "spawn_complete", "run_id": "%(cur)s", "pr_id": "PR01",'
    ' "role": "implementation", "exit_code": 0, "input_tokens": 1000, "output_tokens": 400,'
    ' "num_turns": 5, "duration_s": 12.0, "cost_usd": 0.12, "effective_model": "claude-opus-4-8"}\n'
    '{"schema_version": 1, "event": "spawn_complete", "run_id": "%(cur)s", "pr_id": "PR01",'
    ' "role": "review", "exit_code": 0, "input_tokens": 300, "output_tokens": 200,'
    ' "num_turns": 2, "duration_s": 4.0, "cost_usd": 0.03, "effective_model": "claude-opus-4-8"}\n'
    '{"schema_version": 1, "event": "spawn_complete", "run_id": "%(foreign)s", "pr_id": "PR01",'
    ' "role": "implementation", "exit_code": 0, "input_tokens": 9999, "output_tokens": 8888,'
    ' "num_turns": 9, "duration_s": 99.0, "cost_usd": 9.99, "effective_model": "claude-opus-4-8"}\n'
    '{"schema_version": 1, "event": "run_complete", "run_id": "%(cur)s", "outcome": "completed",'
    ' "integrated": true}\n'
) % {"cur": _CURRENT_RUN, "foreign": _FOREIGN_RUN}


def _scenario(
    *, model="claude-opus-4-8", effort="high", trial_timeout_s=3600, tool_invocation_cmd="convoy"
):
    return ResolvedScenario(
        name="series",
        adapter="claude-cli",
        model=model,
        strategy="series",
        effort=effort,
        tools=ToolsConfig(source="repo", repo="C:/repo"),
        limits=LimitsOverride(trial_timeout_s=trial_timeout_s),
        model_id=None,
        tool_repo_sha="deadbeef",
        tool_invocation_cmd=tool_invocation_cmd,
        config_hash="x" * 64,
    )


def _ok_record(**kw):
    base = dict(
        status=ExitStatus.OK,
        tokens_in=10,
        tokens_out=5,
        num_turns=3,
        duration_s=1.5,
        cost_usd_est=0.01,
        model_id="claude-opus-4-8-exact",
    )
    base.update(kw)
    return RunRecord(**base)


class StubRunner:
    """Records every execute() call; replays one preconfigured RunRecord."""

    def __init__(self, record):
        self.record = record
        self.calls = []

    def execute(self, prompt, workspace, scenario, max_turns=None):
        self.calls.append(
            types.SimpleNamespace(
                prompt=prompt, workspace=workspace, scenario=scenario, max_turns=max_turns
            )
        )
        return self.record


class StubEngine:
    """Injectable engine boundary: behaves like the series engine's ``run``.

    Reads the emitted series.toml from argv (proving it is valid + parseable),
    captures the engine's view of the instantiated assets, writes the supplied
    spawns.jsonl telemetry into the configured outputs dir, and returns a preset
    outcome.
    """

    def __init__(
        self,
        *,
        telemetry_text="",
        returncode=0,
        stdout="",
        stderr="",
        timed_out=False,
        duration_s=1.0,
    ):
        self.telemetry_text = telemetry_text
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out
        self.duration_s = duration_s
        self.calls = []
        # Captured during the call, before the executor cleans the assets dir up.
        self.series_data = None
        self.series_text = ""
        self.outputs_dir = None
        self.prompts_exist = False

    def __call__(self, argv, *, cwd, env, timeout):
        self.calls.append(
            types.SimpleNamespace(argv=list(argv), cwd=cwd, env=dict(env), timeout=timeout)
        )
        series_path = Path(argv[-1])
        self.series_text = series_path.read_text(encoding="utf-8")
        self.series_data = tomllib.loads(self.series_text)
        paths = self.series_data["paths"]
        self.prompts_exist = Path(paths["prompts"]).is_dir()
        self.outputs_dir = Path(paths["outputs"])
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        if self.telemetry_text:
            (self.outputs_dir / "spawns.jsonl").write_text(self.telemetry_text, encoding="utf-8")
        return EngineOutcome(
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
            timed_out=self.timed_out,
            duration_s=self.duration_s,
        )


class SeriesTestBase(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="fathom-ws-"))
        self.addCleanup(cleanup_dir, str(self.workspace))
        self.task_dir = Path(tempfile.mkdtemp(prefix="fathom-task-"))
        self.addCleanup(cleanup_dir, str(self.task_dir))
        (self.task_dir / "series.toml").write_text(_TEMPLATE, encoding="utf-8")
        prompts = self.task_dir / "prompts"
        prompts.mkdir()
        (prompts / "pr01.md").write_text("implement PR01", encoding="utf-8")
        (prompts / "pr02.md").write_text("implement PR02", encoding="utf-8")
        self.task = Task(
            id="t1",
            instruction="do the thing",
            limits={},
            verify={"entry": "verify.py"},
            task_dir=self.task_dir,
        )
        self.config_dir = Path(tempfile.mkdtemp(prefix="fathom-stubcfg-"))
        self.addCleanup(cleanup_dir, str(self.config_dir))

    def make_executor(self, engine, **kw):
        kw.setdefault("make_config", lambda _real: str(self.config_dir))
        kw.setdefault("cleanup", lambda _p: None)  # leave the injected cfg for inspection
        return SeriesExecutor(run_engine=engine, **kw)

    def run_series(self, engine, scenario=None, **kw):
        scenario = scenario or _scenario()
        executor = self.make_executor(engine, **kw)
        return executor.run_trial(self.task, self.workspace, scenario, StubRunner(_ok_record()))


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocol(unittest.TestCase):
    def test_both_executors_satisfy_protocol(self):
        self.assertIsInstance(SingleSessionExecutor(), StrategyExecutor)
        self.assertIsInstance(SeriesExecutor(), StrategyExecutor)


# ---------------------------------------------------------------------------
# Single-session: exactly one Runner call per trial
# ---------------------------------------------------------------------------


class TestSingleSession(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="fathom-ws-"))
        self.addCleanup(cleanup_dir, str(self.workspace))
        self.task = Task(
            id="t1",
            instruction="do it",
            limits={},
            verify={"entry": "verify.py"},
            task_dir=self.workspace,
        )

    def _run(self, record):
        runner = StubRunner(record)
        result = SingleSessionExecutor().run_trial(self.task, self.workspace, _scenario(), runner)
        return runner, result

    def test_exactly_one_run_per_trial(self):
        runner, result = self._run(_ok_record())
        self.assertEqual(len(runner.calls), 1, "single-session must call the Runner exactly once")
        self.assertEqual(len(result.runs), 1)
        self.assertEqual(result.pin_level, PIN_STRONG)
        self.assertEqual(result.status, TrialStatus.COMPLETED)
        self.assertEqual(runner.calls[0].prompt, "do it")

    def test_error_record_maps_to_errored(self):
        _, result = self._run(_ok_record(status=ExitStatus.ERROR, result_text="boom"))
        self.assertEqual(result.status, TrialStatus.ERRORED)
        self.assertTrue(result.scored)

    def test_timeout_record_maps_to_errored(self):
        _, result = self._run(_ok_record(status=ExitStatus.TIMEOUT))
        self.assertEqual(result.status, TrialStatus.ERRORED)

    def test_infrastructure_record_not_scored(self):
        _, result = self._run(_ok_record(status=ExitStatus.INFRASTRUCTURE))
        self.assertEqual(result.status, TrialStatus.INFRASTRUCTURE)
        self.assertTrue(result.is_infrastructure)
        self.assertFalse(result.scored)

    def test_passes_task_max_turns_to_runner(self):
        """The task's turn budget (task.limits.max_turns) must reach the spawn —
        otherwise the adapter's lower default caps and truncates multi-step tasks."""
        task = Task(
            id="t",
            instruction="go",
            limits={"max_turns": 60},
            verify={"entry": "verify.py"},
            task_dir=self.workspace,
        )
        runner = StubRunner(_ok_record())
        SingleSessionExecutor().run_trial(task, self.workspace, _scenario(), runner)
        self.assertEqual(runner.calls[0].max_turns, 60)

    def test_passes_none_when_task_sets_no_max_turns(self):
        runner = StubRunner(_ok_record())  # self.task has limits={}
        SingleSessionExecutor().run_trial(self.task, self.workspace, _scenario(), runner)
        self.assertIsNone(runner.calls[0].max_turns)


# ---------------------------------------------------------------------------
# Series: emitted series.toml
# ---------------------------------------------------------------------------


class TestSeriesEmission(SeriesTestBase):
    def setUp(self):
        super().setUp()
        self.engine = StubEngine(returncode=0)
        self.result = self.run_series(self.engine)
        self.data = self.engine.series_data

    def test_assets_and_outputs_outside_workspace(self):
        ws = self.workspace.resolve()
        for key in ("prompts", "outputs"):
            p = Path(self.data["paths"][key])
            self.assertTrue(p.is_absolute(), f"{key} must be an absolute path")
            self.assertFalse(
                p.resolve().is_relative_to(ws),
                f"{key}={p} must live outside the scored workspace",
            )

    def test_source_assets_were_copied(self):
        # The engine saw a real prompts dir (copied, absolute).
        self.assertTrue(self.engine.prompts_exist)

    def test_permission_mode_is_non_bypass(self):
        self.assertNotEqual(self.data["governance"]["permission_mode"], "bypassPermissions")
        self.assertEqual(self.data["governance"]["permission_mode"], "default")

    def test_model_and_effort_mapped_from_scenario(self):
        self.assertEqual(self.data["governance"]["model"], "claude-opus-4-8")
        self.assertEqual(self.data["governance"]["effort"], "high")
        self.assertNotIn("tier", self.data["governance"], "tier must be dropped so model pin wins")

    def test_budgets_pinned(self):
        budgets = self.data["governance"]["budgets"]
        self.assertEqual(budgets["implementation"], 20.0)
        self.assertEqual(budgets["review"], 5.0)
        self.assertEqual(budgets["fix"], 3.0)

    def test_per_pr_overrides_stripped(self):
        pr01 = next(p for p in self.data["prs"] if p["id"] == "PR01")
        for key in ("model", "tier", "effort", "budget", "budgets"):
            self.assertNotIn(key, pr01, f"per-PR {key} must be stripped for cross-arm parity")

    def test_template_structure_preserved(self):
        # Branches, PR list, and gate checks survive the read→emit round-trip.
        self.assertEqual(self.data["branches"]["base"], "main")
        self.assertEqual(self.data["branches"]["integration"], "demo/integration")
        self.assertEqual([p["id"] for p in self.data["prs"]], ["PR01", "PR02"])
        self.assertEqual(self.data["checks"][0]["name"], "ruff")
        self.assertEqual(self.data["series"]["id"], "demo")


# ---------------------------------------------------------------------------
# Series: isolation env + pinned invocation
# ---------------------------------------------------------------------------


class TestSeriesInvocation(SeriesTestBase):
    def test_isolation_env_and_cwd_and_argv(self):
        engine = StubEngine(returncode=0)
        self.run_series(
            engine, scenario=_scenario(tool_invocation_cmd="uv run --project C:/repo convoy")
        )
        call = engine.calls[0]
        # CLAUDE_CONFIG_DIR is the isolated, credential-only config.
        self.assertEqual(call.env["CLAUDE_CONFIG_DIR"], str(self.config_dir))
        # cwd is the trial workspace.
        self.assertEqual(Path(call.cwd).resolve(), self.workspace.resolve())
        # argv is the pinned invocation command + run + the emitted series.toml.
        self.assertEqual(call.argv[:5], ["uv", "run", "--project", "C:/repo", "convoy"])
        self.assertEqual(call.argv[5], "run")
        self.assertTrue(call.argv[6].endswith("series.toml"))
        self.assertEqual(call.timeout, 3600)

    def test_build_argv_falls_back_to_convoy(self):
        argv = _build_argv(_scenario(tool_invocation_cmd=None), Path("C:/a/series.toml"))
        self.assertEqual(argv[0], "convoy")
        self.assertEqual(argv[1], "run")


# ---------------------------------------------------------------------------
# Series: spawns.jsonl → run records (matching spawn_complete only)
# ---------------------------------------------------------------------------


class TestSeriesTelemetryParsing(SeriesTestBase):
    def setUp(self):
        super().setUp()
        self.engine = StubEngine(returncode=0, telemetry_text=_SERIES_SPAWNS)
        self.result = self.run_series(self.engine)

    def test_only_matching_spawn_complete_events(self):
        # Fixture has: 2 current-run spawn_complete (impl + review), a run_start and
        # run_complete (lifecycle, skipped), 1 foreign-run-id spawn_complete. Exactly
        # the two current spawn_complete events become records.
        self.assertEqual(len(self.result.runs), 2)
        costs = sorted(r.cost_usd_est for r in self.result.runs)
        self.assertEqual(costs, [0.03, 0.12])
        # The foreign run (cost 9.99 / 9999 tokens) and lifecycle events are gone.
        self.assertTrue(all(r.cost_usd_est < 1.0 for r in self.result.runs))
        self.assertEqual(sum(r.tokens_in for r in self.result.runs), 1300)
        self.assertEqual(sum(r.tokens_out for r in self.result.runs), 600)

    def test_weaker_series_pin(self):
        self.assertEqual(self.result.pin_level, PIN_SERIES)
        for r in self.result.runs:
            # requested/effective model string, not an exact CLI-reported id
            self.assertEqual(r.model_id, "claude-opus-4-8")
            self.assertEqual(r.tokens_cache, 0)  # no cache-token split
            self.assertEqual(r.cli_version, "")

    def test_status_completed_on_clean_exit(self):
        self.assertEqual(self.result.status, TrialStatus.COMPLETED)
        self.assertEqual(self.result.wall_clock_s, 1.0)

    def test_select_run_id_prefers_latest(self):
        # The latest run (June 10) wins over the foreign earlier run (June 9).
        events = [json.loads(line) for line in _SERIES_SPAWNS.splitlines() if line.strip()]
        self.assertEqual(_select_run_id(events, set()), _CURRENT_RUN)

    def test_read_events_skips_malformed_lines(self):
        path = self.task_dir / "scratch_spawns.jsonl"
        path.write_text(
            '{"event": "A", "run_id": "r"}\nnot json at all\n\n{"event": "B", "run_id": "r"}\n',
            encoding="utf-8",
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            events = _read_events(path)
        self.assertEqual([e["event"] for e in events], ["A", "B"])
        self.assertEqual(_read_events(self.task_dir / "missing.jsonl"), [])

    def test_foreign_pre_existing_run_excluded_by_presnapshot(self):
        # If the foreign run id was already present before launch, it is excluded
        # even if it were (hypothetically) the lexicographic max.
        events = [
            {"event": "spawn_complete", "run_id": "ZZZ_OLD", "cost_usd": 9.9},
            {"event": "spawn_complete", "run_id": "AAA_NEW", "cost_usd": 0.1},
        ]
        self.assertEqual(_select_run_id(events, {"ZZZ_OLD"}), "AAA_NEW")
        self.assertEqual(len(_materialize_runs(events, "AAA_NEW")), 1)


# ---------------------------------------------------------------------------
# Series: failure classification (infrastructure before scoring)
# ---------------------------------------------------------------------------


class TestSeriesClassification(SeriesTestBase):
    _RUN = "20260610T150000Z-cccc"
    _IMPL = (
        '{"schema_version": 1, "event": "run_start", "run_id": "%(r)s", "series_id": "demo"}\n'
        '{"schema_version": 1, "event": "spawn_complete", "run_id": "%(r)s", "pr_id": "PR01",'
        ' "role": "implementation", "exit_code": 0, "input_tokens": 100, "output_tokens": 50,'
        ' "num_turns": 2, "duration_s": 3.0, "cost_usd": 0.2, "effective_model": "claude-opus-4-8"}\n'
    ) % {"r": _RUN}

    def _run_complete(self, outcome, integrated):
        return (
            '{"schema_version": 1, "event": "run_complete", "run_id": "%s", "outcome": "%s",'
            ' "integrated": %s}\n' % (self._RUN, outcome, "true" if integrated else "false")
        )

    def test_blocking_red_nonzero_exit_is_errored(self):
        # exit 1 = a blocking gate stayed red — a scored task failure.
        engine = StubEngine(
            returncode=1,
            stdout="PR01 gate stayed red",
            telemetry_text=self._IMPL + self._run_complete("blocked", False),
        )
        result = self.run_series(engine)
        self.assertEqual(result.status, TrialStatus.ERRORED)
        self.assertTrue(result.scored)
        self.assertIn("exit 1", result.detail)
        # records are still materialized from the telemetry even on an errored trial
        self.assertEqual(len(result.runs), 1)

    def test_infrastructure_exit_code_is_infrastructure(self):
        engine = StubEngine(
            returncode=2,
            telemetry_text=self._IMPL + self._run_complete("infrastructure", False),
        )
        result = self.run_series(engine)
        self.assertEqual(result.status, TrialStatus.INFRASTRUCTURE)
        self.assertFalse(result.scored, "an infrastructure halt must not be scored")

    def test_usage_limit_signature_in_stdout_is_infrastructure(self):
        engine = StubEngine(
            returncode=1,
            stdout="Claude usage limit reached. Upgrade to Pro.",
            telemetry_text=self._IMPL,
        )
        result = self.run_series(engine)
        self.assertEqual(result.status, TrialStatus.INFRASTRUCTURE)

    def test_auth_signature_in_stderr_is_infrastructure(self):
        engine = StubEngine(returncode=1, stderr="authentication failed: not logged in")
        result = self.run_series(engine)
        self.assertEqual(result.status, TrialStatus.INFRASTRUCTURE)

    def test_usage_error_exit_is_errored(self):
        # exit 3 = a malformed series.toml — fathom's own bug, surfaced as errored, not infra.
        engine = StubEngine(
            returncode=3, stderr="series.toml: missing required section [governance]"
        )
        result = self.run_series(engine)
        self.assertEqual(result.status, TrialStatus.ERRORED)
        self.assertIn("usage error", result.detail)

    def test_classify_helper_orders_infra_before_exit_code(self):
        # An auth signature on the engine's own channel wins over a bare nonzero exit.
        status, _ = _classify(EngineOutcome(returncode=1, stderr="unauthorized"), [])
        self.assertEqual(status, TrialStatus.INFRASTRUCTURE)
        # Exit code 2 is the engine's explicit infrastructure signal.
        status, _ = _classify(EngineOutcome(returncode=2), [])
        self.assertEqual(status, TrialStatus.INFRASTRUCTURE)
        status, _ = _classify(EngineOutcome(returncode=0), [])
        self.assertEqual(status, TrialStatus.COMPLETED)

    def test_run_complete_infrastructure_outcome_is_infra(self):
        # The engine's own terminal verdict (outcome=infrastructure) classifies as infra.
        events = [{"event": "run_complete", "run_id": "R", "outcome": "infrastructure"}]
        status, _ = _classify(EngineOutcome(returncode=2, stdout=""), events)
        self.assertEqual(status, TrialStatus.INFRASTRUCTURE)

    def test_budget_exit_is_errored_with_clear_detail(self):
        # convoy exit 4 / outcome "budget" = a spawn hit its per-spawn --max-budget-usd
        # cap; convoy does NOT integrate the partial work (integrated=False). This is a
        # governance truncation, not a task result, so it must be ERRORED (excluded from
        # the pass rate by report.py's status=="completed" gate) with a clear detail —
        # never fall through to an opaque "engine exit 4" that reads as a task failure,
        # and never halt the whole matrix (a per-spawn cap is trial-specific, not infra).
        events = [
            {"event": "run_complete", "run_id": "R", "outcome": "budget", "integrated": False}
        ]
        status, detail = _classify(EngineOutcome(returncode=4, stdout=""), events)
        self.assertEqual(status, TrialStatus.ERRORED)  # excluded from scoring, re-runnable
        self.assertNotEqual(status, TrialStatus.INFRASTRUCTURE)  # does not halt the matrix
        self.assertIn("budget", detail.lower())
        self.assertNotIn("engine exit 4", detail)

    def test_budget_outcome_caught_even_if_exit_code_differs(self):
        # Defensive: classify on the engine's own terminal verdict too, not only the
        # exit code, so a budget truncation is caught even if the code path differs.
        events = [
            {"event": "run_complete", "run_id": "R", "outcome": "budget", "integrated": False}
        ]
        status, detail = _classify(EngineOutcome(returncode=1, stdout=""), events)
        self.assertEqual(status, TrialStatus.ERRORED)
        self.assertIn("budget", detail.lower())

    def test_completed_outcome_with_clean_exit_is_completed(self):
        # A clean exit whose telemetry says completed is scored as completed — event
        # field content is not sniffed for infra phrasing (the engine signals it).
        events = [
            {"event": "spawn_complete", "run_id": "R", "role": "implementation", "exit_code": 0},
            {"event": "run_complete", "run_id": "R", "outcome": "completed", "integrated": True},
        ]
        status, _ = _classify(EngineOutcome(returncode=0, stdout="all PRs merged"), events)
        self.assertEqual(status, TrialStatus.COMPLETED)


# ---------------------------------------------------------------------------
# Series: timeout terminates the whole process tree (no orphan)
# ---------------------------------------------------------------------------


class TestTimeoutTreeKill(SeriesTestBase):
    def test_run_trial_timeout_is_errored(self):
        engine = StubEngine(returncode=-1, timed_out=True, duration_s=2.0)
        result = self.run_series(engine)
        self.assertEqual(result.status, TrialStatus.ERRORED)
        self.assertIn("tree", result.detail)

    def test_default_engine_kills_grandchild(self):
        """A stub process tree (python parent → grandchild sleeper): on timeout
        the whole tree dies, so the grandchild `claude` stand-in is not orphaned."""
        work = Path(tempfile.mkdtemp(prefix="fathom-tree-"))
        self.addCleanup(cleanup_dir, str(work))
        child_pidfile = work / "child.pid"
        parent_src = (
            "import subprocess, sys, time\n"
            "cpf = sys.argv[1]\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
            "with open(cpf, 'w') as f:\n"
            "    f.write(str(child.pid))\n"
            "    f.flush()\n"
            "time.sleep(120)\n"
        )
        outcome = _default_run_engine(
            [sys.executable, "-c", parent_src, str(child_pidfile)],
            cwd=str(work),
            env=os.environ.copy(),
            timeout=3,
        )
        self.assertTrue(outcome.timed_out)
        self.assertTrue(child_pidfile.exists(), "grandchild never recorded its pid")
        child_pid = int(child_pidfile.read_text().strip())
        try:
            deadline = time.monotonic() + 5.0
            while pid_alive(child_pid) and time.monotonic() < deadline:
                time.sleep(0.1)
            self.assertFalse(
                pid_alive(child_pid), "grandchild (claude stand-in) was orphaned, not killed"
            )
        finally:
            if pid_alive(child_pid):
                from fathom.strategies.series import _terminate_tree

                _terminate_tree(child_pid)


# ---------------------------------------------------------------------------
# TOML writer round-trips through the stdlib reader
# ---------------------------------------------------------------------------


class TestTomlWriter(unittest.TestCase):
    def test_round_trip(self):
        data = {
            "series": {"id": "x", "version": "1.0"},
            "governance": {
                "model": "m",
                "effort": "high",
                "budgets": {"implementation": 20.0},
            },
            "prs": [
                {"id": "PR01", "branch": "b1", "phase": "1", "depends_on": []},
                {"id": "PR02", "branch": "b2", "phase": "2", "depends_on": ["PR01"]},
            ],
            "checks": [
                {"name": "ruff", "run": "ruff check .", "blocking": True, "independent": False}
            ],
        }
        reparsed = tomllib.loads(dump_toml(data))
        self.assertEqual(reparsed, data)

    def test_windows_path_escaping(self):
        data = {"paths": {"outputs": "C:\\Users\\x\\out", "prompts": 'a"b'}}
        reparsed = tomllib.loads(dump_toml(data))
        self.assertEqual(reparsed["paths"]["outputs"], "C:\\Users\\x\\out")
        self.assertEqual(reparsed["paths"]["prompts"], 'a"b')


# ---------------------------------------------------------------------------
# TrialResult helpers
# ---------------------------------------------------------------------------


class TestTrialResult(unittest.TestCase):
    def test_infrastructure_not_scored(self):
        r = TrialResult(status=TrialStatus.INFRASTRUCTURE, runs=[], pin_level=PIN_SERIES)
        self.assertTrue(r.is_infrastructure)
        self.assertFalse(r.scored)

    def test_errored_is_scored(self):
        r = TrialResult(status=TrialStatus.ERRORED, runs=[], pin_level=PIN_STRONG)
        self.assertFalse(r.is_infrastructure)
        self.assertTrue(r.scored)


if __name__ == "__main__":
    unittest.main(verbosity=2)
