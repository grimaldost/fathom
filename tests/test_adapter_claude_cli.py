"""Tests for src/fathom/adapters/{base,claude_cli}.py — stdlib-runnable.

Run directly:  python tests/test_adapter_claude_cli.py
Run via pytest: uv run pytest tests/test_adapter_claude_cli.py

No real spawns: the subprocess boundary is injected as a stub everywhere
(real-spawn isolation is the smoke gate's job, spec §11).
"""

import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

# Allow `python tests/test_adapter_claude_cli.py` from the project root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.adapters.base import ExitStatus, RunRecord, Runner
from fathom.adapters.claude_cli import (
    ClaudeCliRunner,
    build_command,
    cleanup_dir,
    estimate_cost_usd,
    make_isolated_config,
    parse_stream,
)
from fathom.scenario import LimitsOverride, ResolvedScenario, ToolsConfig

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _scenario(*, effort: str = "high", model: str = "claude-opus-4-8", trial_timeout_s=None):
    """A minimal ResolvedScenario for adapter tests (real dataclass, dummy pins)."""
    return ResolvedScenario(
        name="t",
        adapter="claude-cli",
        model=model,
        strategy="single-session",
        effort=effort,
        tools=ToolsConfig(source="none"),
        limits=LimitsOverride(trial_timeout_s=trial_timeout_s),
        model_id=None,
        tool_repo_sha=None,
        tool_invocation_cmd=None,
        config_hash="x" * 64,
    )


def _cp(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["claude"], returncode=returncode, stdout=stdout, stderr=stderr
    )


class RecordingSpawn:
    """Injectable subprocess boundary that records every call and replays a
    per-call responder.  The responder returns a CompletedProcess or raises
    (e.g. subprocess.TimeoutExpired / FileNotFoundError)."""

    def __init__(self, responder):
        self.responder = responder
        self.calls: list[types.SimpleNamespace] = []

    def __call__(self, argv, *, input, timeout, env, cwd):
        cfg = env.get("CLAUDE_CONFIG_DIR")
        contents = sorted(os.listdir(cfg)) if cfg and os.path.isdir(cfg) else None
        self.calls.append(
            types.SimpleNamespace(
                argv=list(argv),
                input=input,
                timeout=timeout,
                env=dict(env),
                cwd=cwd,
                config_contents=contents,
            )
        )
        return self.responder(len(self.calls) - 1)


class AdapterTestBase(unittest.TestCase):
    """Provides hermetic fake config dirs and a no-op-sleep runner factory."""

    def _fake_real_config(self) -> str:
        """A stand-in for ~/.claude: the credential plus decoys that must NOT leak."""
        real = Path(tempfile.mkdtemp(prefix="fake_real_cfg_"))
        (real / ".credentials.json").write_text('{"token": "secret"}', encoding="utf-8")
        (real / "CLAUDE.md").write_text("real repo paths and discipline", encoding="utf-8")
        (real / "settings.json").write_text("{}", encoding="utf-8")
        (real / "history.jsonl").write_text("{}\n", encoding="utf-8")
        self.addCleanup(cleanup_dir, str(real))
        return str(real)

    def make_runner(self, spawn, **kwargs) -> ClaudeCliRunner:
        kwargs.setdefault("real_config_dir", self._fake_real_config())
        runner = ClaudeCliRunner(spawn=spawn, sleep=lambda _s: None, **kwargs)
        return runner

    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="ws_"))
        self.addCleanup(cleanup_dir, str(self.workspace))


# ---------------------------------------------------------------------------
# build_command — pure argv assembly (headless default-deny)
# ---------------------------------------------------------------------------


