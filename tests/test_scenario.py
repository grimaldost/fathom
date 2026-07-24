"""Tests for src/fathom/scenario.py — stdlib-runnable.

Run directly:  python tests/test_scenario.py
Run via pytest: uv run pytest tests/test_scenario.py
"""

import sys
import unittest
from pathlib import Path

# Allow direct stdlib invocation without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.scenario import (
    LimitsOverride,
    PluginsConfig,
    ResolvedScenario,
    ScenarioConfig,
    SettingsConfig,
    ToolsConfig,
    compute_config_hash,
    load_scenario,
    resolve_scenario,
)

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


# ---------------------------------------------------------------------------
# Stub resolver — deterministic, no real git / CLI calls.
# ---------------------------------------------------------------------------


class StubResolver:
    """Minimal in-test resolver that never touches the filesystem."""

    STUB_SHA = "abc123def456abc123def456abc12345"
    STUB_PLUGIN_META = ("stub-plugin", "0.0.0", "aabbcc112233aabbcc112233aabbcc11")

    def resolve_model_id(self, model: str) -> str | None:
        return model + "-20251001"

    def resolve_tool_repo_sha(self, repo: str) -> str:
        return self.STUB_SHA

    def build_tool_invocation_cmd(self, repo: str) -> str:
        return f"uv run --project {repo} convoy"

    def resolve_plugin_meta(self, plugin_dir: str) -> tuple[str, str, str]:
        return self.STUB_PLUGIN_META


STUB = StubResolver()


# ---------------------------------------------------------------------------
# TestComputeConfigHash — hash function properties
# ---------------------------------------------------------------------------


class TestComputeConfigHash(unittest.TestCase):
    def test_flat_key_order_insensitive(self):
        """Sort-keys canonicalization makes flat dict order irrelevant."""
        d1 = {"a": "first", "b": "second", "z": "last"}
        d2 = {"z": "last", "a": "first", "b": "second"}
        self.assertEqual(compute_config_hash(d1), compute_config_hash(d2))

    def test_nested_key_order_insensitive(self):
        """sort_keys=True recurses into nested dicts."""
        d1 = {"outer": {"x": 1, "y": 2}}
        d2 = {"outer": {"y": 2, "x": 1}}
        self.assertEqual(compute_config_hash(d1), compute_config_hash(d2))

    def test_changes_when_value_changes(self):
        d1 = {"key": "value_a"}
        d2 = {"key": "value_b"}
        self.assertNotEqual(compute_config_hash(d1), compute_config_hash(d2))

    def test_none_value_distinct_from_string(self):
        d1 = {"key": None}
        d2 = {"key": "null"}
        self.assertNotEqual(compute_config_hash(d1), compute_config_hash(d2))

    def test_returns_64_char_hex_string(self):
        result = compute_config_hash({"k": "v"})
        self.assertEqual(len(result), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in result))


# ---------------------------------------------------------------------------
# TestResolveScenario — resolver behaviour and hash pin sensitivity
# ---------------------------------------------------------------------------


