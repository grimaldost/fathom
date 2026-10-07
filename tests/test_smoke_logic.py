"""Tests for src/fathom/smoke.py — the assertion plumbing, with stubs only.

Stdlib-runnable:
    python tests/test_smoke_logic.py
Via pytest:
    uv run pytest tests/test_smoke_logic.py

No real spawns and no real engine here: the pure assertions are driven with
crafted observations, and ``run_smoke`` runs against a stub implementing the
``SmokeProbes`` protocol.  The real-spawn / engine-boundary path is exercised
manually via ``fathom smoke`` (spec §11) and its output pasted into the PR summary.
The filesystem touches are forging a shim file (never executed) to prove the
forge + argv-log round-trip, and the temp directories the injection and mount
probes make when they run against a stub CLI in place of the subprocess boundary.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import ClassVar
from unittest import mock

# Allow `python tests/test_smoke_logic.py` from the project root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.adapters.base import ExitStatus, RunRecord
from fathom.adapters.claude_cli import cleanup_dir
from fathom.smoke import (
    CANARY_PLUGIN_DIR,
    CANARY_SKILL,
    CREDENTIAL_MIN_TTL_S,
    INJECTION_CANARY,
    MEMORY_ABOVE_CANARY,
    MEMORY_INSIDE_CANARY,
    CredentialStatus,
    SmokeResult,
    assert_activity_detected,
    assert_authed_completes,
    assert_canary_skill_absent,
    assert_canary_skill_mounted,
    assert_credential_live,
    assert_injection_armed,
    assert_isolated_config_is_credential_only,
    assert_no_ancestor_memory,
    assert_no_bypass_in_engine_spawn,
    assert_tool_denied,
    forge_claude_shim,
    injection_file_of,
    parse_init_skills,
    permission_mode_of,
    read_argv_log,
    read_credential_status,
    run_smoke,
)
from fathom.strategies.series import NON_BYPASS_PERMISSION_MODE

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _ok_record(**kw):
    base = {"status": ExitStatus.OK, "num_turns": 2, "tokens_in": 10, "tokens_out": 5}
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


_NOW_S = 1_700_000_000.0


def _live_credential(at=None, **kw):
    """A credential whose refresh window comfortably clears the gate's horizon.

    Relative to *at* (default: the real clock), so a stub is live whether or not the
    test pins `now_s`.
    """
    now = time.time() if at is None else at
    base = {
        "found": True,
        "readable": True,
        "expires_at_ms": int((now + 3600) * 1000),
        "refresh_expires_at_ms": int((now + 30 * 86400) * 1000),
    }
    base.update(kw)
    return CredentialStatus(**base)


class StubProbes:
    """A SmokeProbes implementation that replays canned observations."""

    def __init__(
        self,
        *,
        credential=None,
        config_contents=None,
        authed=None,
        deny=None,
        injection=None,
        memory=None,
        mount_treatment=None,
        mount_control=None,
        engine_argvs=None,
        raise_on=None,
    ):
        self._credential = credential if credential is not None else _live_credential()
        self._config = config_contents if config_contents is not None else [".credentials.json"]
        self._authed = authed if authed is not None else _ok_record()
        self._deny = deny if deny is not None else ([], _ok_record())
        self._injection = (
            injection
            if injection is not None
            else (
                [*_good_argv(), "--append-system-prompt-file", "/skill.md"],
                _ok_record(result_text=f"hi {INJECTION_CANARY}"),
            )
        )
        self._memory = (
            memory if memory is not None else _ok_record(result_text=f"hi {MEMORY_INSIDE_CANARY}")
        )
        # By default, the treatment has the canary; the control does not.
        self._mount_treatment = (
            mount_treatment if mount_treatment is not None else [CANARY_SKILL, "other:skill"]
        )
        self._mount_control = mount_control if mount_control is not None else ["other:skill"]
        self._engine = engine_argvs if engine_argvs is not None else [_good_argv()]
        self._raise_on = set(raise_on or ())
        self.calls = []

    def credential_status(self):
        self.calls.append("credential")
        if "credential" in self._raise_on:
            raise RuntimeError("credential boom")
        return self._credential

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

    def memory_spawn(self):
        self.calls.append("memory")
        if "memory" in self._raise_on:
            raise RuntimeError("memory boom")
        return self._memory

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


class TestAncestorMemoryAssertion(unittest.TestCase):
    def test_the_workspace_file_alone_passes(self):
        record = _ok_record(result_text=f"Hello. {MEMORY_INSIDE_CANARY}")
        self.assertTrue(assert_no_ancestor_memory(record).ok)

    def test_a_file_from_above_the_workspace_fails(self):
        text = f"Hello. {MEMORY_INSIDE_CANARY} {MEMORY_ABOVE_CANARY}"
        result = assert_no_ancestor_memory(_ok_record(result_text=text))
        self.assertFalse(result.ok)
        self.assertIn("above_canary=True", result.detail)

    def test_a_spawn_that_read_no_instruction_file_proves_nothing(self):
        self.assertFalse(assert_no_ancestor_memory(_ok_record(result_text="Hello.")).ok)


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


# ---------------------------------------------------------------------------
# The credential pre-flight, and the two checks that passed HOLLOW
#
# Both checks once passed hollow:
#   "stream parsing detects activity" passed with turns=1 tokens_in=0 tokens_out=0
#   "disallowed tool refused"        passed with no tool call to refuse
# Neither verified the spawn was live before asserting on it, so an unauthenticated
# spawn made them PASS by absence — a vacuous gate inside the trust gate, and a
# headline of all-but-one passing read as "mostly fine".
# ---------------------------------------------------------------------------


class TestCredentialPreflight(unittest.TestCase):
    def test_live_credential_passes(self):
        r = assert_credential_live(_live_credential(at=_NOW_S), now_s=_NOW_S)
        self.assertTrue(r.ok, r.detail)
        self.assertFalse(r.skipped)

    def test_dead_refresh_token_fails_and_says_reauthenticate(self):
        dead = _live_credential(
            at=_NOW_S,
            expires_at_ms=int((_NOW_S - 86400) * 1000),
            refresh_expires_at_ms=int((_NOW_S - 3600) * 1000),
        )
        r = assert_credential_live(dead, now_s=_NOW_S)
        self.assertFalse(r.ok, "an expired refresh token is a dead seat, not a warning")
        self.assertIn("re-authenticate", r.detail.lower())

    def test_expired_access_token_with_live_refresh_passes(self):
        # The CLI refreshes on demand; a short-lived access token is normal.
        refreshable = _live_credential(at=_NOW_S, expires_at_ms=int((_NOW_S - 60) * 1000))
        self.assertTrue(assert_credential_live(refreshable, now_s=_NOW_S).ok)

    def test_refresh_window_under_the_horizon_fails(self):
        short = _live_credential(
            at=_NOW_S, refresh_expires_at_ms=int((_NOW_S + CREDENTIAL_MIN_TTL_S / 2) * 1000)
        )
        r = assert_credential_live(short, now_s=_NOW_S)
        self.assertFalse(r.ok, "less life than the gate's own horizon must refuse before spend")

    def test_missing_file_fails_rather_than_passing_by_absence(self):
        absent = CredentialStatus(found=False, readable=False)
        r = assert_credential_live(absent, now_s=_NOW_S)
        self.assertFalse(r.ok, "a missing file must fail, not pass by absence")

    def test_unparsable_file_fails(self):
        shapeless = CredentialStatus(found=True, readable=True, detail="no claudeAiOauth block")
        self.assertFalse(assert_credential_live(shapeless, now_s=_NOW_S).ok)


class TestCredentialReaderTakesMetadataOnly(unittest.TestCase):
    """ADR-0004: the credential is copied, never read.  The pre-flight reads two
    integers out of it and must not surface anything else, ever."""

    def _write(self, body):
        d = Path(tempfile.mkdtemp(prefix="fathom-cred-"))
        self.addCleanup(cleanup_dir, str(d))
        p = d / ".credentials.json"
        p.write_text(json.dumps(body), encoding="utf-8")
        return p

    def test_reads_the_two_timestamps(self):
        p = self._write(
            {
                "claudeAiOauth": {
                    "accessToken": "SENTINEL-ACCESS",
                    "refreshToken": "SENTINEL-REFRESH",
                    "expiresAt": 1234000,
                    "refreshTokenExpiresAt": 5678000,
                    "subscriptionType": "max",
                }
            }
        )
        st = read_credential_status(p)
        self.assertTrue(st.found and st.readable)
        self.assertEqual(st.expires_at_ms, 1234000)
        self.assertEqual(st.refresh_expires_at_ms, 5678000)

    def test_no_token_value_reaches_the_status_or_its_rendering(self):
        p = self._write(
            {
                "claudeAiOauth": {
                    "accessToken": "SENTINEL-ACCESS",
                    "refreshToken": "SENTINEL-REFRESH",
                    "expiresAt": 1234000,
                    "refreshTokenExpiresAt": 5678000,
                },
                "mcpOAuth": {"some:server": {"accessToken": "SENTINEL-MCP"}},
            }
        )
        st = read_credential_status(p)
        rendered = repr(st) + assert_credential_live(st, now_s=_NOW_S).detail
        for sentinel in ("SENTINEL-ACCESS", "SENTINEL-REFRESH", "SENTINEL-MCP"):
            self.assertNotIn(sentinel, rendered, "a token value must never leave the file")

    def test_missing_file_is_found_false(self):
        d = Path(tempfile.mkdtemp(prefix="fathom-cred-"))
        self.addCleanup(cleanup_dir, str(d))
        st = read_credential_status(d / "nope.json")
        self.assertFalse(st.found)

    def test_malformed_json_is_readable_false(self):
        d = Path(tempfile.mkdtemp(prefix="fathom-cred-"))
        self.addCleanup(cleanup_dir, str(d))
        p = d / ".credentials.json"
        p.write_text("{not json", encoding="utf-8")
        st = read_credential_status(p)
        self.assertTrue(st.found)
        self.assertFalse(st.readable)


class TestLivenessGating(unittest.TestCase):
    """The two checks must not conclude anything from a spawn that never ran."""

    _DEAD: ClassVar[dict[str, object]] = {
        "status": ExitStatus.INFRASTRUCTURE,
        "num_turns": 1,
        "tokens_in": 0,
        "tokens_out": 0,
    }

    def test_activity_is_skipped_not_passed_on_a_dead_spawn(self):
        r = assert_activity_detected(_ok_record(**self._DEAD))
        self.assertFalse(r.ok, "a spawn that never authenticated proves no stream parsing")
        self.assertTrue(r.skipped, "and it is SKIPPED, not a failure of the parser")
        self.assertIn("spawn not live", r.detail)

    def test_denial_is_skipped_not_passed_on_a_dead_spawn(self):
        r = assert_tool_denied([], _ok_record(**self._DEAD))
        self.assertFalse(r.ok, "no tool call was made, so no refusal was observed")
        self.assertTrue(r.skipped)
        self.assertIn("spawn not live", r.detail)

    def test_live_spawn_with_no_token_flow_is_a_real_failure(self):
        # Turns alone are the harness's own accounting; tokens are the model's.
        r = assert_activity_detected(_ok_record(num_turns=1, tokens_in=0, tokens_out=0))
        self.assertFalse(r.ok)
        self.assertFalse(r.skipped, "an OK spawn with no tokens is a parser failure, not a skip")


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
    """A treatment spawn is armed only if --append-system-prompt-file reached
    the argv AND the injected canary directive reached the model (OK spawn)."""

    def _armed_argv(self):
        return [*_good_argv("default"), "--append-system-prompt-file", "/skill.md"]

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
        argv = [*_good_argv("default"), "--dangerously-skip-permissions"]
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


class TestCanaryPlugin(unittest.TestCase):
    """The canary plugin ships as package data, so an installed wheel can run
    `fathom smoke` from any data root, not only from a source checkout."""

    def test_lives_inside_the_package(self):
        import fathom

        self.assertEqual(CANARY_PLUGIN_DIR.parent, Path(fathom.__file__).resolve().parent)

    def test_manifest_and_skill_match_the_asserted_skill_id(self):
        plugin_name, skill_dir = CANARY_SKILL.split(":")
        manifest_path = CANARY_PLUGIN_DIR / ".claude-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], plugin_name)
        skill = CANARY_PLUGIN_DIR / "skills" / skill_dir / "SKILL.md"
        self.assertTrue(skill.is_file(), f"missing {skill}")
        frontmatter = skill.read_text(encoding="utf-8").splitlines()
        self.assertIn(f"name: {skill_dir}", frontmatter)


class TestEngineBoundaryNeedsDataRoot(unittest.TestCase):
    """The engine-boundary probe reads the data root's series arm. Run from anywhere
    else, it fails before any temp dir or shim exists, and says how to proceed."""

    def test_missing_series_arm_names_the_fix(self):
        from fathom.smoke import RealProbes

        with tempfile.TemporaryDirectory() as td:
            probes = RealProbes(scenarios_dir=Path(td))
            with self.assertRaises(FileNotFoundError) as cm:
                probes.engine_spawn_argvs()
        self.assertIn("data root", str(cm.exception))
        self.assertIn("--no-engine-boundary", str(cm.exception))


def _fake_cli(argv, *, input, timeout, env, cwd):
    """A stand-in for the claude CLI, answering from the files its argv names.

    The init event lists ``<manifest name>:<skill dir>`` for each ``--plugin-dir``,
    and the reply carries the injection canary only when the file named by
    ``--append-system-prompt-file`` holds it, both read while the spawn runs.
    """
    argv = [str(a) for a in argv]
    skills = []
    for i, tok in enumerate(argv[:-1]):
        if tok == "--plugin-dir":
            root = Path(argv[i + 1])
            manifest = root / ".claude-plugin" / "plugin.json"
            name = json.loads(manifest.read_text(encoding="utf-8"))["name"]
            skills += [f"{name}:{d.name}" for d in sorted((root / "skills").iterdir())]
    reply = "hello"
    inject = injection_file_of(argv)
    if inject is not None and INJECTION_CANARY in Path(inject).read_text(encoding="utf-8"):
        reply += f"\n{INJECTION_CANARY}"
    events = [
        {"type": "system", "subtype": "init", "skills": skills},
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 1,
            "result": reply,
            "total_cost_usd": 0.001,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        },
    ]
    stdout = "".join(json.dumps(e) + "\n" for e in events)
    return subprocess.CompletedProcess(argv, 0, stdout, "")


class TestLiveSpawnsUseStagedCopies(unittest.TestCase):
    """The injection and mount spawns pass per-spawn copies, as a trial's spawn does.

    ``RealProbes`` with the subprocess boundary replaced by a stub CLI: the checks
    still find the flag and the canary, and the argv names the copies.
    """

    def setUp(self):
        from fathom import smoke

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.probes = smoke.RealProbes(real_config_dir=tmp.name, scenarios_dir=None)
        self.runners = []
        real_runner = smoke.ClaudeCliRunner

        def _recording_runner(**kwargs):
            runner = real_runner(**kwargs)
            self.runners.append(runner)
            return runner

        patches = [
            mock.patch("fathom.adapters.claude_cli._subprocess_spawn", _fake_cli),
            mock.patch.object(smoke, "ClaudeCliRunner", _recording_runner),
            mock.patch.dict(os.environ),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop("FATHOM_STREAM_DIR", None)

    def test_the_injection_spawn_passes_a_copy_of_the_body(self):
        argv, record = self.probes.injection_spawn()
        self.assertTrue(assert_injection_armed(argv, record).ok, (argv, record.result_text))
        (runner,) = self.runners
        self.assertTrue(runner.stage_files)
        self.assertNotEqual(Path(injection_file_of(argv)), Path(runner.append_system_prompt_file))

    def test_the_mount_spawns_pass_a_copy_of_the_canary(self):
        treatment = self.probes.mount_treatment_skills()
        control = self.probes.mount_control_skills()
        self.assertTrue(assert_canary_skill_mounted(treatment).ok, treatment)
        self.assertTrue(assert_canary_skill_absent(control).ok, control)
        self.assertEqual([r.stage_files for r in self.runners], [True, True])
        self.assertEqual(self.runners[0].plugin_dirs, (str(CANARY_PLUGIN_DIR),))

    def test_the_mount_spawn_names_no_declared_path(self):
        seen = []

        def _spy(argv, **kw):
            seen.append([str(a) for a in argv])
            return _fake_cli(argv, **kw)

        with mock.patch("fathom.adapters.claude_cli._subprocess_spawn", _spy):
            self.probes.mount_treatment_skills()
        self.assertIn("--plugin-dir", seen[0])
        self.assertNotIn(str(CANARY_PLUGIN_DIR), " ".join(seen[0]))


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
        # 11 checks when engine included: credential, concurrency, config, authed,
        # activity, deny, injection, memory, mount-treatment, mount-control, engine.
        _code, output = self._run(StubProbes())
        self.assertEqual(output.count("[PASS]"), 11, output)
        self.assertIn("(11/11 checks)", output)

    # -- The hollow checks, and the headline that hid them ---------------

    def test_a_dead_credential_refuses_before_anything_else(self):
        dead = _live_credential(
            at=_NOW_S,
            expires_at_ms=int((_NOW_S - 86400) * 1000),
            refresh_expires_at_ms=int((_NOW_S - 3600) * 1000),
        )
        code, output = self._run(StubProbes(credential=dead), now_s=_NOW_S)
        self.assertEqual(code, 1)
        self.assertIn("re-authenticate", output.lower())
        # Check 0: the credential verdict is available to everything after it.
        self.assertLess(output.index("credential"), output.index("isolated config"))

    def test_a_dead_spawn_does_not_let_the_two_liveness_checks_pass(self):
        """A dead spawn must not let the liveness checks pass."""
        dead_spawn = _ok_record(
            status=ExitStatus.INFRASTRUCTURE, num_turns=1, tokens_in=0, tokens_out=0
        )
        probes = StubProbes(authed=dead_spawn, deny=([], dead_spawn))
        code, output = self._run(probes)
        self.assertEqual(code, 1)
        self.assertIn("[SKIP] stream parsing detects activity", output)
        self.assertIn("[SKIP] disallowed tool refused under default-deny", output)
        self.assertNotIn("[PASS] stream parsing detects activity", output)
        self.assertNotIn("[PASS] disallowed tool refused under default-deny", output)

    def test_a_skipped_check_is_not_a_pass_in_the_headline(self):
        dead_spawn = _ok_record(
            status=ExitStatus.INFRASTRUCTURE, num_turns=1, tokens_in=0, tokens_out=0
        )
        _, output = self._run(StubProbes(authed=dead_spawn, deny=([], dead_spawn)), now_s=_NOW_S)
        summary = output.splitlines()[-1]
        self.assertNotIn("ALL PASS", summary)
        self.assertIn("skipped", summary.lower())

    def test_the_summary_line_names_what_was_not_proven(self):
        """The one line an operator reads carries what the fold above says."""
        probes = StubProbes(engine_argvs=[_good_argv("bypassPermissions")])
        _, output = self._run(probes)
        summary = output.splitlines()[-1]
        self.assertIn("engine-boundary", summary, summary)

    def test_credential_probe_exception_is_guarded(self):
        code, output = self._run(StubProbes(raise_on={"credential"}))
        self.assertEqual(code, 1)
        self.assertIn("credential boom", output)

    def test_force_fail_returns_one(self):
        code, output = self._run(StubProbes(), force_fail=True)
        self.assertEqual(
            code, 1, "force-fail must produce a nonzero exit even when all else passes"
        )
        summary = output.splitlines()[-1]
        self.assertNotIn("ALL PASS", summary)
        # The summary names the check, not just that something went wrong.
        self.assertIn("forced failure (--force-fail)", summary)

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
        self.assertEqual(output.count("[PASS]"), 10)

    def test_order_credential_config_authed_deny_injection_mount_engine(self):
        probes = StubProbes()
        self._run(probes)
        self.assertEqual(
            probes.calls,
            [
                "credential",
                "config",
                "authed",
                "deny",
                "injection",
                "memory",
                "mount_treatment",
                "mount_control",
                "engine",
            ],
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


class TestEngineBoundaryWithoutADataRoot(unittest.TestCase):
    """No data root resolved: the engine-boundary check says how to name one."""

    def test_it_names_every_way_forward(self):
        from fathom.smoke import RealProbes

        probes = RealProbes(scenarios_dir=None)
        with self.assertRaises(FileNotFoundError) as cm:
            probes.engine_spawn_argvs()
        message = str(cm.exception)
        for phrase in ("no data root", "--home", "FATHOM_HOME", "--no-engine-boundary"):
            self.assertIn(phrase, message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