class TestBuildCommand(unittest.TestCase):
    def _cmd(self, **overrides):
        kw = dict(
            model="claude-opus-4-8",
            effort="high",
            max_turns=30,
            max_budget_usd=5.0,
            allowed_tools=["Read", "Grep"],
            disallowed_tools=["Write", "Edit", "Bash"],
            stream=True,
        )
        kw.update(overrides)
        return build_command(**kw)

    def test_no_permission_mode_flag(self):
        """bypassPermissions nullifies the allowlist; the flag is never present."""
        cmd = self._cmd()
        self.assertNotIn("--permission-mode", cmd)
        self.assertNotIn("bypassPermissions", cmd)

    def test_no_dangerously_skip_permissions_flag(self):
        self.assertNotIn("--dangerously-skip-permissions", self._cmd())

    def test_no_bare_flag(self):
        """--bare strips the config-bound subscription login; never use it."""
        self.assertNotIn("--bare", self._cmd())

    def test_exact_allowed_tools_list(self):
        cmd = self._cmd()
        self.assertEqual(cmd[cmd.index("--allowed-tools") + 1], "Read,Grep")

    def test_exact_disallowed_tools_list(self):
        cmd = self._cmd()
        self.assertEqual(cmd[cmd.index("--disallowed-tools") + 1], "Write,Edit,Bash")

    def test_effort_flag_present(self):
        cmd = self._cmd(effort="medium")
        self.assertEqual(cmd[cmd.index("--effort") + 1], "medium")

    def test_model_flag_present(self):
        cmd = self._cmd()
        self.assertEqual(cmd[cmd.index("--model") + 1], "claude-opus-4-8")

    def test_per_spawn_budget_and_turn_flags(self):
        cmd = self._cmd()
        self.assertEqual(cmd[cmd.index("--max-turns") + 1], "30")
        self.assertEqual(cmd[cmd.index("--max-budget-usd") + 1], "5.0")

    def test_stream_json_output_format(self):
        cmd = self._cmd(stream=True)
        self.assertIn("stream-json", cmd)
        self.assertIn("--verbose", cmd)

    def test_non_stream_output_format(self):
        cmd = self._cmd(stream=False)
        self.assertIn("json", cmd)
        self.assertNotIn("stream-json", cmd)

    def test_empty_disallowed_tools_omits_flag(self):
        cmd = self._cmd(disallowed_tools=[])
        self.assertNotIn("--disallowed-tools", cmd)

    def test_allowed_tools_always_present_even_when_empty(self):
        """Default-deny: an empty allowlist is still passed explicitly."""
        cmd = self._cmd(allowed_tools=[])
        self.assertIn("--allowed-tools", cmd)
        self.assertEqual(cmd[cmd.index("--allowed-tools") + 1], "")

    def test_zero_budget_omits_flag(self):
        cmd = self._cmd(max_budget_usd=0)
        self.assertNotIn("--max-budget-usd", cmd)

    def test_append_system_prompt_file_present_when_set(self):
        cmd = self._cmd(append_system_prompt_file="/abs/skill.md")
        self.assertIn("--append-system-prompt-file", cmd)
        self.assertEqual(cmd[cmd.index("--append-system-prompt-file") + 1], "/abs/skill.md")

    def test_append_system_prompt_file_absent_when_unset(self):
        self.assertNotIn("--append-system-prompt-file", self._cmd())

    def test_plugin_dir_single_mount(self):
        cmd = self._cmd(plugin_dirs=["A"])
        self.assertIn("--plugin-dir", cmd)
        idx = cmd.index("--plugin-dir")
        self.assertEqual(cmd[idx + 1], "A")

    def test_plugin_dir_multiple_mounts_in_order(self):
        cmd = self._cmd(plugin_dirs=["A", "B"])
        indices = [i for i, x in enumerate(cmd) if x == "--plugin-dir"]
        self.assertEqual(len(indices), 2)
        # First --plugin-dir followed by A
        self.assertEqual(cmd[indices[0] + 1], "A")
        # Second --plugin-dir followed by B
        self.assertEqual(cmd[indices[1] + 1], "B")

    def test_plugin_dir_empty_omits_flag(self):
        cmd = self._cmd(plugin_dirs=[])
        self.assertNotIn("--plugin-dir", cmd)


# ---------------------------------------------------------------------------
# Isolation — credential-only temp CLAUDE_CONFIG_DIR
# ---------------------------------------------------------------------------