class TestResolveScenario(unittest.TestCase):
    def _config(self, **overrides) -> ScenarioConfig:
        defaults = dict(
            name="test",
            adapter="claude-cli",
            model="claude-opus-4-8",
            strategy="single-session",
            effort="high",
            tools=ToolsConfig(source="none"),
            limits=LimitsOverride(),
        )
        defaults.update(overrides)
        return ScenarioConfig(**defaults)

    def test_stable_hash_for_identical_inputs(self):
        """Resolving the same config twice yields the same hash."""
        config = self._config()
        r1 = resolve_scenario(config, STUB)
        r2 = resolve_scenario(config, STUB)
        self.assertEqual(r1.config_hash, r2.config_hash)

    def test_hash_changes_when_model_id_changes(self):
        config = self._config()

        class AltModel:
            def resolve_model_id(self, model: str) -> str | None:
                return "completely-different-model-id"

            def resolve_tool_repo_sha(self, repo: str) -> str:
                return StubResolver.STUB_SHA

            def build_tool_invocation_cmd(self, repo: str) -> str:
                return f"uv run --project {repo} convoy"

        r1 = resolve_scenario(config, STUB)
        r2 = resolve_scenario(config, AltModel())
        self.assertNotEqual(r1.config_hash, r2.config_hash)

    def test_hash_changes_when_invocation_cmd_changes(self):
        config = self._config(
            strategy="series",
            tools=ToolsConfig(source="repo", repo="/some/path"),
        )

        class AltCmd:
            def resolve_model_id(self, model: str) -> str | None:
                return model + "-20251001"

            def resolve_tool_repo_sha(self, repo: str) -> str:
                return StubResolver.STUB_SHA

            def build_tool_invocation_cmd(self, repo: str) -> str:
                return f"DIFFERENT_CMD {repo}"

        r1 = resolve_scenario(config, STUB)
        r2 = resolve_scenario(config, AltCmd())
        self.assertNotEqual(r1.config_hash, r2.config_hash)

    def test_hash_changes_when_tool_sha_changes(self):
        config = self._config(
            strategy="series",
            tools=ToolsConfig(source="repo", repo="/some/path"),
        )

        class AltSha:
            def resolve_model_id(self, model: str) -> str | None:
                return model + "-20251001"

            def resolve_tool_repo_sha(self, repo: str) -> str:
                return "deadbeefdeadbeefdeadbeefdeadbeef"

            def build_tool_invocation_cmd(self, repo: str) -> str:
                return f"uv run --project {repo} convoy"

        r1 = resolve_scenario(config, STUB)
        r2 = resolve_scenario(config, AltSha())
        self.assertNotEqual(r1.config_hash, r2.config_hash)

    def test_none_tools_yields_no_pins(self):
        """source=none scenarios produce no invocation cmd or SHA."""
        resolved = resolve_scenario(self._config(), STUB)
        self.assertIsNone(resolved.tool_invocation_cmd)
        self.assertIsNone(resolved.tool_repo_sha)

    def test_repo_tools_yields_invocation_cmd_and_sha(self):
        config = self._config(tools=ToolsConfig(source="repo", repo="/tools/repo"))
        resolved = resolve_scenario(config, STUB)
        self.assertIsNotNone(resolved.tool_invocation_cmd)
        self.assertIsNotNone(resolved.tool_repo_sha)
        self.assertIn("uv run --project", resolved.tool_invocation_cmd)

    def test_config_hash_is_64_char_hex(self):
        resolved = resolve_scenario(self._config(), STUB)
        self.assertEqual(len(resolved.config_hash), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in resolved.config_hash))

    def test_returned_type_is_resolved_scenario(self):
        resolved = resolve_scenario(self._config(), STUB)
        self.assertIsInstance(resolved, ResolvedScenario)


# ---------------------------------------------------------------------------
# TestRepoInvocationCmd — the engine invocation command must be cwd-independent.
# Regression guard for the series-arm F1 bug: the engine runs with cwd=trial
# workspace (a temp dir), so a relative [tools].repo baked verbatim into
# `uv run --project <rel> convoy` fails to resolve there. resolve_repo_invocation_cmd
# freezes the repo to an absolute, forward-slash path at resolution time.
# ---------------------------------------------------------------------------


