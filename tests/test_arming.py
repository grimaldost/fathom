"""Tests for fathom.arming — per-scenario arming VERIFICATION (FATH-B01).

The defect these tests exist for: fathom validated *declarations* (the inject file
exists, the mount dir is non-empty) and stopped there, so an entirely unarmed arm
scored 100% on 9 trials with ``smoke`` 8/8 and ``Infra Errors: 0``.  The
``serena-nav`` case is reproduced verbatim below (``MisarmedAllowlistTests``): a
plugin-mounted server's tools are named ``mcp__plugin_<plugin>_<server>__<tool>``
while the allow-list said ``mcp__serena``, so all 23 tools were denied.

Every check here is written so the UNARMED case fails.  A test that only asserts
the armed case passes would reproduce the original defect in the test suite.

Stdlib-only: ``python tests/test_arming.py`` runs without uv.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom import arming  # noqa: E402
from fathom.scenario import (  # noqa: E402
    ContextConfig,
    EnvConfig,
    LimitsOverride,
    PluginsConfig,
    ResolvedScenario,
    SettingsConfig,
    ToolsConfig,
)


def make_scenario(**kw) -> ResolvedScenario:
    base = dict(
        name="arm",
        adapter="claude-cli",
        model="claude-haiku-4-5",
        strategy="single-session",
        effort="low",
        tools=ToolsConfig(source="none", allowed=("Read",)),
        limits=LimitsOverride(trial_timeout_s=60),
        model_id=None,
        tool_repo_sha=None,
        tool_invocation_cmd=None,
        config_hash="0" * 64,
    )
    base.update(kw)
    return ResolvedScenario(**base)


def make_obs(**kw) -> arming.ArmingObservation:
    base = dict(
        spawn_ok=True,
        init_present=True,
        plugins=(),
        skills=(),
        tools=("Read", "Write"),
        mcp_servers=(),
        hooks_fired=(),
        successful_mcp_calls=(),
        denied_tools=(),
        argv=("claude", "-p"),
        spawn_env={},
        config_dir_files=(),
        settings_sha=None,
        detail="",
    )
    base.update(kw)
    return arming.ArmingObservation(**base)


# ---------------------------------------------------------------------------
# Which axes a scenario declares
# ---------------------------------------------------------------------------


class DeclaredAxesTests(unittest.TestCase):
    def test_a_plain_arm_declares_no_arming_axis(self) -> None:
        self.assertEqual(arming.declared_axes(make_scenario()), ())

    def test_each_treatment_block_declares_its_axis(self) -> None:
        sc = make_scenario(
            plugins=PluginsConfig(mount=("/p",)),
            settings=SettingsConfig(inject="/s.json"),
            env=EnvConfig(vars=(("PATH", "/x"),)),
            context=ContextConfig(inject="/c.md"),
        )
        self.assertEqual(set(arming.declared_axes(sc)), {"plugins", "settings", "env", "context"})

    def test_needs_verification_is_false_for_an_undeclared_arm(self) -> None:
        self.assertFalse(arming.needs_verification(make_scenario()))
        self.assertTrue(
            arming.needs_verification(make_scenario(plugins=PluginsConfig(mount=("/p",))))
        )


# ---------------------------------------------------------------------------
# Allow-list matching — the serena defect lives here
# ---------------------------------------------------------------------------


class AllowlistTests(unittest.TestCase):
    def test_exact_name_permits(self) -> None:
        self.assertTrue(arming.allowlist_permits("Read", ("Read",), ()))

    def test_server_prefix_rule_permits_its_tools(self) -> None:
        self.assertTrue(
            arming.allowlist_permits(
                "mcp__plugin_serena_serena__find_symbol",
                ("mcp__plugin_serena_serena",),
                (),
            )
        )

    def test_the_serena_spelling_does_not_permit(self) -> None:
        # The recorded defect: the allow-list said `mcp__serena`, the tools are
        # named `mcp__plugin_serena_serena__*`.  A prefix rule must NOT match on a
        # partial segment, or the check would bless the very run it exists to catch.
        self.assertFalse(
            arming.allowlist_permits("mcp__plugin_serena_serena__find_symbol", ("mcp__serena",), ())
        )

    def test_init_event_server_spelling_does_not_permit_either(self) -> None:
        # `plugin:serena:serena` is what the init event calls the server — copying
        # it into the allow-list also fails, which is why this is unguessable.
        self.assertFalse(
            arming.allowlist_permits(
                "mcp__plugin_serena_serena__find_symbol", ("plugin:serena:serena",), ()
            )
        )

    def test_disallow_wins_over_allow(self) -> None:
        self.assertFalse(
            arming.allowlist_permits("Bash", ("Bash",), ("Bash",)),
        )

    def test_wildcard_specifier_rule_permits(self) -> None:
        self.assertTrue(arming.allowlist_permits("Bash", ("Bash(python:*)",), ()))

    def test_empty_allowlist_permits_nothing(self) -> None:
        self.assertFalse(arming.allowlist_permits("Read", (), ()))


# ---------------------------------------------------------------------------
# The plugins axis
# ---------------------------------------------------------------------------


class PluginMountTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.mount = Path(self.tmp.name) / "serena"
        (self.mount / ".claude-plugin").mkdir(parents=True)
        (self.mount / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "serena", "version": "1.2.0"}), encoding="utf-8"
        )
        self.sc = make_scenario(plugins=PluginsConfig(mount=(str(self.mount),)))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_mounted_plugin_present_in_init_passes(self) -> None:
        obs = make_obs(plugins=({"name": "serena", "path": str(self.mount), "version": "1.2.0"},))
        checks = arming.verify_arming(self.sc, obs)
        reg = [c for c in checks if c.name == "plugins registered in the spawn"]
        self.assertTrue(reg and reg[0].ok, [c.detail for c in checks])

    def test_declared_mount_absent_from_init_FAILS(self) -> None:
        # The unarmed-arm case: the mount dir existed and was non-empty (which is
        # all the old declaration-time warning checked) but nothing registered.
        obs = make_obs(plugins=())
        checks = arming.verify_arming(self.sc, obs)
        self.assertFalse(arming.all_ok(checks))
        self.assertIn("serena", " ".join(c.detail for c in checks if not c.ok))

    def test_a_different_plugin_registering_does_not_satisfy_the_mount(self) -> None:
        obs = make_obs(plugins=({"name": "somethingelse", "path": "/x", "version": "1"},))
        self.assertFalse(arming.all_ok(arming.verify_arming(self.sc, obs)))


class MisarmedAllowlistTests(unittest.TestCase):
    """The recorded BLOCKER, reproduced: registered MCP tools, all of them denied."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.mount = Path(self.tmp.name) / "serena"
        (self.mount / ".claude-plugin").mkdir(parents=True)
        (self.mount / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "serena", "version": "1.2.0"}), encoding="utf-8"
        )
        self.registered = {
            "name": "serena",
            "path": str(self.mount),
            "version": "1.2.0",
        }
        self.mcp_tools = (
            "Read",
            "mcp__plugin_serena_serena__find_symbol",
            "mcp__plugin_serena_serena__list_dir",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _scenario(self, allowed: tuple[str, ...]) -> ResolvedScenario:
        return make_scenario(
            plugins=PluginsConfig(mount=(str(self.mount),)),
            tools=ToolsConfig(source="none", allowed=allowed),
        )

    def test_the_defect_run_FAILS_verification(self) -> None:
        sc = self._scenario(("Read", "mcp__serena"))
        obs = make_obs(
            plugins=(self.registered,),
            tools=self.mcp_tools,
            mcp_servers=({"name": "plugin:serena:serena", "status": "connected"},),
        )
        checks = arming.verify_arming(sc, obs)
        self.assertFalse(arming.all_ok(checks), "an all-tools-denied arm must not verify")
        bad = " ".join(c.detail for c in checks if not c.ok)
        self.assertIn("mcp__plugin_serena_serena__find_symbol", bad)

    def test_the_corrected_allowlist_PASSES(self) -> None:
        sc = self._scenario(("Read", "mcp__plugin_serena_serena"))
        obs = make_obs(
            plugins=(self.registered,),
            tools=self.mcp_tools,
            mcp_servers=({"name": "plugin:serena:serena", "status": "connected"},),
        )
        checks = arming.verify_arming(sc, obs)
        self.assertTrue(arming.all_ok(checks), [c for c in checks if not c.ok])

    def test_a_dead_mcp_server_FAILS_even_with_a_correct_allowlist(self) -> None:
        sc = self._scenario(("Read", "mcp__plugin_serena_serena"))
        obs = make_obs(
            plugins=(self.registered,),
            tools=("Read",),  # server never connected, so no tools registered
            mcp_servers=({"name": "plugin:serena:serena", "status": "failed"},),
        )
        self.assertFalse(arming.all_ok(arming.verify_arming(sc, obs)))

    def test_an_ambient_unhealthy_server_is_ignored(self) -> None:
        # Account-level connectors leak into the spawn's init event as `pending` /
        # `needs-auth`.  They are not the arm's treatment and must not fail its gate.
        sc = self._scenario(("Read", "mcp__plugin_serena_serena"))
        obs = make_obs(
            plugins=(self.registered,),
            tools=self.mcp_tools,
            mcp_servers=(
                {"name": "plugin:serena:serena", "status": "connected"},
                {"name": "claude.ai Gmail", "status": "needs-auth"},
            ),
        )
        self.assertTrue(arming.all_ok(arming.verify_arming(sc, obs)))


# ---------------------------------------------------------------------------
# The settings axis
# ---------------------------------------------------------------------------


class SettingsArmingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = Path(self.tmp.name) / "hooks.json"
        self.settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [{"hooks": [{"type": "command", "command": "echo hi"}]}]
                    }
                }
            ),
            encoding="utf-8",
        )
        self.sc = make_scenario(settings=SettingsConfig(inject=str(self.settings)))
        self.sha = arming.file_sha256(self.settings)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_settings_present_and_hook_fired_verifies(self) -> None:
        obs = make_obs(
            config_dir_files=(".credentials.json", "settings.json"),
            settings_sha=self.sha,
            hooks_fired=("SessionStart:startup",),
        )
        checks = arming.verify_arming(self.sc, obs)
        self.assertTrue(arming.all_ok(checks), [c for c in checks if not c.ok])
        self.assertTrue(any(c.level == "verified" for c in checks if c.axis == "settings"))

    def test_settings_never_reached_the_config_dir_FAILS(self) -> None:
        obs = make_obs(config_dir_files=(".credentials.json",), settings_sha=None)
        self.assertFalse(arming.all_ok(arming.verify_arming(self.sc, obs)))

    def test_a_different_settings_body_FAILS(self) -> None:
        obs = make_obs(
            config_dir_files=(".credentials.json", "settings.json"),
            settings_sha="deadbeef",
            hooks_fired=("SessionStart:startup",),
        )
        self.assertFalse(arming.all_ok(arming.verify_arming(self.sc, obs)))

    def test_a_declared_SessionStart_hook_that_never_fired_FAILS(self) -> None:
        # SessionStart always fires in a live spawn, so silence means the hook is
        # not wired — the exact silent degradation the settings axis exists to avoid.
        obs = make_obs(
            config_dir_files=(".credentials.json", "settings.json"),
            settings_sha=self.sha,
            hooks_fired=(),
        )
        self.assertFalse(arming.all_ok(arming.verify_arming(self.sc, obs)))

    def test_a_PreToolUse_only_hook_is_present_not_verified(self) -> None:
        # A PreToolUse hook cannot be provoked by the probe's single no-tool turn.
        # It reports PRESENT (file reached the live config dir) rather than a
        # green VERIFIED it did not earn.
        self.settings.write_text(
            json.dumps(
                {"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "x"}]}]}}
            ),
            encoding="utf-8",
        )
        sc = make_scenario(settings=SettingsConfig(inject=str(self.settings)))
        obs = make_obs(
            config_dir_files=(".credentials.json", "settings.json"),
            settings_sha=arming.file_sha256(self.settings),
            hooks_fired=(),
        )
        checks = arming.verify_arming(sc, obs)
        self.assertTrue(arming.all_ok(checks), [c for c in checks if not c.ok])
        self.assertTrue(all(c.level == "present" for c in checks if c.axis == "settings"))


# ---------------------------------------------------------------------------
# The env and context axes
# ---------------------------------------------------------------------------


class EnvArmingTests(unittest.TestCase):
    def test_declared_var_present_in_the_live_spawn_env_verifies(self) -> None:
        sc = make_scenario(env=EnvConfig(vars=(("FATHOM_MARK", "on"),)))
        obs = make_obs(spawn_env={"FATHOM_MARK": "on", "PATH": "/usr/bin"})
        self.assertTrue(arming.all_ok(arming.verify_arming(sc, obs)))

    def test_missing_var_FAILS(self) -> None:
        sc = make_scenario(env=EnvConfig(vars=(("FATHOM_MARK", "on"),)))
        self.assertFalse(arming.all_ok(arming.verify_arming(sc, make_obs(spawn_env={}))))

    def test_an_unsubstituted_template_FAILS(self) -> None:
        # `${workspace}` / `${PATH}` are substituted at spawn time; a literal
        # `${...}` surviving into the spawn env means substitution silently no-oped.
        sc = make_scenario(env=EnvConfig(vars=(("PATH", "/tools;${PATH}"),)))
        obs = make_obs(spawn_env={"PATH": "/tools;${PATH}"})
        self.assertFalse(arming.all_ok(arming.verify_arming(sc, obs)))

    def test_an_empty_value_FAILS(self) -> None:
        sc = make_scenario(env=EnvConfig(vars=(("FATHOM_MARK", "on"),)))
        self.assertFalse(
            arming.all_ok(arming.verify_arming(sc, make_obs(spawn_env={"FATHOM_MARK": ""})))
        )


class ContextArmingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.body = Path(self.tmp.name) / "skill.md"
        self.body.write_text("# a skill body\n", encoding="utf-8")
        self.sc = make_scenario(context=ContextConfig(inject=str(self.body)))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_flag_in_argv_pointing_at_a_non_empty_body_passes(self) -> None:
        obs = make_obs(argv=("claude", "--append-system-prompt-file", str(self.body), "-p"))
        self.assertTrue(arming.all_ok(arming.verify_arming(self.sc, obs)))

    def test_flag_missing_from_the_real_argv_FAILS(self) -> None:
        self.assertFalse(arming.all_ok(arming.verify_arming(self.sc, make_obs())))

    def test_an_empty_body_FAILS(self) -> None:
        self.body.write_text("", encoding="utf-8")
        obs = make_obs(argv=("claude", "--append-system-prompt-file", str(self.body), "-p"))
        self.assertFalse(arming.all_ok(arming.verify_arming(self.sc, obs)))

    def test_argv_pointing_at_a_different_file_FAILS(self) -> None:
        other = Path(self.tmp.name) / "other.md"
        other.write_text("x", encoding="utf-8")
        obs = make_obs(argv=("claude", "--append-system-prompt-file", str(other), "-p"))
        self.assertFalse(arming.all_ok(arming.verify_arming(self.sc, obs)))


# ---------------------------------------------------------------------------
# Whole-spawn failure modes
# ---------------------------------------------------------------------------


class ProbeFailureTests(unittest.TestCase):
    def test_a_failed_probe_spawn_FAILS_verification(self) -> None:
        sc = make_scenario(plugins=PluginsConfig(mount=("/p",)))
        obs = make_obs(spawn_ok=False, init_present=False, detail="auth expired")
        checks = arming.verify_arming(sc, obs)
        self.assertFalse(arming.all_ok(checks))

    def test_no_init_event_FAILS_verification(self) -> None:
        sc = make_scenario(plugins=PluginsConfig(mount=("/p",)))
        obs = make_obs(init_present=False)
        self.assertFalse(arming.all_ok(arming.verify_arming(sc, obs)))

    def test_an_undeclared_scenario_yields_no_checks_and_is_ok(self) -> None:
        checks = arming.verify_arming(make_scenario(), make_obs())
        self.assertEqual(checks, [])
        self.assertTrue(arming.all_ok(checks))


class VerifyAllTests(unittest.TestCase):
    """The gate ``fathom run`` calls before the first paid spawn."""

    class _Probe:
        def __init__(self, obs_by_name: dict) -> None:
            self.obs_by_name = obs_by_name
            self.calls: list[str] = []

        def observe(self, scenario):  # noqa: ANN001, ANN202
            self.calls.append(scenario.name)
            return self.obs_by_name[scenario.name]

    def test_an_all_unarmed_matrix_never_spawns_a_probe(self) -> None:
        probe = self._Probe({})
        ok, report = arming.verify_all([make_scenario(name="bare")], probe)
        self.assertTrue(ok)
        self.assertEqual(probe.calls, [], "an arm with no treatment must cost nothing to verify")

    def test_only_declaring_arms_are_probed(self) -> None:
        armed = make_scenario(name="armed", env=EnvConfig(vars=(("M", "1"),)))
        probe = self._Probe({"armed": make_obs(spawn_env={"M": "1"})})
        ok, _ = arming.verify_all([make_scenario(name="bare"), armed], probe)
        self.assertTrue(ok)
        self.assertEqual(probe.calls, ["armed"])

    def test_a_failing_arm_makes_the_whole_matrix_fail(self) -> None:
        armed = make_scenario(name="armed", env=EnvConfig(vars=(("M", "1"),)))
        probe = self._Probe({"armed": make_obs(spawn_env={})})
        ok, report = arming.verify_all([make_scenario(name="bare"), armed], probe)
        self.assertFalse(ok)
        self.assertIn("armed", report)
        self.assertIn("FAIL", report)

    def test_a_probe_that_raises_is_a_failure_not_a_crash(self) -> None:
        class _Boom:
            def observe(self, scenario):  # noqa: ANN001, ANN202
                raise RuntimeError("spawn exploded")

        armed = make_scenario(name="armed", env=EnvConfig(vars=(("M", "1"),)))
        ok, report = arming.verify_all([armed], _Boom())
        self.assertFalse(ok)
        self.assertIn("spawn exploded", report)


class ReportRenderingTests(unittest.TestCase):
    def test_render_marks_pass_and_fail(self) -> None:
        checks = [
            arming.ArmingCheck("plugins", "a", True, "d1", level="verified"),
            arming.ArmingCheck("env", "b", False, "d2"),
        ]
        text = arming.render_checks("arm", checks)
        self.assertIn("PASS", text)
        self.assertIn("FAIL", text)
        self.assertIn("d2", text)


if __name__ == "__main__":
    unittest.main()