class TestIsolation(AdapterTestBase):
    def test_make_isolated_config_is_credentials_only(self):
        """Only .credentials.json is copied — no CLAUDE.md / settings / history leak."""
        real = self._fake_real_config()
        cfg = make_isolated_config(real)
        try:
            self.assertEqual(sorted(os.listdir(cfg)), [".credentials.json"])
            self.assertEqual(
                (Path(cfg) / ".credentials.json").read_text(encoding="utf-8"),
                '{"token": "secret"}',
            )
        finally:
            cleanup_dir(cfg)

    def test_make_isolated_config_handles_missing_credential(self):
        empty = Path(tempfile.mkdtemp(prefix="empty_real_"))
        self.addCleanup(cleanup_dir, str(empty))
        cfg = make_isolated_config(str(empty))
        try:
            self.assertEqual(os.listdir(cfg), [])
        finally:
            cleanup_dir(cfg)

    def test_make_isolated_config_writes_scenario_settings(self):
        """A scenario-declared settings_file is written as settings.json next to
        the credential — an explicit per-arm treatment (the user's real
        settings.json stays excluded, test above)."""
        real = self._fake_real_config()
        holder = Path(tempfile.mkdtemp(prefix="arm_settings_"))
        self.addCleanup(cleanup_dir, str(holder))
        body = '{"hooks": {"PreToolUse": []}}'
        (holder / "arm.json").write_text(body, encoding="utf-8")
        cfg = make_isolated_config(real, settings_file=str(holder / "arm.json"))
        try:
            self.assertEqual(sorted(os.listdir(cfg)), [".credentials.json", "settings.json"])
            self.assertEqual((Path(cfg) / "settings.json").read_text(encoding="utf-8"), body)
        finally:
            cleanup_dir(cfg)

    def test_make_isolated_config_no_settings_by_default(self):
        """Without a settings_file the isolated config has no settings.json."""
        real = self._fake_real_config()
        cfg = make_isolated_config(real)
        try:
            self.assertNotIn("settings.json", os.listdir(cfg))
        finally:
            cleanup_dir(cfg)

    def test_execute_spawns_with_credentials_only_config(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn)
        runner.execute("do the task", self.workspace, _scenario())
        self.assertEqual(spawn.calls[0].config_contents, [".credentials.json"])

    def test_execute_sets_config_dir_env_and_cwd(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn)
        runner.execute("do the task", self.workspace, _scenario())
        call = spawn.calls[0]
        self.assertIn("CLAUDE_CONFIG_DIR", call.env)
        self.assertEqual(call.cwd, str(self.workspace))

    def test_execute_cleans_up_temp_config(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn)
        runner.execute("do the task", self.workspace, _scenario())
        cfg_dir = spawn.calls[0].env["CLAUDE_CONFIG_DIR"]
        self.assertFalse(os.path.isdir(cfg_dir))

    def test_execute_strips_billing_diverters_from_spawn_env(self):
        """A host ANTHROPIC_API_KEY (or Bedrock/Vertex routing) must NOT reach the
        spawn: it would divert billing off the copied subscription credential and
        break USD comparability. Benign vars still pass through."""
        keys = (
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_BASE_URL",
            "CLAUDE_CODE_USE_BEDROCK",
            "FATHOM_BENIGN_DECOY",
        )
        saved = {k: os.environ.get(k) for k in keys}

        def _restore():
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        self.addCleanup(_restore)
        os.environ["ANTHROPIC_API_KEY"] = "sk-should-not-leak"
        os.environ["ANTHROPIC_BASE_URL"] = "https://proxy.invalid"
        os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
        os.environ["FATHOM_BENIGN_DECOY"] = "keep-me"

        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn)
        runner.execute("do the task", self.workspace, _scenario())
        env = spawn.calls[0].env
        self.assertNotIn("ANTHROPIC_API_KEY", env, "API key must be stripped from the spawn env")
        self.assertNotIn("ANTHROPIC_BASE_URL", env, "base-url override must be stripped")
        self.assertNotIn("CLAUDE_CODE_USE_BEDROCK", env, "Bedrock routing must be stripped")
        self.assertIn("CLAUDE_CONFIG_DIR", env, "the isolated config dir must still be set")
        self.assertEqual(env.get("FATHOM_BENIGN_DECOY"), "keep-me", "benign vars must pass through")


# ---------------------------------------------------------------------------
# execute argv — scenario-resolved flags reach the spawn
# ---------------------------------------------------------------------------