class TestRepoInvocationCmd(unittest.TestCase):
    def _project_arg(self, cmd: str) -> str:
        parts = cmd.split()
        return parts[parts.index("--project") + 1]

    def test_relative_repo_frozen_to_absolute(self):
        from fathom.scenario import resolve_repo_invocation_cmd

        cmd = resolve_repo_invocation_cmd("../convoy")
        proj = self._project_arg(cmd)
        self.assertTrue(Path(proj).is_absolute(), f"project path not absolute: {proj!r}")
        self.assertNotIn("..", cmd)  # the raw relative token is gone
        self.assertEqual(proj, str(Path("../convoy").resolve()).replace("\\", "/"))

    def test_forward_slash_normalized(self):
        from fathom.scenario import resolve_repo_invocation_cmd

        cmd = resolve_repo_invocation_cmd(str(Path.cwd()))
        self.assertNotIn("\\", cmd)  # config_hash stability across separators

    def test_real_resolvers_delegate_to_helper(self):
        """Both real resolvers must produce the same cwd-independent command,
        so the series arm works from cli.py and from the smoke gate identically."""
        from fathom.cli import _DefaultResolver
        from fathom.scenario import resolve_repo_invocation_cmd
        from fathom.smoke import _DefaultSmokeResolver

        expected = resolve_repo_invocation_cmd("../convoy")
        self.assertEqual(_DefaultResolver().build_tool_invocation_cmd("../convoy"), expected)
        self.assertEqual(_DefaultSmokeResolver().build_tool_invocation_cmd("../convoy"), expected)


# ---------------------------------------------------------------------------
# TestLoadScenario — TOML parsing (no resolution)
# ---------------------------------------------------------------------------


class TestLoadScenario(unittest.TestCase):
    def test_load_bare_fields(self):
        config = load_scenario(SCENARIOS_DIR / "bare.toml")
        self.assertEqual(config.name, "bare")
        self.assertIsInstance(config.adapter, str)
        self.assertIsInstance(config.model, str)
        self.assertIsInstance(config.strategy, str)
        self.assertIsInstance(config.effort, str)
        self.assertIsInstance(config.tools, ToolsConfig)
        self.assertIsInstance(config.limits, LimitsOverride)

    def test_load_does_not_produce_resolved_fields(self):
        """load_scenario must not call the resolver; no pins on ScenarioConfig."""
        config = load_scenario(SCENARIOS_DIR / "bare.toml")
        self.assertFalse(hasattr(config, "model_id"))
        self.assertFalse(hasattr(config, "tool_repo_sha"))
        self.assertFalse(hasattr(config, "tool_invocation_cmd"))
        self.assertFalse(hasattr(config, "config_hash"))

    def test_load_returns_scenario_config(self):
        config = load_scenario(SCENARIOS_DIR / "bare.toml")
        self.assertIsInstance(config, ScenarioConfig)


# ---------------------------------------------------------------------------
# TestThreeScenarios — the three committed files + cross-file assertions
# ---------------------------------------------------------------------------


