"""Tests for fathom.arming — per-scenario arming VERIFICATION.

The defect these tests exist for: fathom validated *declarations* (the inject file
exists, the mount dir is non-empty) and stopped there, so an entirely unarmed arm
scored as fully armed.  The allowlist mismatch case (``MisarmedAllowlistTests``)
tests a scenario where plugin-mounted server tools are named
``mcp__plugin_<plugin>_<server>__<tool>`` but the allow-list uses a different
prefix, so tools are unexpectedly denied.

Every check here is written so the UNARMED case fails.  A test that only asserts
the armed case passes would reproduce the original defect in the test suite.

Stdlib-only: ``python tests/test_arming.py`` runs without uv.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom import arming
from fathom.scenario import (
    ContextConfig,
    EnvConfig,
    LimitsOverride,
    PluginsConfig,
    ResolvedScenario,
    SettingsConfig,
    ToolsConfig,
)


def make_scenario(**kw) -> ResolvedScenario:
    base = {
        "name": "arm",
        "adapter": "claude-cli",
        "model": "claude-haiku-4-5",
        "strategy": "single-session",
        "effort": "low",
        "tools": ToolsConfig(source="none", allowed=("Read",)),
        "limits": LimitsOverride(trial_timeout_s=60),
        "model_id": None,
        "tool_repo_sha": None,
        "tool_invocation_cmd": None,
        "config_hash": "0" * 64,
    }
    base.update(kw)
    return ResolvedScenario(**base)


def make_obs(**kw) -> arming.ArmingObservation:
    base = {
        "spawn_ok": True,
        "init_present": True,
        "plugins": (),
        "skills": (),
        "tools": ("Read", "Write"),
        "mcp_servers": (),
        "hooks_fired": (),
        "successful_mcp_calls": (),
        "denied_tools": (),
        "argv": ("claude", "-p"),
        "spawn_env": {},
        "config_dir_files": (),
        "settings_sha": None,
        "detail": "",
    }
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
# Allow-list matching — a misspelled tool prefix is caught here
# ---------------------------------------------------------------------------


class AllowlistTests(unittest.TestCase):
    def test_exact_name_permits(self) -> None:
        self.assertTrue(arming.allowlist_permits("Read", ("Read",), ()))

    def test_server_prefix_rule_permits_its_tools(self) -> None:
        self.assertTrue(
            arming.allowlist_permits(
                "mcp__plugin_codenav_codenav__find_symbol",
                ("mcp__plugin_codenav_codenav",),
                (),
            )
        )

    def test_a_bare_plugin_spelling_does_not_permit(self) -> None:
        # The failure this guards: the allow-list says `mcp__codenav`, the tools are
        # named `mcp__plugin_codenav_codenav__*`.  A prefix rule must NOT match on a
        # partial segment, or the check would bless the very run it exists to catch.
        self.assertFalse(
            arming.allowlist_permits(
                "mcp__plugin_codenav_codenav__find_symbol", ("mcp__codenav",), ()
            )
        )

    def test_init_event_server_spelling_does_not_permit_either(self) -> None:
        # `plugin:codenav:codenav` is what the init event calls the server — copying
        # it into the allow-list also fails, which is why this is unguessable.
        self.assertFalse(
            arming.allowlist_permits(
                "mcp__plugin_codenav_codenav__find_symbol", ("plugin:codenav:codenav",), ()
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
        self.mount = Path(self.tmp.name) / "codenav"
        (self.mount / ".claude-plugin").mkdir(parents=True)
        (self.mount / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "codenav", "version": "1.2.0"}), encoding="utf-8"
        )
        self.sc = make_scenario(plugins=PluginsConfig(mount=(str(self.mount),)))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_mounted_plugin_present_in_init_passes(self) -> None:
        obs = make_obs(plugins=({"name": "codenav", "path": str(self.mount), "version": "1.2.0"},))
        checks = arming.verify_arming(self.sc, obs)
        reg = [c for c in checks if c.name == "plugins registered in the spawn"]
        self.assertTrue(reg and reg[0].ok, [c.detail for c in checks])

    def test_declared_mount_absent_from_init_FAILS(self) -> None:
        # The unarmed-arm case: the mount dir existed and was non-empty (which is
        # all the old declaration-time warning checked) but nothing registered.
        obs = make_obs(plugins=())
        checks = arming.verify_arming(self.sc, obs)
        self.assertFalse(arming.all_ok(checks))
        self.assertIn("codenav", " ".join(c.detail for c in checks if not c.ok))

    def test_a_different_plugin_registering_does_not_satisfy_the_mount(self) -> None:
        obs = make_obs(plugins=({"name": "somethingelse", "path": "/x", "version": "1"},))
        self.assertFalse(arming.all_ok(arming.verify_arming(self.sc, obs)))


class MisarmedAllowlistTests(unittest.TestCase):
    """The plugin is mounted and its server is up, but the allow-list denies every MCP
    tool it registers: the arm runs as the control, and verification must say so."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.mount = Path(self.tmp.name) / "codenav"
        (self.mount / ".claude-plugin").mkdir(parents=True)
        (self.mount / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "codenav", "version": "1.2.0"}), encoding="utf-8"
        )
        self.registered = {
            "name": "codenav",
            "path": str(self.mount),
            "version": "1.2.0",
        }
        self.mcp_tools = (
            "Read",
            "mcp__plugin_codenav_codenav__find_symbol",
            "mcp__plugin_codenav_codenav__list_dir",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _scenario(self, allowed: tuple[str, ...]) -> ResolvedScenario:
        return make_scenario(
            plugins=PluginsConfig(mount=(str(self.mount),)),
            tools=ToolsConfig(source="none", allowed=allowed),
        )

    def test_an_allowlist_that_denies_every_mcp_tool_FAILS(self) -> None:
        sc = self._scenario(("Read", "mcp__codenav"))
        obs = make_obs(
            plugins=(self.registered,),
            tools=self.mcp_tools,
            mcp_servers=({"name": "plugin:codenav:codenav", "status": "connected"},),
        )
        checks = arming.verify_arming(sc, obs)
        self.assertFalse(arming.all_ok(checks), "an all-tools-denied arm must not verify")
        bad = " ".join(c.detail for c in checks if not c.ok)
        self.assertIn("mcp__plugin_codenav_codenav__find_symbol", bad)

    def test_the_corrected_allowlist_PASSES(self) -> None:
        sc = self._scenario(("Read", "mcp__plugin_codenav_codenav"))
        obs = make_obs(
            plugins=(self.registered,),
            tools=self.mcp_tools,
            mcp_servers=({"name": "plugin:codenav:codenav", "status": "connected"},),
        )
        checks = arming.verify_arming(sc, obs)
        self.assertTrue(arming.all_ok(checks), [c for c in checks if not c.ok])

    def test_a_dead_mcp_server_FAILS_even_with_a_correct_allowlist(self) -> None:
        sc = self._scenario(("Read", "mcp__plugin_codenav_codenav"))
        obs = make_obs(
            plugins=(self.registered,),
            tools=("Read",),  # server never connected, so no tools registered
            mcp_servers=({"name": "plugin:codenav:codenav", "status": "failed"},),
        )
        self.assertFalse(arming.all_ok(arming.verify_arming(sc, obs)))

    def test_ambient_mcp_tools_are_not_charged_to_the_arm(self) -> None:
        # Account-level connectors can leak into the isolated spawn and register
        # their own mcp__* tools.  They are not the arm's treatment, and default-deny
        # already refuses them — failing a skills-only plugin arm because an unrelated
        # connector is unreachable would be a false positive that trains the operator
        # to pass --force.
        sc = self._scenario(("Read", "Write"))
        obs = make_obs(
            plugins=(self.registered,),
            tools=("Read", "mcp__claude_ai_Docs__query-docs"),
            mcp_servers=({"name": "claude.ai Docs", "status": "pending"},),
        )
        checks = arming.verify_arming(sc, obs)
        self.assertTrue(arming.all_ok(checks), [c.detail for c in checks if not c.ok])

    def test_a_mount_serving_a_server_that_registers_no_tools_FAILS(self) -> None:
        sc = self._scenario(("Read", "mcp__plugin_codenav_codenav"))
        obs = make_obs(
            plugins=(self.registered,),
            # An ambient connector's tools are present; the arm's own are not.
            tools=("Read", "mcp__claude_ai_Docs__query-docs"),
            mcp_servers=(
                {"name": "plugin:codenav:codenav", "status": "connected"},
                {"name": "claude.ai Docs", "status": "pending"},
            ),
        )
        self.assertFalse(arming.all_ok(arming.verify_arming(sc, obs)))

    def test_server_tool_prefix_matches_the_observed_spelling(self) -> None:
        self.assertEqual(
            arming.server_tool_prefix("plugin:codenav:codenav"), "mcp__plugin_codenav_codenav"
        )
        self.assertEqual(arming.server_tool_prefix("claude.ai Docs"), "mcp__claude_ai_Docs")

    def test_an_ambient_unhealthy_server_is_ignored(self) -> None:
        # Account-level connectors leak into the spawn's init event as `pending` /
        # `needs-auth`.  They are not the arm's treatment and must not fail its gate.
        sc = self._scenario(("Read", "mcp__plugin_codenav_codenav"))
        obs = make_obs(
            plugins=(self.registered,),
            tools=self.mcp_tools,
            mcp_servers=(
                {"name": "plugin:codenav:codenav", "status": "connected"},
                {"name": "claude.ai Mail", "status": "needs-auth"},
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
    """The spawn reads a copy of the body, as a trial's does, so content is compared."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.body = Path(self.tmp.name) / "skill.md"
        self.body.write_text("# a skill body\n", encoding="utf-8")
        self.sc = make_scenario(context=ContextConfig(inject=str(self.body)))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _spawned_with(path: Path) -> arming.ArmingObservation:
        """What the probe records: the argv names *path*, read while the spawn ran."""
        return make_obs(
            argv=("claude", "--append-system-prompt-file", str(path), "-p"),
            context_sha=arming.file_sha256(path),
        )

    def test_a_copy_of_the_non_empty_body_passes(self) -> None:
        copy = Path(self.tmp.name) / "stage" / "context.md"
        copy.parent.mkdir()
        copy.write_bytes(self.body.read_bytes())
        checks = arming.verify_arming(self.sc, self._spawned_with(copy))
        self.assertTrue(arming.all_ok(checks), [c.detail for c in checks])
        self.assertEqual(checks[0].level, "verified")

    def test_flag_missing_from_the_real_argv_FAILS(self) -> None:
        self.assertFalse(arming.all_ok(arming.verify_arming(self.sc, make_obs())))

    def test_an_empty_body_FAILS(self) -> None:
        self.body.write_text("", encoding="utf-8")
        obs = self._spawned_with(self.body)
        self.assertFalse(arming.all_ok(arming.verify_arming(self.sc, obs)))

    def test_a_file_with_different_content_FAILS(self) -> None:
        other = Path(self.tmp.name) / "other.md"
        other.write_text("x", encoding="utf-8")
        checks = arming.verify_arming(self.sc, self._spawned_with(other))
        self.assertFalse(arming.all_ok(checks))
        self.assertIn("DIFFERENT content", checks[0].detail)

    def test_the_declared_path_without_its_content_FAILS(self) -> None:
        # The argv naming the declared file proves nothing on its own: the file the
        # spawn met could not be read while it ran.
        obs = make_obs(argv=("claude", "--append-system-prompt-file", str(self.body), "-p"))
        checks = arming.verify_arming(self.sc, obs)
        self.assertFalse(arming.all_ok(checks))
        self.assertIn("could not be read", checks[0].detail)


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


# ---------------------------------------------------------------------------
# The probe spawns the way a trial does: from per-spawn copies of the arm's files
# ---------------------------------------------------------------------------


def _fake_cli(argv, *, input, timeout, env, cwd):  # type: ignore[no-untyped-def]
    """A stand-in for the claude CLI's init event, read from the argv it is given.

    Each ``--plugin-dir`` registers under its manifest name, or its directory name
    without one, and each server in its ``.mcp.json`` connects only when its command,
    with ``${CLAUDE_PLUGIN_ROOT}`` replaced by that directory, is a file there. So a
    plugin whose server lives in its ``.venv`` connects from its declared directory
    and fails from a copy that left the ``.venv`` out, as it would in a real spawn.
    """
    argv = [str(a) for a in argv]
    plugins, servers, tools = [], [], ["Read"]
    for i, tok in enumerate(argv[:-1]):
        if tok != "--plugin-dir":
            continue
        root = Path(argv[i + 1])
        name = arming.plugin_name_of(str(root)) or root.name
        plugins.append({"name": name, "path": str(root)})
        mcp = root / ".mcp.json"
        if not mcp.is_file():
            continue
        for server, spec in json.loads(mcp.read_text(encoding="utf-8"))["mcpServers"].items():
            command = spec["command"].replace("${CLAUDE_PLUGIN_ROOT}", str(root))
            up = Path(command).is_file()
            servers.append(
                {"name": f"plugin:{name}:{server}", "status": "connected" if up else "failed"}
            )
            if up:
                tools.append(f"mcp__plugin_{name}_{server}__find")
    events = [
        {
            "type": "system",
            "subtype": "init",
            "tools": tools,
            "skills": [],
            "plugins": plugins,
            "mcp_servers": servers,
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 1,
            "result": "ok",
            "total_cost_usd": 0.001,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        },
    ]
    stdout = "".join(json.dumps(e) + "\n" for e in events)
    return subprocess.CompletedProcess(argv, 0, stdout, "")


class ProbeSpawnsFromCopiesTests(unittest.TestCase):
    """``RealArmingProbe`` with a stub spawn: what it proves is what a trial runs.

    A trial's spawn gets copies of the arm's files that leave out ``.git``, ``.venv``,
    ``__pycache__`` and Claude Code's cache markers. A probe of the declared files
    passes a plugin that needs one of those, and every trial then runs unarmed.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "data-root"
        self.root.mkdir()
        self.config = Path(self.tmp.name) / "config"  # no credential: nothing to copy
        self.config.mkdir()
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("FATHOM_STREAM_DIR", None)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _plugin(self, dirname: str, *, name: str | None, server_path: str) -> Path:
        mount = self.root / dirname
        (mount / ".claude-plugin").mkdir(parents=True)
        manifest = {"name": name} if name else {}
        (mount / ".claude-plugin" / "plugin.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        (mount / ".mcp.json").write_text(
            json.dumps(
                {"mcpServers": {"srv": {"command": "${CLAUDE_PLUGIN_ROOT}/" + server_path}}}
            ),
            encoding="utf-8",
        )
        server = mount / server_path
        server.parent.mkdir(parents=True, exist_ok=True)
        server.write_text("server", encoding="utf-8")
        return mount

    def _observe(self, sc: ResolvedScenario) -> arming.ArmingObservation:
        from fathom.armingprobe import RealArmingProbe

        probe = RealArmingProbe(real_config_dir=str(self.config), spawn=_fake_cli)
        obs = probe.observe(sc)
        self.assertTrue(obs.spawn_ok, obs.detail)
        self.assertNotIn(str(self.root), " ".join(obs.argv), "the probe named a declared path")
        return obs

    def _plugin_arm(self, mount: Path, plugin: str) -> ResolvedScenario:
        return make_scenario(
            plugins=PluginsConfig(mount=(str(mount),)),
            tools=ToolsConfig(source="none", allowed=("Read", f"mcp__plugin_{plugin}_srv")),
        )

    def test_a_plugin_that_needs_its_venv_is_reported_unarmed(self) -> None:
        mount = self._plugin("venvplug", name="venvplug", server_path=".venv/bin/server")
        sc = self._plugin_arm(mount, "venvplug")
        checks = arming.verify_arming(sc, self._observe(sc))
        self.assertFalse(arming.all_ok(checks), [c.detail for c in checks])
        failed = " ".join(c.detail for c in checks if not c.ok)
        self.assertIn("failed", failed)
        self.assertIn(".venv", failed, "the report should say what the copy left out")

    def test_an_unnamed_plugin_that_needs_its_venv_is_reported_unarmed(self) -> None:
        # Without a manifest name the plugin is known by its directory's name, which
        # its copy keeps; its server must still be charged to it.
        mount = self._plugin("bareplug", name=None, server_path=".venv/bin/server")
        sc = self._plugin_arm(mount, "bareplug")
        self.assertFalse(arming.all_ok(arming.verify_arming(sc, self._observe(sc))))

    def test_a_normal_plugin_arm_is_armed(self) -> None:
        mount = self._plugin("goodplug", name="goodplug", server_path="server.py")
        sc = self._plugin_arm(mount, "goodplug")
        checks = arming.verify_arming(sc, self._observe(sc))
        self.assertTrue(arming.all_ok(checks), [c.detail for c in checks if not c.ok])
        self.assertTrue(all(c.level == "verified" for c in checks))

    def test_an_unnamed_plugin_is_matched_through_its_copy(self) -> None:
        # Its copy's path is all the init event gives: the i-th --plugin-dir is the
        # copy of the i-th mount.
        mount = self._plugin("bareplug", name=None, server_path="server.py")
        sc = self._plugin_arm(mount, "bareplug")
        checks = arming.verify_arming(sc, self._observe(sc))
        self.assertTrue(arming.all_ok(checks), [c.detail for c in checks if not c.ok])

    def test_a_context_arm_is_armed_through_the_staged_copy(self) -> None:
        body = self.root / "arm-body.md"
        body.write_text("# a skill body\n", encoding="utf-8")
        sc = make_scenario(context=ContextConfig(inject=str(body)))
        obs = self._observe(sc)
        in_argv = obs.argv[obs.argv.index("--append-system-prompt-file") + 1]
        self.assertNotEqual(Path(in_argv), body)
        self.assertFalse(Path(in_argv).exists(), "the copy outlived the spawn")
        self.assertEqual(obs.context_sha, arming.file_sha256(body))
        checks = arming.verify_arming(sc, obs)
        self.assertTrue(arming.all_ok(checks), [c.detail for c in checks])


class PluginCopyPairingTests(unittest.TestCase):
    """A copy's path is paired with a mount only when the counts agree."""

    def test_an_unpaired_copy_is_not_charged_to_a_mount(self) -> None:
        # One unnamed mount, two --plugin-dir values: which one is its copy cannot be
        # told, so the registered first one does not stand in for it.
        with tempfile.TemporaryDirectory() as tmp:
            mount = Path(tmp) / "a"
            mount.mkdir()
            sc = make_scenario(plugins=PluginsConfig(mount=(str(mount),)))
            other = str(Path(tmp) / "stage" / "x")
            obs = make_obs(
                argv=("claude", "--plugin-dir", other, "--plugin-dir", str(Path(tmp) / "y")),
                plugins=({"name": "x", "path": other},),
            )
            self.assertFalse(arming.all_ok(arming.verify_arming(sc, obs)))

    def test_a_paired_copy_stands_in_for_its_mount(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mount = Path(tmp) / "a"
            mount.mkdir()
            sc = make_scenario(plugins=PluginsConfig(mount=(str(mount),)))
            copy = str(Path(tmp) / "stage" / "a")
            obs = make_obs(
                argv=("claude", "--plugin-dir", copy),
                plugins=({"name": "a", "path": copy},),
            )
            self.assertTrue(arming.all_ok(arming.verify_arming(sc, obs)))


class VerifyAllTests(unittest.TestCase):
    """The gate ``fathom run`` calls before the first paid spawn."""

    class _Probe:
        def __init__(self, obs_by_name: dict) -> None:
            self.obs_by_name = obs_by_name
            self.calls: list[str] = []

        def observe(self, scenario):
            self.calls.append(scenario.name)
            return self.obs_by_name[scenario.name]

    def test_an_all_unarmed_matrix_never_spawns_a_probe(self) -> None:
        probe = self._Probe({})
        ok, _report = arming.verify_all([make_scenario(name="bare")], probe)
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
            def observe(self, scenario):
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