class TestExecuteArgv(AdapterTestBase):
    def test_effort_resolved_from_scenario(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn)
        runner.execute("p", self.workspace, _scenario(effort="medium"))
        argv = spawn.calls[0].argv
        self.assertEqual(argv[argv.index("--effort") + 1], "medium")

    def test_model_resolved_from_scenario(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn)
        runner.execute("p", self.workspace, _scenario(model="claude-sonnet-4-6"))
        argv = spawn.calls[0].argv
        self.assertEqual(argv[argv.index("--model") + 1], "claude-sonnet-4-6")

    def test_no_permission_flags_through_execute(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn)
        runner.execute("p", self.workspace, _scenario())
        argv = spawn.calls[0].argv
        self.assertNotIn("--permission-mode", argv)
        self.assertNotIn("--dangerously-skip-permissions", argv)
        self.assertNotIn("bypassPermissions", argv)

    def test_allow_disallow_lists_through_execute(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(
            spawn, allowed_tools=["Read", "Grep"], disallowed_tools=["Write", "Bash"]
        )
        runner.execute("p", self.workspace, _scenario())
        argv = spawn.calls[0].argv
        self.assertEqual(argv[argv.index("--allowed-tools") + 1], "Read,Grep")
        self.assertEqual(argv[argv.index("--disallowed-tools") + 1], "Write,Bash")

    def test_prompt_passed_on_stdin(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn)
        runner.execute("the prompt text", self.workspace, _scenario())
        self.assertEqual(spawn.calls[0].input, "the prompt text")

    def test_max_turns_override_reaches_argv(self):
        # A per-trial max_turns (e.g. from task.limits.max_turns) overrides the
        # adapter default so multi-step tasks are not truncated by the low default.
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn, default_max_turns=30)
        runner.execute("p", self.workspace, _scenario(), max_turns=60)
        argv = spawn.calls[0].argv
        self.assertEqual(argv[argv.index("--max-turns") + 1], "60")

    def test_max_turns_defaults_when_no_override(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn, default_max_turns=25)
        runner.execute("p", self.workspace, _scenario())
        argv = spawn.calls[0].argv
        self.assertEqual(argv[argv.index("--max-turns") + 1], "25")

    def test_inject_path_reaches_argv(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn, append_system_prompt_file="/abs/skill.md")
        runner.execute("p", self.workspace, _scenario())
        argv = spawn.calls[0].argv
        self.assertEqual(argv[argv.index("--append-system-prompt-file") + 1], "/abs/skill.md")

    def test_plugin_dirs_single_mount_reaches_argv(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn, plugin_dirs=["/path/to/plugin1"])
        runner.execute("p", self.workspace, _scenario())
        argv = spawn.calls[0].argv
        idx = argv.index("--plugin-dir")
        self.assertEqual(argv[idx + 1], "/path/to/plugin1")

    def test_plugin_dirs_multiple_mounts_in_order(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn, plugin_dirs=["/path/to/humble", "/path/to/super"])
        runner.execute("p", self.workspace, _scenario())
        argv = spawn.calls[0].argv
        indices = [i for i, x in enumerate(argv) if x == "--plugin-dir"]
        self.assertEqual(len(indices), 2)
        self.assertEqual(argv[indices[0] + 1], "/path/to/humble")
        self.assertEqual(argv[indices[1] + 1], "/path/to/super")

    def test_plugin_dirs_empty_omits_flag(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn, plugin_dirs=[])
        runner.execute("p", self.workspace, _scenario())
        argv = spawn.calls[0].argv
        self.assertNotIn("--plugin-dir", argv)


# ---------------------------------------------------------------------------
# Stream parsing — complete + truncated into RunRecords
# ---------------------------------------------------------------------------