class TestThreeScenarios(unittest.TestCase):
    def _lr(self, filename: str):
        """Load and resolve a scenario file using the stub resolver."""
        path = SCENARIOS_DIR / filename
        config = load_scenario(path)
        return config, resolve_scenario(config, STUB)

    def test_bare_parses_and_resolves(self):
        config, resolved = self._lr("bare.toml")
        self.assertEqual(config.name, "bare")
        self.assertIsNotNone(resolved.config_hash)
        self.assertEqual(config.tools.source, "none")
        self.assertIsNone(resolved.tool_invocation_cmd)
        self.assertIsNone(resolved.tool_repo_sha)

    def test_single_long_session_parses_and_resolves(self):
        config, resolved = self._lr("single-long-session.toml")
        self.assertEqual(config.name, "single-long-session")
        self.assertIsNotNone(resolved.config_hash)
        self.assertIsNone(resolved.tool_invocation_cmd)
        self.assertIsNone(resolved.tool_repo_sha)

    def test_series_parses_and_resolves(self):
        config, resolved = self._lr("series.toml")
        self.assertEqual(config.name, "series")
        self.assertIsNotNone(resolved.config_hash)
        self.assertIsNotNone(resolved.tool_invocation_cmd)
        self.assertIsNotNone(resolved.tool_repo_sha)

    def test_equal_effort_across_all_three(self):
        """All three scenarios must declare the same effort for cross-arm parity."""
        bare_cfg, _ = self._lr("bare.toml")
        sls_cfg, _ = self._lr("single-long-session.toml")
        series_cfg, _ = self._lr("series.toml")
        self.assertEqual(bare_cfg.effort, sls_cfg.effort)
        self.assertEqual(sls_cfg.effort, series_cfg.effort)

    def test_series_has_larger_trial_timeout_than_bare(self):
        """Series scenario must carry a larger trial-timeout override."""
        bare_cfg, _ = self._lr("bare.toml")
        series_cfg, _ = self._lr("series.toml")
        self.assertIsNotNone(series_cfg.limits.trial_timeout_s)
        self.assertIsNotNone(bare_cfg.limits.trial_timeout_s)
        self.assertGreater(series_cfg.limits.trial_timeout_s, bare_cfg.limits.trial_timeout_s)

    def test_series_repo_points_to_convoy(self):
        config, _ = self._lr("series.toml")
        self.assertEqual(config.tools.source, "repo")
        self.assertIsNotNone(config.tools.repo)
        self.assertIn("convoy", config.tools.repo)

    def test_series_invocation_cmd_uses_uv_run_project(self):
        """Must be explicit uv run --project <repo> convoy, not a bare PATH lookup."""
        config, resolved = self._lr("series.toml")
        cmd = resolved.tool_invocation_cmd
        self.assertIn("uv run --project", cmd)
        self.assertIn("convoy", cmd)
        self.assertNotEqual(cmd.strip(), "convoy")
        self.assertTrue(cmd.startswith("uv "), msg=f"bare PATH lookup: {cmd!r}")

    def test_series_invocation_cmd_contains_repo_path(self):
        config, resolved = self._lr("series.toml")
        # The repo path from the TOML must appear in the invocation command.
        self.assertIn(config.tools.repo, resolved.tool_invocation_cmd)

    def test_all_three_have_unique_config_hashes(self):
        """Different scenarios must produce different config hashes."""
        _, r_bare = self._lr("bare.toml")
        _, r_sls = self._lr("single-long-session.toml")
        _, r_series = self._lr("series.toml")
        hashes = {r_bare.config_hash, r_sls.config_hash, r_series.config_hash}
        self.assertEqual(len(hashes), 3, "Expected 3 distinct hashes")


