"""Tests for src/fathom/smoke.py — the assertion plumbing, with stubs only.

Stdlib-runnable:
    python tests/test_smoke_logic.py
Via pytest:
    uv run pytest tests/test_smoke_logic.py

No real spawns and no real engine here: the pure assertions are driven with
crafted observations, and ``run_smoke`` runs against a stub implementing the
``SmokeProbes`` protocol.  The real-spawn / engine-boundary path is exercised
manually via ``fathom smoke`` (spec §11) and its output pasted into the PR summary.
The one filesystem touch is forging a shim file (never executed) to prove the
forge + argv-log round-trip.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Allow `python tests/test_smoke_logic.py` from the project root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.adapters.base import ExitStatus, RunRecord
from fathom.adapters.claude_cli import cleanup_dir
from fathom.smoke import (
    CANARY_SKILL,
    INJECTION_CANARY,
    SmokeResult,
    assert_activity_detected,
    assert_authed_completes,
    assert_canary_skill_absent,
    assert_canary_skill_mounted,
    assert_injection_armed,
    assert_isolated_config_is_credential_only,
    assert_no_bypass_in_engine_spawn,
    assert_tool_denied,
    forge_claude_shim,
    injection_file_of,
    parse_init_skills,
    permission_mode_of,
    read_argv_log,
    run_smoke,
)
from fathom.strategies.series import NON_BYPASS_PERMISSION_MODE


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _ok_record(**kw):
    base = dict(status=ExitStatus.OK, num_turns=2, tokens_in=10, tokens_out=5)
    base.update(kw)
    return RunRecord(**base)


def _good_argv(mode=NON_BYPASS_PERMISSION_MODE):
    return [
        "claude",
        "--print",
        "--output-format",
        "json",
        "--model",
        "claude-opus-4-8",
        "--effort",
        "high",
        "--permission-mode",
        mode,
        "--no-session-persistence",
        "--allowed-tools",
        "Read",
    ]


class StubProbes:
    """A SmokeProbes implementation that replays canned observations."""

    def __init__(
        self,
        *,
        config_contents=None,
        authed=None,
        deny=None,
        injection=None,
        mount_treatment=None,
        mount_control=None,
        engine_argvs=None,
        raise_on=None,
    ):
        self._config = config_contents if config_contents is not None else [".credentials.json"]
        self._authed = authed if authed is not None else _ok_record()
        self._deny = deny if deny is not None else ([], _ok_record())
        self._injection = (
            injection
            if injection is not None
            else (
                _good_argv() + ["--append-system-prompt-file", "/skill.md"],
                _ok_record(result_text=f"hi {INJECTION_CANARY}"),
            )
        )
        # By default, the treatment has the canary; the control does not.
        self._mount_treatment = (
            mount_treatment if mount_treatment is not None else [CANARY_SKILL, "other:skill"]
        )
        self._mount_control = mount_control if mount_control is not None else ["other:skill"]
        self._engine = engine_argvs if engine_argvs is not None else [_good_argv()]
        self._raise_on = set(raise_on or ())
        self.calls = []

    def isolated_config_contents(self):
        self.calls.append("config")
        if "config" in self._raise_on:
            raise RuntimeError("config boom")
        return self._config

    def authed_spawn(self):
        self.calls.append("authed")
        if "authed" in self._raise_on:
            raise RuntimeError("authed boom")
        return self._authed

    def deny_spawn(self):
        self.calls.append("deny")
        if "deny" in self._raise_on:
            raise RuntimeError("deny boom")
        return self._deny

    def injection_spawn(self):
        self.calls.append("injection")
        if "injection" in self._raise_on:
            raise RuntimeError("injection boom")
        return self._injection

    def mount_treatment_skills(self):
        self.calls.append("mount_treatment")
        if "mount_treatment" in self._raise_on:
            raise RuntimeError("mount_treatment boom")
        return self._mount_treatment

    def mount_control_skills(self):
        self.calls.append("mount_control")
        if "mount_control" in self._raise_on:
            raise RuntimeError("mount_control boom")
        return self._mount_control

    def engine_spawn_argvs(self):
        self.calls.append("engine")
        if "engine" in self._raise_on:
            raise RuntimeError("engine boom")
        return self._engine


# ---------------------------------------------------------------------------
# Pure assertions
# ---------------------------------------------------------------------------


class TestConfigAssertion(unittest.TestCase):
    def test_credential_only_passes(self):
        r = assert_isolated_config_is_credential_only([".credentials.json"])
        self.assertTrue(r.ok)

    def test_extra_file_fails(self):
        r = assert_isolated_config_is_credential_only([".credentials.json", "CLAUDE.md"])
        self.assertFalse(r.ok, "a leaked CLAUDE.md must fail the credential-only check")

    def test_empty_config_fails(self):
        self.assertFalse(assert_isolated_config_is_credential_only([]).ok)


class TestAuthedAndActivity(unittest.TestCase):
    def test_ok_status_passes(self):
        self.assertTrue(assert_authed_completes(_ok_record()).ok)

    def test_infrastructure_status_fails(self):
        r = assert_authed_completes(_ok_record(status=ExitStatus.INFRASTRUCTURE))
        self.assertFalse(r.ok, "an auth/usage-limit (infra) status is not a completion")

    def test_error_status_fails(self):
        self.assertFalse(assert_authed_completes(_ok_record(status=ExitStatus.ERROR)).ok)

    def test_activity_from_turns(self):
        self.assertTrue(assert_activity_detected(_ok_record(num_turns=1, tokens_out=0)).ok)

    def test_activity_from_tokens(self):
        self.assertTrue(assert_activity_detected(_ok_record(num_turns=0, tokens_out=3)).ok)

    def test_no_activity_fails(self):
        r = assert_activity_detected(_ok_record(num_turns=0, tokens_in=0, tokens_out=0))
        self.assertFalse(r.ok, "zero turns and zero tokens means the parser saw no activity")


class TestToolDenied(unittest.TestCase):
    def test_no_files_passes(self):
        self.assertTrue(assert_tool_denied([], _ok_record()).ok)

    def test_leaked_file_fails(self):
        r = assert_tool_denied(["probe.txt"], _ok_record())
        self.assertFalse(r.ok, "a created file means default-deny did not hold")
        self.assertIn("probe.txt", r.detail)


class TestPermissionModeOf(unittest.TestCase):
    def test_extracts_value(self):
        self.assertEqual(permission_mode_of(_good_argv("default")), "default")

    def test_missing_returns_none(self):
        self.assertIsNone(permission_mode_of(["claude", "--print", "--model", "m"]))

    def test_flag_at_end_without_value_returns_none(self):
        self.assertIsNone(permission_mode_of(["claude", "--permission-mode"]))


def test_injection_file_of():
    assert injection_file_of(["claude", "--append-system-prompt-file", "/a.md"]) == "/a.md"
    assert injection_file_of(["claude", "-p"]) is None


class TestInjectionArmed(unittest.TestCase):
    """K7: a treatment spawn is armed only if --append-system-prompt-file reached
    the argv AND the injected canary directive reached the model (OK spawn)."""

    def _armed_argv(self):
        return _good_argv("default") + ["--append-system-prompt-file", "/skill.md"]

    def test_armed_passes(self):
        rec = _ok_record(result_text=f"Hello! {INJECTION_CANARY}")
        self.assertTrue(assert_injection_armed(self._armed_argv(), rec).ok)

    def test_missing_flag_fails(self):
        rec = _ok_record(result_text=f"Hello! {INJECTION_CANARY}")
        self.assertFalse(
            assert_injection_armed(_good_argv("default"), rec).ok,
            "no --append-system-prompt-file means the treatment arm is not armed",
        )

    def test_missing_canary_fails(self):
        rec = _ok_record(result_text="Hello, friend!")
        self.assertFalse(
            assert_injection_armed(self._armed_argv(), rec).ok,
            "canary absent means the injected system prompt did not reach the model",
        )

    def test_infra_status_fails(self):
        rec = _ok_record(status=ExitStatus.INFRASTRUCTURE, result_text=INJECTION_CANARY)
        self.assertFalse(assert_injection_armed(self._armed_argv(), rec).ok)


class TestEngineBoundaryAssertion(unittest.TestCase):
    def test_pinned_default_passes(self):
        r = assert_no_bypass_in_engine_spawn([_good_argv("default")])
        self.assertTrue(r.ok, r.detail)

    def test_empty_fails(self):
        r = assert_no_bypass_in_engine_spawn([])
        self.assertFalse(r.ok, "no recorded spawn means the boundary was never exercised")

    def test_bypass_mode_fails(self):
        r = assert_no_bypass_in_engine_spawn([_good_argv("bypassPermissions")])
        self.assertFalse(r.ok)
        self.assertIn("bypassPermissions", r.detail)

    def test_dangerously_skip_flag_fails(self):
        argv = _good_argv("default") + ["--dangerously-skip-permissions"]
        r = assert_no_bypass_in_engine_spawn([argv])
        self.assertFalse(r.ok)
        self.assertIn("--dangerously-skip-permissions", r.detail)

    def test_missing_mode_fails(self):
        r = assert_no_bypass_in_engine_spawn([["claude", "--print", "--model", "m"]])
        self.assertFalse(r.ok)
        self.assertIn("missing --permission-mode", r.detail)

    def test_one_bad_among_good_fails(self):
        r = assert_no_bypass_in_engine_spawn(
            [_good_argv("default"), _good_argv("bypassPermissions")]
        )
        self.assertFalse(r.ok, "a single bypass spawn fails the whole boundary check")

    def test_custom_non_bypass_mode_param(self):
        # A mode that is not the pinned value is a mismatch (the pin did not reach).
        r = assert_no_bypass_in_engine_spawn([_good_argv("acceptEdits")], non_bypass_mode="default")
        self.assertFalse(r.ok)


# ---------------------------------------------------------------------------
# parse_init_skills
# ---------------------------------------------------------------------------


class TestParseInitSkills(unittest.TestCase):
    def _lines(self, *objs):
        return [json.dumps(obj) for obj in objs]

    def test_extracts_skills_from_init_event(self):
        lines = self._lines(
            {"type": "system", "subtype": "init", "model": "haiku", "skills": ["a:b", "c:d"]},
        )
        self.assertEqual(parse_init_skills(lines), ["a:b", "c:d"])

    def test_empty_when_no_init_event(self):
        lines = self._lines({"type": "assistant", "message": {"content": "hi"}})
        self.assertEqual(parse_init_skills(lines), [])

    def test_empty_when_skills_absent(self):
        lines = self._lines({"type": "system", "subtype": "init", "model": "haiku"})
        self.assertEqual(parse_init_skills(lines), [])

    def test_empty_when_skills_not_a_list(self):
        lines = self._lines({"type": "system", "subtype": "init", "skills": "not-a-list"})
        self.assertEqual(parse_init_skills(lines), [])

    def test_skips_malformed_json_lines(self):
        lines = [
            "not json at all\n",
            json.dumps({"type": "system", "subtype": "init", "skills": ["x:y"]}) + "\n",
        ]
        self.assertEqual(parse_init_skills(lines), ["x:y"])

    def test_returns_first_init_event_only(self):
        lines = self._lines(
            {"type": "system", "subtype": "init", "skills": ["first:skill"]},
            {"type": "system", "subtype": "init", "skills": ["second:skill"]},
        )
        self.assertEqual(parse_init_skills(lines), ["first:skill"])

    def test_empty_list_on_empty_input(self):
        self.assertEqual(parse_init_skills([]), [])

    def test_filters_empty_skill_strings(self):
        lines = self._lines(
            {"type": "system", "subtype": "init", "skills": ["real:skill", "", "other:one"]},
        )
        self.assertEqual(parse_init_skills(lines), ["real:skill", "other:one"])


# ---------------------------------------------------------------------------
# assert_canary_skill_mounted / assert_canary_skill_absent
# ---------------------------------------------------------------------------


class TestMountAssertions(unittest.TestCase):
    def test_mounted_passes_when_canary_present(self):
        r = assert_canary_skill_mounted([CANARY_SKILL, "other:skill"])
        self.assertTrue(r.ok, r.detail)

    def test_mounted_fails_when_canary_absent(self):
        r = assert_canary_skill_mounted(["other:skill"])
        self.assertFalse(r.ok, "canary absent from skills means the mount did not register")
        self.assertIn(CANARY_SKILL, r.detail)

    def test_mounted_fails_when_skills_empty(self):
        r = assert_canary_skill_mounted([])
        self.assertFalse(r.ok)
        self.assertIn(CANARY_SKILL, r.detail)

    def test_absent_passes_when_canary_not_present(self):
        r = assert_canary_skill_absent(["other:skill"])
        self.assertTrue(r.ok, r.detail)

    def test_absent_fails_when_canary_is_present(self):
        r = assert_canary_skill_absent([CANARY_SKILL, "other:skill"])
        self.assertFalse(r.ok, "canary present in control spawn means something is wrong")
        self.assertIn(CANARY_SKILL, r.detail)

    def test_absent_passes_for_empty_skills(self):
        r = assert_canary_skill_absent([])
        self.assertTrue(r.ok)


# ---------------------------------------------------------------------------
# run_smoke orchestration
# ---------------------------------------------------------------------------


class TestRunSmoke(unittest.TestCase):
    def _run(self, probes, **kw):
        out = io.StringIO()
        code = run_smoke(probes, out=out, **kw)
        return code, out.getvalue()

    def test_all_pass_returns_zero(self):
        code, output = self._run(StubProbes())
        self.assertEqual(code, 0)
        self.assertIn("ALL PASS", output)
        self.assertNotIn("[FAIL]", output)

    def test_reports_every_check(self):
        # 8 checks when engine included:
        #   config, authed, activity, deny, injection, mount-treatment, mount-control, engine.
        code, output = self._run(StubProbes())
        self.assertEqual(output.count("[PASS]"), 8, output)
        self.assertIn("(8/8 checks)", output)

    def test_force_fail_returns_one(self):
        code, output = self._run(StubProbes(), force_fail=True)
        self.assertEqual(
            code, 1, "force-fail must produce a nonzero exit even when all else passes"
        )
        self.assertIn("SOME FAILED", output)
        self.assertIn("forced failure", output)

    def test_failing_assertion_returns_one(self):
        probes = StubProbes(engine_argvs=[_good_argv("bypassPermissions")])
        code, output = self._run(probes)
        self.assertEqual(code, 1)
        self.assertIn("[FAIL]", output)

    def test_infra_authed_fails_run(self):
        probes = StubProbes(authed=_ok_record(status=ExitStatus.INFRASTRUCTURE, num_turns=0))
        code, _ = self._run(probes)
        self.assertEqual(code, 1)

    def test_leaked_file_fails_run(self):
        probes = StubProbes(deny=(["probe.txt"], _ok_record()))
        code, _ = self._run(probes)
        self.assertEqual(code, 1)

    def test_probe_exception_is_guarded(self):
        probes = StubProbes(raise_on={"engine"})
        code, output = self._run(probes)
        self.assertEqual(code, 1, "a raising probe must fail the gate, not crash it")
        self.assertIn("(probe error)", output)
        self.assertIn("engine boom", output)

    def test_mount_probe_exception_is_guarded(self):
        probes = StubProbes(raise_on={"mount_treatment"})
        code, output = self._run(probes)
        self.assertEqual(code, 1, "a raising mount probe must fail the gate, not crash it")
        self.assertIn("(probe error)", output)
        self.assertIn("mount_treatment boom", output)

    def test_missing_canary_in_treatment_fails(self):
        probes = StubProbes(mount_treatment=["other:skill"])
        code, _ = self._run(probes)
        self.assertEqual(code, 1)

    def test_canary_present_in_control_fails(self):
        probes = StubProbes(mount_control=[CANARY_SKILL, "other:skill"])
        code, _ = self._run(probes)
        self.assertEqual(code, 1)

    def test_include_engine_false_skips_engine(self):
        probes = StubProbes()
        code, output = self._run(probes, include_engine=False)
        self.assertEqual(code, 0)
        self.assertNotIn("engine", probes.calls, "engine probe must not run when excluded")
        self.assertEqual(output.count("[PASS]"), 7)

    def test_order_config_authed_deny_injection_mount_engine(self):
        probes = StubProbes()
        self._run(probes)
        self.assertEqual(
            probes.calls,
            ["config", "authed", "deny", "injection", "mount_treatment", "mount_control", "engine"],
        )


# ---------------------------------------------------------------------------
# Shim forge + argv-log round-trip (filesystem only; the shim is never executed)
# ---------------------------------------------------------------------------


class TestArgvLog(unittest.TestCase):
    def test_round_trip_skips_malformed_and_blank(self):
        d = Path(tempfile.mkdtemp(prefix="fathom-smoke-log-"))
        self.addCleanup(cleanup_dir, str(d))
        log = d / "argv.jsonl"
        log.write_text(
            '["claude", "--print"]\n'
            "not json at all\n"
            "\n"
            '{"not": "a list"}\n'
            '["claude", "--permission-mode", "default"]\n',
            encoding="utf-8",
        )
        argvs = read_argv_log(log)
        self.assertEqual(argvs, [["claude", "--print"], ["claude", "--permission-mode", "default"]])

    def test_missing_file_is_empty(self):
        self.assertEqual(read_argv_log(Path(tempfile.gettempdir()) / "does-not-exist.jsonl"), [])


class TestForgeShim(unittest.TestCase):
    def test_forge_writes_a_nonempty_shim(self):
        d = Path(tempfile.mkdtemp(prefix="fathom-smoke-forge-"))
        self.addCleanup(cleanup_dir, str(d))
        record = d / "argv.jsonl"
        try:
            shim = forge_claude_shim(d, record)
        except RuntimeError as exc:
            # Windows needs a distlib launcher stub to forge claude.exe; if this
            # environment lacks one, the forge is unavailable (not a logic bug).
            self.skipTest(f"shim forge unavailable here: {exc}")
        self.assertTrue(shim.is_file())
        self.assertGreater(shim.stat().st_size, 0)
        expected = "claude.exe" if os.name == "nt" else "claude"
        self.assertEqual(shim.name, expected)


class TestSmokeResult(unittest.TestCase):
    def test_fields(self):
        r = SmokeResult("x", True, "d")
        self.assertEqual((r.name, r.ok, r.detail), ("x", True, "d"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