class TestParseComplete(AdapterTestBase):
    def _record(self) -> RunRecord:
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn)
        return runner.execute("p", self.workspace, _scenario())

    def test_status_ok(self):
        self.assertEqual(self._record().status, ExitStatus.OK)

    def test_tokens(self):
        rec = self._record()
        self.assertEqual(rec.tokens_in, 1500)
        self.assertEqual(rec.tokens_out, 350)
        self.assertEqual(rec.tokens_cache, 700)  # cache_read 600 + cache_creation 100

    def test_turns(self):
        self.assertEqual(self._record().num_turns, 3)

    def test_duration(self):
        self.assertEqual(self._record().duration_s, 45.2)  # duration_ms 45200

    def test_cost(self):
        self.assertEqual(self._record().cost_usd_est, 0.1234)

    def test_model_id_from_stream(self):
        self.assertEqual(self._record().model_id, "claude-opus-4-8-20260115")

    def test_cli_version_from_stream(self):
        self.assertEqual(self._record().cli_version, "1.2.3")

    def test_raw_usage_preserved(self):
        self.assertEqual(self._record().usage.get("cache_creation_input_tokens"), 100)


class TestParseTruncated(AdapterTestBase):
    def _record(self) -> RunRecord:
        def responder(i):
            raise subprocess.TimeoutExpired(
                cmd=["claude"], timeout=123, output=_fixture("stream_truncated.jsonl")
            )

        spawn = RecordingSpawn(responder)
        runner = self.make_runner(spawn)
        return runner.execute("p", self.workspace, _scenario(trial_timeout_s=123))

    def test_status_timeout(self):
        self.assertEqual(self._record().status, ExitStatus.TIMEOUT)

    def test_partial_usage_recovered_from_assistant_messages(self):
        rec = self._record()
        self.assertEqual(rec.tokens_in, 900)
        self.assertEqual(rec.tokens_out, 75)
        self.assertEqual(rec.tokens_cache, 150)

    def test_partial_turns_recovered(self):
        self.assertEqual(self._record().num_turns, 2)

    def test_duration_falls_back_to_timeout(self):
        self.assertEqual(self._record().duration_s, 123.0)

    def test_timeout_marker_in_result_text(self):
        self.assertIn("[TIMEOUT after 123s]", self._record().result_text)

    def test_truncated_does_not_crash_on_partial_line(self):
        # The fixture's final line is a JSON fragment cut off by the kill.
        self.assertIsInstance(self._record(), RunRecord)


class TestParseStreamUnit(unittest.TestCase):
    """parse_stream is the pure core — exercise it directly too."""

    def test_tolerates_garbage_lines(self):
        parsed = parse_stream(["not json", "", '{"type": "result", "num_turns": 1}'])
        self.assertEqual(parsed.num_turns, 1)

    def test_empty_stream(self):
        parsed = parse_stream([])
        self.assertEqual(parsed.num_turns, 0)
        self.assertFalse(parsed.saw_result)


# ---------------------------------------------------------------------------
# Cost estimate — token×price fallback (canonical model-tier rates)
# ---------------------------------------------------------------------------


class TestEstimateCostUsd(unittest.TestCase):
    """The pure token×price helper used when the CLI reports total_cost_usd == 0."""

    def test_opus_strong_rate(self):
        # 1000/1k × $0.005 (in) + 1000/1k × $0.025 (out) = 0.030
        self.assertAlmostEqual(estimate_cost_usd("claude-opus-4-8", 1000, 1000), 0.030, places=6)

    def test_sonnet_mid_rate(self):
        self.assertAlmostEqual(estimate_cost_usd("claude-sonnet-4-6", 1000, 1000), 0.018, places=6)

    def test_haiku_weak_rate(self):
        self.assertAlmostEqual(estimate_cost_usd("claude-haiku-4-5", 1000, 1000), 0.006, places=6)

    def test_fable_frontier_rate(self):
        self.assertAlmostEqual(estimate_cost_usd("claude-fable-5", 1000, 1000), 0.060, places=6)

    def test_dated_snapshot_matches_family(self):
        # The CLI reports an exact dated id; family match must still resolve it.
        self.assertAlmostEqual(
            estimate_cost_usd("claude-opus-4-8-20260115", 1000, 1000), 0.030, places=6
        )

    def test_unknown_model_defaults_to_strong(self):
        # An empty/unknown model id falls back to the strong (opus) rate — fathom's
        # default model — so the estimate is conservative rather than zero.
        self.assertAlmostEqual(estimate_cost_usd("", 1000, 1000), 0.030, places=6)
        self.assertAlmostEqual(estimate_cost_usd("mystery-model", 1000, 1000), 0.030, places=6)

    def test_zero_tokens_zero_cost(self):
        self.assertEqual(estimate_cost_usd("claude-opus-4-8", 0, 0), 0.0)