class TestToolAllowlists(unittest.TestCase):
    """Regression: matrix run 1 was invalidated because single-session arms
    spawned with an empty allowlist under default-deny (unarmed agents).
    The scenario schema must carry explicit allow/disallow lists (spec §5),
    hash them when set, and keep hashes stable for scenarios that never set
    them (resume-key compatibility)."""

    def _write(self, tmp: Path, tools_block: str) -> Path:
        p = tmp / "s.toml"
        p.write_text(
            'name = "s"\n'
            'adapter = "claude-cli"\n'
            'model = "m"\n'
            'strategy = "single-session"\n'
            'effort = "high"\n'
            f"{tools_block}\n",
            encoding="utf-8",
        )
        return p

    def test_allowed_and_disallowed_parsed_as_tuples(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = self._write(
                Path(td),
                '[tools]\nsource = "none"\nallowed = ["Read", "Write"]\ndisallowed = ["WebSearch"]',
            )
            cfg = load_scenario(p)
            self.assertEqual(cfg.tools.allowed, ("Read", "Write"))
            self.assertEqual(cfg.tools.disallowed, ("WebSearch",))

    def test_absent_and_empty_allowlist_hash_identically(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            r = StubResolver()
            absent = resolve_scenario(
                load_scenario(self._write(tmp, '[tools]\nsource = "none"')), r
            )
            empty = resolve_scenario(
                load_scenario(self._write(tmp, '[tools]\nsource = "none"\nallowed = []')), r
            )
            self.assertEqual(absent.config_hash, empty.config_hash)

    def test_setting_allowlist_changes_hash(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            r = StubResolver()
            without = resolve_scenario(
                load_scenario(self._write(tmp, '[tools]\nsource = "none"')), r
            )
            armed = resolve_scenario(
                load_scenario(self._write(tmp, '[tools]\nsource = "none"\nallowed = ["Read"]')), r
            )
            self.assertNotEqual(without.config_hash, armed.config_hash)

    def test_committed_single_arms_are_armed_and_equal(self):
        """Both single-spawn scenario files must grant write capability and
        identical allowlists (the arm distinction is strategy, not tools)."""
        bare = load_scenario(SCENARIOS_DIR / "bare.toml")
        sls = load_scenario(SCENARIOS_DIR / "single-long-session.toml")
        for cfg in (bare, sls):
            self.assertTrue(cfg.tools.allowed, f"{cfg.name}: empty allowlist (unarmed arm)")
            self.assertIn("Write", cfg.tools.allowed, f"{cfg.name}: no Write tool")
            self.assertIn("Edit", cfg.tools.allowed, f"{cfg.name}: no Edit tool")
        self.assertEqual(bare.tools.allowed, sls.tools.allowed)


class TestContextInjection(unittest.TestCase):
    """The [context] inject field: a treatment scenario appends a file's body to
    the spawn's system prompt. Absent inject == no context (hash-stable vs any
    committed ledger); the *content* (sha256), not the path, enters the
    hash so editing the body forks history but moving the file does not."""

    def _write(self, tmp: Path, context_block: str) -> Path:
        p = tmp / "s.toml"
        p.write_text(
            'name = "s"\n'
            'adapter = "claude-cli"\n'
            'model = "m"\n'
            'strategy = "single-session"\n'
            'effort = "high"\n'
            '[tools]\nsource = "none"\nallowed = ["Read"]\n'
            f"{context_block}\n",
            encoding="utf-8",
        )
        return p

    def test_absent_and_no_inject_hash_identically(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            r = StubResolver()
            absent = resolve_scenario(load_scenario(self._write(tmp, "")), r)
            empty_ctx = resolve_scenario(load_scenario(self._write(tmp, "[context]")), r)
            self.assertEqual(absent.config_hash, empty_ctx.config_hash)

    def test_setting_inject_changes_hash(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "skill.md").write_text("BODY A", encoding="utf-8")
            r = StubResolver()
            without = resolve_scenario(load_scenario(self._write(tmp, "")), r)
            armed = resolve_scenario(
                load_scenario(self._write(tmp, '[context]\ninject = "skill.md"')), r
            )
            self.assertNotEqual(without.config_hash, armed.config_hash)

    def test_different_bodies_hash_differently(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "a.md").write_text("BODY A", encoding="utf-8")
            (tmp / "b.md").write_text("BODY B — different", encoding="utf-8")
            r = StubResolver()
            ra = resolve_scenario(load_scenario(self._write(tmp, '[context]\ninject = "a.md"')), r)
            rb = resolve_scenario(load_scenario(self._write(tmp, '[context]\ninject = "b.md"')), r)
            self.assertNotEqual(ra.config_hash, rb.config_hash)

    def test_inject_resolved_relative_to_scenario_dir(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "skill.md").write_text("BODY", encoding="utf-8")
            cfg = load_scenario(self._write(tmp, '[context]\ninject = "skill.md"'))
            self.assertTrue(os.path.isabs(cfg.context.inject))
            self.assertTrue(Path(cfg.context.inject).is_file())

    def test_distinct_missing_inject_files_hash_differently(self):
        """Two treatments naming different (missing) inject files must not collide
        into one ledger bucket — fathom never lets longitudinal history silently fork."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            r = StubResolver()
            miss_a = resolve_scenario(
                load_scenario(self._write(tmp, '[context]\ninject = "gone-a.md"')), r
            )
            miss_b = resolve_scenario(
                load_scenario(self._write(tmp, '[context]\ninject = "gone-b.md"')), r
            )
            self.assertNotEqual(miss_a.config_hash, miss_b.config_hash)


# ---------------------------------------------------------------------------
# TestPluginMount — [plugins] mount field + config_hash extension (§2)
# ---------------------------------------------------------------------------


class TestPluginMount(unittest.TestCase):
    """The [plugins] mount field folds (name, version, tree_sha) per mounted
    plugin dir into config_hash. Absent [plugins] or empty mount == no plugins
    (hash-stable vs committed ledgers); changing a plugin's tree_sha changes
    the hash."""

    def _write(self, tmp: Path, plugins_block: str) -> Path:
        p = tmp / "s.toml"
        p.write_text(
            'name = "s"\n'
            'adapter = "claude-cli"\n'
            'model = "m"\n'
            'strategy = "single-session"\n'
            'effort = "high"\n'
            '[tools]\nsource = "none"\nallowed = ["Read"]\n'
            f"{plugins_block}\n",
            encoding="utf-8",
        )
        return p

    def test_absent_and_empty_mount_hash_identically(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            r = StubResolver()
            absent = resolve_scenario(load_scenario(self._write(tmp, "")), r)
            empty_plugins = resolve_scenario(
                load_scenario(self._write(tmp, "[plugins]\nmount = []")), r
            )
            self.assertEqual(absent.config_hash, empty_plugins.config_hash)

    def test_setting_mount_changes_hash(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            plugin_dir = tmp / "my-plugin"
            plugin_dir.mkdir()
            r = StubResolver()
            without = resolve_scenario(load_scenario(self._write(tmp, "")), r)
            with_plugin = resolve_scenario(
                load_scenario(self._write(tmp, f'[plugins]\nmount = ["{plugin_dir.as_posix()}"]')),
                r,
            )
            self.assertNotEqual(without.config_hash, with_plugin.config_hash)

    def test_changing_tree_sha_changes_hash(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            plugin_dir = tmp / "my-plugin"
            plugin_dir.mkdir()
            toml_path = self._write(tmp, f'[plugins]\nmount = ["{plugin_dir.as_posix()}"]')

            class ShaResolver:
                def __init__(self, sha: str) -> None:
                    self._sha = sha

                def resolve_model_id(self, model: str) -> str | None:
                    return model + "-20251001"

                def resolve_tool_repo_sha(self, repo: str) -> str:
                    return StubResolver.STUB_SHA

                def build_tool_invocation_cmd(self, repo: str) -> str:
                    return f"uv run --project {repo} convoy"

                def resolve_plugin_meta(self, plugin_dir: str) -> tuple[str, str, str]:
                    return ("plug", "1.0", self._sha)

            r1 = resolve_scenario(load_scenario(toml_path), ShaResolver("sha-aaa"))
            r2 = resolve_scenario(load_scenario(toml_path), ShaResolver("sha-bbb"))
            self.assertNotEqual(r1.config_hash, r2.config_hash)

    def test_mount_paths_absolutized_relative_to_scenario_dir(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            plugin_dir = tmp / "my-plugin"
            plugin_dir.mkdir()
            cfg = load_scenario(self._write(tmp, '[plugins]\nmount = ["my-plugin"]'))
            self.assertIsInstance(cfg.plugins, PluginsConfig)
            self.assertEqual(len(cfg.plugins.mount), 1)
            self.assertTrue(os.path.isabs(cfg.plugins.mount[0]))
            self.assertEqual(Path(cfg.plugins.mount[0]), plugin_dir.resolve())

    def test_known_good_hashes_unchanged(self):
        """Regression: PluginsConfig must not shift config_hash for scenarios
        that have no [plugins] block — committed skill-pyeng-v1 ledger resume
        keys depend on these being byte-identical (ADR-0002).

        Hashes were captured with StubResolver before PluginsConfig was added;
        they must remain stable across any schema extension."""
        known = {
            # top-level arms (scenarios/)
            "bare.toml": "bbc88a419d2128e34d8c1cc864f08dbc76591581c86b02f12da36807d302f810",
            "single-long-session.toml": (
                "d1e8897eac5f8c949f16b8901d32c5d8a4111e7d04ecda97bfb6194ae79e405f"
            ),
            # skill-pyeng-v1 bank (scenarios/skill-pyeng/)
            "skill-pyeng/bare.toml": (
                "bbc88a419d2128e34d8c1cc864f08dbc76591581c86b02f12da36807d302f810"
            ),
            "skill-pyeng/generic-nudge.toml": (
                "2c9a96a307f60f72ece5fcfe78148989fa0c459291d20260348954c1510ff8b5"
            ),
            "skill-pyeng/pyeng-skill.toml": (
                "427bd061011bc4cf7a29cbdfb7fb88a2935222a44b5afb15137b8081d12107bf"
            ),
        }
        r = StubResolver()
        for filename, expected_hash in known.items():
            path = SCENARIOS_DIR / filename
            config = load_scenario(path)
            resolved = resolve_scenario(config, r)
            self.assertEqual(
                resolved.config_hash,
                expected_hash,
                f"{filename}: config_hash shifted — would break committed ledger resume keys",
            )


class TestSettingsInjection(unittest.TestCase):
    """The [settings] inject field: a treatment scenario writes a settings.json
    into the spawn's isolated config dir, so a user-scope hook (e.g. a PreToolUse
    rewrite) is active for the arm — the one thing a plugin mount cannot deliver
    in headless `claude -p`. Absent inject == no settings (hash-stable vs
    committed ledgers); the file's *content* (sha256), not the path, enters
    config_hash. Distinct axis from [context]: identical bodies must not collide."""

    def _write(self, tmp: Path, settings_block: str) -> Path:
        p = tmp / "s.toml"
        p.write_text(
            'name = "s"\n'
            'adapter = "claude-cli"\n'
            'model = "m"\n'
            'strategy = "single-session"\n'
            'effort = "high"\n'
            '[tools]\nsource = "none"\nallowed = ["Read"]\n'
            f"{settings_block}\n",
            encoding="utf-8",
        )
        return p

    def test_absent_and_empty_settings_hash_identically(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            r = StubResolver()
            absent = resolve_scenario(load_scenario(self._write(tmp, "")), r)
            empty = resolve_scenario(load_scenario(self._write(tmp, "[settings]")), r)
            self.assertEqual(absent.config_hash, empty.config_hash)

    def test_setting_inject_changes_hash(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "settings.json").write_text('{"hooks": {}}', encoding="utf-8")
            r = StubResolver()
            without = resolve_scenario(load_scenario(self._write(tmp, "")), r)
            armed = resolve_scenario(
                load_scenario(self._write(tmp, '[settings]\ninject = "settings.json"')), r
            )
            self.assertNotEqual(without.config_hash, armed.config_hash)

    def test_different_bodies_hash_differently(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "a.json").write_text('{"hooks": {"PreToolUse": []}}', encoding="utf-8")
            (tmp / "b.json").write_text('{"hooks": {"PreToolUse": [1]}}', encoding="utf-8")
            r = StubResolver()
            ra = resolve_scenario(
                load_scenario(self._write(tmp, '[settings]\ninject = "a.json"')), r
            )
            rb = resolve_scenario(
                load_scenario(self._write(tmp, '[settings]\ninject = "b.json"')), r
            )
            self.assertNotEqual(ra.config_hash, rb.config_hash)

    def test_inject_resolved_relative_to_scenario_dir(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "settings.json").write_text("{}", encoding="utf-8")
            cfg = load_scenario(self._write(tmp, '[settings]\ninject = "settings.json"'))
            self.assertIsInstance(cfg.settings, SettingsConfig)
            self.assertTrue(os.path.isabs(cfg.settings.inject))
            self.assertTrue(Path(cfg.settings.inject).is_file())

    def test_settings_and_context_are_distinct_axes(self):
        """A [settings] inject and a [context] inject with identical bodies must
        not produce the same hash — they are different treatment channels."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "x").write_text("SAME BODY", encoding="utf-8")
            r = StubResolver()
            as_ctx = resolve_scenario(load_scenario(self._write(tmp, '[context]\ninject = "x"')), r)
            as_set = resolve_scenario(
                load_scenario(self._write(tmp, '[settings]\ninject = "x"')), r
            )
            self.assertNotEqual(as_ctx.config_hash, as_set.config_hash)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