class TestCostFallback(AdapterTestBase):
    """End-to-end: a parsed run reporting total_cost_usd == 0 (subscription) still
    yields a non-zero cost_usd_est from the token×price fallback (D2 / §11)."""

    def _zero_cost_stream(self) -> str:
        return (
            "\n".join(
                json.dumps(obj)
                for obj in (
                    {
                        "type": "system",
                        "subtype": "init",
                        "model": "claude-opus-4-8",
                        "version": "1.2.3",
                    },
                    {"type": "assistant", "message": {"usage": {"input_tokens": 1000}}},
                    {
                        "type": "result",
                        "subtype": "success",
                        "is_error": False,
                        "num_turns": 2,
                        "duration_ms": 1000,
                        "total_cost_usd": 0.0,
                        "result": "done",
                        "usage": {"input_tokens": 1000, "output_tokens": 1000},
                    },
                )
            )
            + "\n"
        )

    def test_fallback_estimate_when_reported_cost_zero(self):
        spawn = RecordingSpawn(lambda i: _cp(0, self._zero_cost_stream()))
        runner = self.make_runner(spawn)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertEqual(rec.status, ExitStatus.OK)
        # opus rate on 1000 in + 1000 out = 0.030; D2 would have left this 0.0.
        self.assertAlmostEqual(rec.cost_usd_est, 0.030, places=6)

    def test_reported_cost_preferred_over_fallback(self):
        # When the CLI DOES report a cost, it wins — the fallback never overrides.
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertEqual(rec.cost_usd_est, 0.1234)


# ---------------------------------------------------------------------------
# Retry — transient failures retried up to the cap, then ERROR
# ---------------------------------------------------------------------------


class TestRetry(AdapterTestBase):
    def test_transient_retried_to_cap(self):
        spawn = RecordingSpawn(lambda i: _cp(1, "", "Error: 529 overloaded_error"))
        runner = self.make_runner(spawn, max_attempts=3)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertEqual(len(spawn.calls), 3)
        self.assertEqual(rec.status, ExitStatus.ERROR)

    def test_transient_then_success(self):
        def responder(i):
            if i == 0:
                return _cp(1, "", "transient 503 error")
            return _cp(0, _fixture("stream_complete.jsonl"))

        spawn = RecordingSpawn(responder)
        runner = self.make_runner(spawn, max_attempts=3)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertEqual(len(spawn.calls), 2)
        self.assertEqual(rec.status, ExitStatus.OK)

    def test_non_transient_error_not_retried(self):
        spawn = RecordingSpawn(lambda i: _cp(1, "", "TypeError: bad task"))
        runner = self.make_runner(spawn, max_attempts=3)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertEqual(len(spawn.calls), 1)
        self.assertEqual(rec.status, ExitStatus.ERROR)


# ---------------------------------------------------------------------------
# Infrastructure classification — auth + usage-limit never score, never retry
# ---------------------------------------------------------------------------


class TestInfrastructureClassification(AdapterTestBase):
    def test_auth_failure_is_infrastructure(self):
        spawn = RecordingSpawn(
            lambda i: _cp(1, "", "Invalid API key · Please run /login to authenticate")
        )
        runner = self.make_runner(spawn, max_attempts=3)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertEqual(rec.status, ExitStatus.INFRASTRUCTURE)
        self.assertTrue(rec.is_infrastructure)

    def test_auth_failure_not_retried(self):
        spawn = RecordingSpawn(lambda i: _cp(1, "", "authentication failed"))
        runner = self.make_runner(spawn, max_attempts=3)
        runner.execute("p", self.workspace, _scenario())
        self.assertEqual(len(spawn.calls), 1)

    def test_usage_limit_is_infrastructure(self):
        # rc==0 but the result event reports the subscription cap — the simple
        # returncode check would miss this; classification reads result_text.
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_usage_limit.jsonl")))
        runner = self.make_runner(spawn, max_attempts=3)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertEqual(rec.status, ExitStatus.INFRASTRUCTURE)

    def test_usage_limit_not_retried(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_usage_limit.jsonl")))
        runner = self.make_runner(spawn, max_attempts=3)
        runner.execute("p", self.workspace, _scenario())
        self.assertEqual(len(spawn.calls), 1)

    def test_usage_limit_not_scored_flag(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_usage_limit.jsonl")))
        runner = self.make_runner(spawn)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertTrue(rec.is_infrastructure)

    def test_session_limit_phrasing_is_infrastructure(self):
        # Exact phrasing observed 2026-07-01: the 5-hour rolling-window refusal.
        # Before the `session limit` alternation this scored as an ERRORED trial
        # and the matrix kept burning cells (~30 poisoned trials) instead of
        # stopping cleanly.
        from fathom.adapters.claude_cli import _classify_infrastructure, _spawn_is_infrastructure

        msg = "You've hit your session limit · resets 11:10pm (America/Sao_Paulo)"
        self.assertTrue(_classify_infrastructure(msg))
        self.assertTrue(_spawn_is_infrastructure("", msg, success=False))

    def test_missing_cli_is_infrastructure(self):
        def responder(i):
            raise FileNotFoundError("claude")

        spawn = RecordingSpawn(responder)
        runner = self.make_runner(spawn)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertEqual(rec.status, ExitStatus.INFRASTRUCTURE)

    def test_successful_task_reporting_auth_status_is_scored(self):
        # A clean success (rc=0, is_error=False) whose RESULT TEXT merely reports that a data
        # source needs auth (an env-setup task) must be SCORED, not misread as a spawn auth
        # failure. Regression: an env-setup task whose result text reports a data source needs auth.
        stream = (
            "\n".join(
                json.dumps(o)
                for o in (
                    {"type": "system", "subtype": "init", "model": "m", "version": "1.2.3"},
                    {
                        "type": "result",
                        "subtype": "success",
                        "is_error": False,
                        "num_turns": 5,
                        "duration_ms": 1000,
                        "result": "dataset_a needs authentication (auth provider not "
                        "configured); unauthorized for dataset_b. result.json written.",
                        "usage": {"input_tokens": 100, "output_tokens": 50},
                    },
                )
            )
            + "\n"
        )
        spawn = RecordingSpawn(lambda i: _cp(0, stream))
        runner = self.make_runner(spawn)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertEqual(rec.status, ExitStatus.OK)

    def test_auth_on_stderr_is_infrastructure_even_if_stdout_ok(self):
        # The spawn's OWN stderr carrying an auth failure is infrastructure regardless of a
        # clean stdout — that is the CLI's auth, not task content.
        spawn = RecordingSpawn(
            lambda i: _cp(0, _fixture("stream_complete.jsonl"), "Invalid API key")
        )
        runner = self.make_runner(spawn)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertEqual(rec.status, ExitStatus.INFRASTRUCTURE)

    def test_successful_task_mentioning_usage_limit_is_scored(self):
        # A clean success (rc=0, is_error=False) whose RESULT TEXT merely mentions a
        # quota/usage-limit phrase — the agent wrote an error handler, a test named
        # test_quota_exceeded, or a CLI hint "Upgrade to Pro" — must be SCORED, not
        # misread as a subscription-cap infra failure. Misreading it discards a good
        # trial, halts the matrix, and re-burns money on resume. Mirror of the auth
        # version above; the usage-limit branch previously ignored `success`.
        stream = (
            "\n".join(
                json.dumps(o)
                for o in (
                    {"type": "system", "subtype": "init", "model": "m", "version": "1.2.3"},
                    {
                        "type": "result",
                        "subtype": "success",
                        "is_error": False,
                        "num_turns": 3,
                        "duration_ms": 900,
                        "result": "Added handler raising QuotaError('quota exceeded'); "
                        "CLI prints 'Upgrade to Pro' when the limit reached. Done.",
                        "usage": {"input_tokens": 100, "output_tokens": 40},
                    },
                )
            )
            + "\n"
        )
        spawn = RecordingSpawn(lambda i: _cp(0, stream))
        runner = self.make_runner(spawn)
        rec = runner.execute("p", self.workspace, _scenario())
        self.assertEqual(
            rec.status,
            ExitStatus.OK,
            "a successful task whose output mentions usage-limit text must be scored",
        )
        self.assertFalse(rec.is_infrastructure)

    def test_spawn_infra_classification_keys_on_success(self):
        from fathom.adapters.claude_cli import _spawn_is_infrastructure

        # success + quota phrase in RESULT TEXT → task content, NOT infrastructure.
        self.assertFalse(
            _spawn_is_infrastructure("", "quota exceeded handled gracefully", success=True)
        )
        self.assertFalse(
            _spawn_is_infrastructure(
                "", "prints 'Upgrade to Pro' on 401 unauthorized", success=True
            )
        )
        # a FAILED spawn with the same phrase IS infrastructure (the real cap).
        self.assertTrue(_spawn_is_infrastructure("", "Claude usage limit reached", success=False))
        # the CLI's OWN stderr carrying the signature is infra regardless of success.
        self.assertTrue(_spawn_is_infrastructure("usage limit reached", "", success=True))
        self.assertTrue(_spawn_is_infrastructure("Invalid API key", "", success=True))


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocol(unittest.TestCase):
    def test_runner_satisfies_protocol(self):
        # ClaudeCliRunner satisfies the runtime-checkable Runner protocol.
        cfg = tempfile.mkdtemp(prefix="proto_")
        self.addCleanup(cleanup_dir, cfg)
        runner = ClaudeCliRunner(real_config_dir=cfg)
        self.assertIsInstance(runner, Runner)
        self.assertTrue(callable(runner.execute))

    def test_run_record_is_infrastructure_property(self):
        self.assertTrue(RunRecord(status=ExitStatus.INFRASTRUCTURE).is_infrastructure)
        self.assertFalse(RunRecord(status=ExitStatus.OK).is_infrastructure)

    def test_run_record_is_error_property(self):
        self.assertFalse(RunRecord(status=ExitStatus.OK).is_error)
        self.assertTrue(RunRecord(status=ExitStatus.ERROR).is_error)
        self.assertTrue(RunRecord(status=ExitStatus.TIMEOUT).is_error)
        self.assertTrue(RunRecord(status=ExitStatus.INFRASTRUCTURE).is_error)


class TestSubprocessSpawnKillsTree(unittest.TestCase):
    """The default subprocess boundary kills the whole process tree on timeout.

    Token-free: a python parent that spawns a grandchild sleeper stands in for the
    claude CLI and its tool subprocesses. Regression for the adapter timeout path
    (unlike the engine path) orphaning tool grandchildren that keep mutating the
    workspace the verifier is about to score.
    """

    def test_timeout_kills_grandchild(self):
        import time

        from fathom.adapters.claude_cli import _subprocess_spawn, pid_alive, terminate_process_tree

        work = Path(tempfile.mkdtemp(prefix="fathom-adapter-tree-"))
        child_pidfile = work / "child.pid"
        try:
            parent_src = (
                "import subprocess, sys, time\n"
                "cpf = sys.argv[1]\n"
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
                "with open(cpf, 'w') as f:\n"
                "    f.write(str(child.pid))\n"
                "    f.flush()\n"
                "time.sleep(120)\n"
            )
            with self.assertRaises(subprocess.TimeoutExpired):
                _subprocess_spawn(
                    [sys.executable, "-c", parent_src, str(child_pidfile)],
                    input="",
                    timeout=3,
                    env=os.environ.copy(),
                    cwd=str(work),
                )
            self.assertTrue(child_pidfile.exists(), "grandchild never recorded its pid")
            child_pid = int(child_pidfile.read_text().strip())
            deadline = time.monotonic() + 5.0
            while pid_alive(child_pid) and time.monotonic() < deadline:
                time.sleep(0.1)
            self.assertFalse(pid_alive(child_pid), "grandchild (tool stand-in) was orphaned")
        finally:
            if child_pidfile.exists():
                cpid = int(child_pidfile.read_text().strip())
                if pid_alive(cpid):
                    terminate_process_tree(cpid)
            cleanup_dir(str(work))


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
