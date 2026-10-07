"""The spawn environment carries none of fathom's own state — stdlib-runnable.

Run directly:  python tests/test_spawn_env.py
Run via pytest: uv run pytest tests/test_spawn_env.py

fathom talks to itself through FATHOM_* variables: FATHOM_HOME names the data root,
which holds every task's reference material; FATHOM_STREAM_DIR and FATHOM_STREAM_TAG
tell the adapter where to keep a trial's raw stream, and the tag carries the arm's name.
The shell that started fathom also leaves PWD (and OLDPWD) naming the directory it was
started in, which is the data root when fathom finds its data root from there; moving
into the data root for a command does not change them. None of that is for the agent
under test. These tests set such variables in the parent, run from inside a
data-root-like directory as a command does, and read the environment each spawn path
actually hands its child: the single-session adapter (and every strategy that runs
through it) and the series engine.

A scenario's ``[env]`` table is applied after the strip. It may name any variable,
FATHOM_* included: that is the arm's own declared treatment, and it enters config_hash.
A ``${NAME}`` in its values reads the stripped environment, so a template cannot forward
the parent's FATHOM_* values or its working directory.

Two more routes to the data root are closed here. A variable can name it by value
(VIRTUAL_ENV and PATH, when fathom runs from a virtual environment inside it): while a
command runs, the data root is registered as hidden and such values are withheld. And a
treatment arm's argv would name its [context] body and [plugins] mounts, which live
under the data root: the runner `fathom run` builds passes per-spawn copies instead.

No real spawns: both subprocess boundaries are injected.
"""

import contextlib
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.adapters.base import ExitStatus, RunRecord
from fathom.adapters.claude_cli import (
    ClaudeCliRunner,
    cleanup_dir,
    make_spawn_env,
    without_harness_vars,
)
from fathom.scenario import EnvConfig, LimitsOverride, ResolvedScenario, ToolsConfig
from fathom.strategies.series import EngineOutcome, SeriesExecutor
from fathom.taskbank import Task

# What a parent process holds during `fathom run`: the data root, the stream tee's
# directory and per-trial tag (set by the run loop), and any other FATHOM_* name.
PARENT_FATHOM_VARS = {
    "FATHOM_HOME": "/data/root/with/reference/solutions",
    "FATHOM_STREAM_DIR": "(replaced by a temporary directory in setUp)",
    "FATHOM_STREAM_TAG": "example--arm-a--add--r0",
    "FATHOM_SOMETHING_NEW": "any future harness variable",
}
BENIGN = {"SPAWN_ENV_TEST_BENIGN": "keep-me"}

_STREAM = (
    '{"type": "system", "subtype": "init", "model": "m", "version": "1.2.3"}\n'
    '{"type": "result", "subtype": "success", "is_error": false, "num_turns": 1,'
    ' "duration_ms": 10, "total_cost_usd": 0.01, "result": "done",'
    ' "usage": {"input_tokens": 1, "output_tokens": 1}}\n'
)

_SERIES_TEMPLATE = """\
[series]
id = "example"
version = "1.0"

[paths]
prompts = "prompts"
outputs = "outputs"

[governance]
effort = "high"

[[prs]]
id = "PR01"
branch = "example/pr01"
prompt = "pr01.md"
phase = "1"
depends_on = []
"""


def _harness_names(env) -> list[str]:
    """The FATHOM_* names in *env*.

    Assertions compare these name lists, never the environment mapping itself: a failure
    message would print the whole environment, and it can hold credentials.
    """
    return sorted(name for name in env if name.upper().startswith("FATHOM_"))


def _names_holding(env, needle: str) -> list[str]:
    """The names in *env* whose value contains *needle* (names only, as above)."""
    return sorted(name for name, value in env.items() if needle in value)


def _dir_names(env) -> list[str]:
    """The working-directory variable names in *env*, in any case."""
    return sorted(name for name in env if name.upper() in {"PWD", "OLDPWD"})


def _scenario(*, strategy="single-session", env_vars=(), tool_invocation_cmd=None):
    return ResolvedScenario(
        name="arm-a",
        adapter="claude-cli",
        model="claude-opus-4-8",
        strategy=strategy,
        effort="high",
        tools=ToolsConfig(source="none"),
        limits=LimitsOverride(trial_timeout_s=60),
        model_id=None,
        tool_repo_sha=None,
        tool_invocation_cmd=tool_invocation_cmd,
        config_hash="x" * 64,
        env=EnvConfig(vars=tuple(env_vars)),
    )


class _RecordingSpawn:
    """The adapter's subprocess boundary: records the child env, replays a clean run."""

    def __init__(self):
        self.envs: list[dict[str, str]] = []

    def __call__(self, argv, *, input, timeout, env, cwd):
        self.envs.append(dict(env))
        return subprocess.CompletedProcess(list(argv), 0, _STREAM, "")


class _RecordingEngine:
    """The series engine boundary: records the env the engine process would get."""

    def __init__(self):
        self.envs: list[dict[str, str]] = []

    def __call__(self, argv, *, cwd, env, timeout):
        self.envs.append(dict(env))
        return EngineOutcome(returncode=0, stdout="", stderr="", timed_out=False, duration_s=0.1)


class _Base(unittest.TestCase):
    def setUp(self):
        # The tee writes where FATHOM_STREAM_DIR points, so the parent's value is a
        # real temporary directory.
        self.streams = Path(tempfile.mkdtemp(prefix="fathom-spawn-env-streams-"))
        self.addCleanup(cleanup_dir, str(self.streams))
        # fathom started from inside its data root: the shell's PWD names it (in the
        # shell's own spelling), and OLDPWD names it after a `cd` back out and in.
        self.data_root = Path(tempfile.mkdtemp(prefix="fathom-spawn-env-root-"))
        self.addCleanup(cleanup_dir, str(self.data_root))
        self.parent = {
            **PARENT_FATHOM_VARS,
            "FATHOM_STREAM_DIR": str(self.streams),
            "PWD": self.data_root.as_posix(),
            "OLDPWD": str(self.data_root),
            **BENIGN,
        }
        patcher = mock.patch.dict(os.environ, self.parent)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.workspace = Path(tempfile.mkdtemp(prefix="fathom-spawn-env-ws-"))
        self.addCleanup(cleanup_dir, str(self.workspace))
        self.real_config = Path(tempfile.mkdtemp(prefix="fathom-spawn-env-cfg-"))
        (self.real_config / ".credentials.json").write_text("{}", encoding="utf-8")
        self.addCleanup(cleanup_dir, str(self.real_config))

    def run_adapter(self, scenario=None) -> dict[str, str]:
        spawn = _RecordingSpawn()
        runner = ClaudeCliRunner(
            spawn=spawn, sleep=lambda _s: None, real_config_dir=str(self.real_config)
        )
        # A fathom command runs with the data root as its working directory.
        with contextlib.chdir(self.data_root):
            record = runner.execute("p", self.workspace, scenario or _scenario())
        self.assertEqual(record.status, ExitStatus.OK)
        self.assertEqual(len(spawn.envs), 1)
        return spawn.envs[0]

    def run_engine(self) -> dict[str, str]:
        task_dir = Path(tempfile.mkdtemp(prefix="fathom-spawn-env-task-"))
        self.addCleanup(cleanup_dir, str(task_dir))
        (task_dir / "series.toml").write_text(_SERIES_TEMPLATE, encoding="utf-8")
        (task_dir / "prompts").mkdir()
        (task_dir / "prompts" / "pr01.md").write_text("implement PR01", encoding="utf-8")
        task = Task(
            id="add",
            instruction="do the thing",
            limits={},
            verify={"entry": "verify.py"},
            task_dir=task_dir,
        )
        engine = _RecordingEngine()
        executor = SeriesExecutor(run_engine=engine, real_config_dir=str(self.real_config))
        # A fathom command runs with the data root as its working directory.
        with contextlib.chdir(self.data_root):
            executor.run_trial(
                task,
                self.workspace,
                _scenario(strategy="series", tool_invocation_cmd="engine"),
                types.SimpleNamespace(execute=lambda *a, **k: RunRecord(status=ExitStatus.OK)),
            )
        self.assertEqual(len(engine.envs), 1)
        return engine.envs[0]


class TestMakeSpawnEnv(_Base):
    def test_no_fathom_variable_reaches_the_spawn_env(self):
        env = make_spawn_env("cfg-dir")
        self.assertEqual(_harness_names(env), [])
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], "cfg-dir")
        self.assertEqual(env["SPAWN_ENV_TEST_BENIGN"], "keep-me")

    def test_the_account_connectors_are_turned_off_in_the_spawn_env(self):
        """The account's claude.ai connectors reach a session whatever its configuration
        directory, and arrive in some spawns and not others."""
        self.assertEqual(make_spawn_env("/cfg")["ENABLE_CLAUDEAI_MCP_SERVERS"], "false")

    def test_the_parent_environment_is_left_as_it_was(self):
        make_spawn_env("cfg-dir")
        for name, value in self.parent.items():
            self.assertEqual(os.environ[name], value)

    def test_the_working_directory_variables_do_not_reach_the_spawn_env(self):
        env = make_spawn_env("cfg-dir")
        self.assertEqual(_dir_names(env), [])
        self.assertEqual(_names_holding(env, self.data_root.name), [])

    def test_env_for_agent_code_drops_the_billing_variables_too(self):
        # A gate runs agent-written code, and what it prints reaches the agent: it gets
        # the spawn's environment less the config dir, not fathom's with the credentials.
        from fathom.adapters.claude_cli import env_for_agent_code

        planted = {
            "ANTHROPIC_API_KEY": "planted",
            "ANTHROPIC_AUTH_TOKEN": "planted",
            "AWS_BEARER_TOKEN_BEDROCK": "planted",
        }
        with mock.patch.dict(os.environ, planted):
            env = env_for_agent_code()
            spawn = make_spawn_env("cfg-dir")
        for built in (env, spawn):
            self.assertEqual(_names_holding(built, "planted"), [])
            self.assertEqual(_harness_names(built), [])
            self.assertEqual(_dir_names(built), [])
            self.assertEqual(built["SPAWN_ENV_TEST_BENIGN"], "keep-me")
        self.assertEqual(spawn["CLAUDE_CONFIG_DIR"], "cfg-dir")

    def test_without_harness_vars_matches_names_case_insensitively(self):
        # Windows treats environment names case-insensitively, so a child there reads
        # `Fathom_Home` as FATHOM_HOME. The strip does too.
        env = {
            "Fathom_Home": "/x",
            "fathom_stream_tag": "t",
            "Pwd": "/root",
            "oldpwd": "/root",
            "FATHOMLESS": "kept",
            "PWDX": "kept",
            "PATH": "/b",
        }
        self.assertEqual(
            without_harness_vars(env), {"FATHOMLESS": "kept", "PWDX": "kept", "PATH": "/b"}
        )
        self.assertIn("Fathom_Home", env, "the input mapping is not modified")


class TestAdapterSpawn(_Base):
    def test_no_fathom_variable_reaches_the_child(self):
        env = self.run_adapter()
        self.assertEqual(_harness_names(env), [])
        self.assertTrue("CLAUDE_CONFIG_DIR" in env)
        self.assertEqual(env["SPAWN_ENV_TEST_BENIGN"], "keep-me")

    def test_no_value_names_the_data_root_it_was_started_in(self):
        env = self.run_adapter()
        self.assertEqual(_dir_names(env), [])
        self.assertEqual(_names_holding(env, self.data_root.name), [])

    def test_the_stream_tee_still_works_from_the_parent(self):
        # The tee reads FATHOM_STREAM_DIR in fathom's own process, so stripping the
        # child's copy leaves it working.
        env = self.run_adapter()
        self.assertEqual(_harness_names(env), [])
        written = list(self.streams.iterdir())
        self.assertEqual(len(written), 1)
        self.assertTrue(written[0].name.startswith("example--arm-a--add--r0--a1--"))

    def test_a_scenario_env_still_applies(self):
        env = self.run_adapter(
            _scenario(env_vars=(("EXAMPLE_DIR", "${workspace}/store"), ("PATH", "/x;${PATH}")))
        )
        self.assertEqual(env["EXAMPLE_DIR"], f"{self.workspace}/store")
        self.assertTrue(env["PATH"].startswith("/x;"))
        self.assertEqual(_harness_names(env), [])

    def test_a_scenario_may_set_a_fathom_name_of_its_own(self):
        # Declared in the arm file and hashed with it, so it is a treatment, not a leak;
        # the parent's other FATHOM_* values still do not pass.
        env = self.run_adapter(_scenario(env_vars=(("FATHOM_HOME", "${workspace}/fixture"),)))
        self.assertEqual(env["FATHOM_HOME"], f"{self.workspace}/fixture")
        self.assertEqual(_harness_names(env), ["FATHOM_HOME"])

    def test_a_scenario_template_cannot_forward_a_parent_fathom_value(self):
        env = self.run_adapter(
            _scenario(
                env_vars=(("COPY_OF_HOME", "${FATHOM_HOME}"), ("TAG", "${FATHOM_STREAM_TAG}"))
            )
        )
        self.assertEqual(env["COPY_OF_HOME"], "")
        self.assertEqual(env["TAG"], "")
        self.assertEqual(_harness_names(env), [])

    def test_a_scenario_template_cannot_forward_the_parent_working_directory(self):
        env = self.run_adapter(_scenario(env_vars=(("WHERE", "${PWD}"), ("BEFORE", "${OLDPWD}"))))
        self.assertEqual(env["WHERE"], "")
        self.assertEqual(env["BEFORE"], "")
        self.assertEqual(_names_holding(env, self.data_root.name), [])


class TestSeriesEngineSpawn(_Base):
    def test_no_fathom_variable_reaches_the_engine(self):
        env = self.run_engine()
        self.assertEqual(_harness_names(env), [])
        self.assertTrue("CLAUDE_CONFIG_DIR" in env)
        self.assertEqual(env["SPAWN_ENV_TEST_BENIGN"], "keep-me")

    def test_no_value_names_the_data_root_it_was_started_in(self):
        env = self.run_engine()
        self.assertEqual(_dir_names(env), [])
        self.assertEqual(_names_holding(env, self.data_root.name), [])


def _spellings(path: Path) -> set[str]:
    """Lower-cased, forward-slashed ways a string could spell *path*: as given and
    resolved."""
    return {f.replace("\\", "/").lower() for f in (str(path), str(path.resolve()))}


def _naming(value: str, path: Path) -> bool:
    """True when *value* spells *path* in any of the ways above."""
    value = value.replace("\\", "/").lower()
    return any(s in value for s in _spellings(path))


def _names_naming(env, path: Path) -> list[str]:
    """The names in *env* whose value spells *path* (names only, as above)."""
    return sorted(name for name, value in env.items() if _naming(value, path))


class TestArgvNamesNoDataRoot(_Base):
    """A treatment arm's argv names copies of its files, not the declared paths.

    The authoring guide keeps an arm's [context] body and [plugins] mounts under
    scenarios/assets/ in the data root. Whatever the argv names, the agent can learn: a
    shell grant reads the process table, and Claude Code tells the model a loaded skill's
    base directory. So the runner `fathom run` builds copies them into a directory of the
    spawn's own.
    """

    def setUp(self):
        super().setUp()
        assets = self.data_root / "scenarios" / "assets"
        self.inject = assets / "nudge.md"
        self.inject.parent.mkdir(parents=True)
        self.inject.write_text("Write tests first.", encoding="utf-8")
        self.plugin = assets / "example-plugin"
        (self.plugin / ".claude-plugin").mkdir(parents=True)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "example-plugin", "version": "1.0.0"}', encoding="utf-8"
        )
        (self.plugin / "skills" / "example").mkdir(parents=True)
        (self.plugin / "skills" / "example" / "SKILL.md").write_text("a skill", encoding="utf-8")

    def _arm(self, *, inject=None, mount=()):
        from fathom.scenario import ContextConfig, PluginsConfig

        return ResolvedScenario(
            name="arm-a",
            adapter="claude-cli",
            model="claude-opus-4-8",
            strategy="single-session",
            effort="high",
            tools=ToolsConfig(source="none", allowed=("Read", "Write")),
            limits=LimitsOverride(trial_timeout_s=60),
            model_id=None,
            tool_repo_sha=None,
            tool_invocation_cmd=None,
            config_hash="x" * 64,
            context=ContextConfig(inject=inject),
            plugins=PluginsConfig(mount=tuple(mount)),
        )

    def run_trial_runner(self, scenario) -> dict:
        """The runner `fathom run` builds for *scenario*, spawned once through a stub
        that records the argv and what the files it names held at that moment."""
        from fathom.cli import _default_runner_factory

        seen: dict = {}

        def spawn(argv, *, input, timeout, env, cwd):
            argv = list(argv)
            seen["argv"] = argv
            if "--append-system-prompt-file" in argv:
                body = Path(argv[argv.index("--append-system-prompt-file") + 1])
                seen["body_path"] = body
                seen["body"] = body.read_text(encoding="utf-8")
            seen["mounts"] = [
                Path(argv[i + 1]) for i, tok in enumerate(argv) if tok == "--plugin-dir"
            ]
            seen["plugin_json"] = [
                (m / ".claude-plugin" / "plugin.json").is_file() for m in seen["mounts"]
            ]
            return subprocess.CompletedProcess(argv, 0, _STREAM, "")

        runner = _default_runner_factory(scenario)
        runner._spawn = spawn
        runner._sleep = lambda _s: None
        runner.real_config_dir = str(self.real_config)
        with contextlib.chdir(self.data_root):
            record = runner.execute("p", self.workspace, scenario)
        self.assertEqual(record.status, ExitStatus.OK)
        # No argv element names the data root, in any spelling (positions only: an
        # element could hold a path the failure message should not print in full).
        leaking = [i for i, tok in enumerate(seen["argv"]) if _naming(tok, self.data_root)]
        self.assertEqual(leaking, [], "argv positions naming the data root")
        return seen

    def test_an_inject_arm_passes_a_copy_of_the_body(self):
        seen = self.run_trial_runner(self._arm(inject=str(self.inject)))
        self.assertEqual(seen["body"], "Write tests first.")

    def test_a_mount_arm_passes_a_copy_of_the_plugin(self):
        seen = self.run_trial_runner(self._arm(mount=[str(self.plugin)]))
        self.assertEqual(len(seen["mounts"]), 1)
        self.assertEqual(seen["plugin_json"], [True])

    def test_the_copy_does_not_carry_the_mount_directory_name(self):
        # The directory an author mounts is often named after the arm. The plugin's
        # identity is the name in its manifest, so the copy takes a fixed name.
        named = self.data_root / "scenarios" / "assets" / "zq-arm-mount"
        named.mkdir()
        (named / ".claude-plugin").mkdir()
        (named / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "example-plugin"}', encoding="utf-8"
        )
        seen = self.run_trial_runner(self._arm(mount=[str(named)]))
        self.assertEqual(seen["plugin_json"], [True])
        naming = [i for i, tok in enumerate(seen["argv"]) if "zq-arm-mount" in tok.lower()]
        self.assertEqual(naming, [], "argv positions naming the mount directory")

    def test_a_plugin_without_a_manifest_keeps_its_directory_name(self):
        # Without a manifest, Claude Code takes the plugin's name from its directory, so
        # renaming the copy would rename the plugin and its skills.
        bare = self.data_root / "scenarios" / "assets" / "no-manifest"
        (bare / "skills" / "example").mkdir(parents=True)
        (bare / "skills" / "example" / "SKILL.md").write_text("a skill", encoding="utf-8")
        seen = self.run_trial_runner(self._arm(mount=[str(bare)]))
        self.assertEqual(seen["mounts"][0].name, "no-manifest")

    def test_the_copies_are_gone_after_the_spawn(self):
        seen = self.run_trial_runner(self._arm(inject=str(self.inject), mount=[str(self.plugin)]))
        self.assertFalse(seen["body_path"].exists())
        self.assertFalse(seen["mounts"][0].exists())


class TestValuesNamingTheDataRoot(_Base):
    """A variable that names the data root by value does not reach a child.

    `uv run fathom` in a data repository that pins fathom sets VIRTUAL_ENV to the data
    root's .venv and puts its scripts directory first on PATH. Stripping by name misses
    both. While a command runs against a data root, the CLI registers it as hidden
    (test_cli.py checks that registration).
    """

    def setUp(self):
        super().setUp()
        venv = self.data_root / ".venv"
        scripts = venv / ("Scripts" if os.name == "nt" else "bin")
        self.other_entry = str(Path(tempfile.gettempdir()) / "some-tool" / "bin")
        patcher = mock.patch.dict(
            os.environ,
            {"VIRTUAL_ENV": str(venv), "PATH": os.pathsep.join([str(scripts), self.other_entry])},
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def hidden(self):
        from fathom.adapters.claude_cli import hidden_from_children

        return hidden_from_children(self.data_root)

    def test_make_spawn_env_withholds_the_data_root(self):
        with self.hidden():
            env = make_spawn_env("cfg-dir")
        self.assertEqual(_names_naming(env, self.data_root), [])
        self.assertNotIn("VIRTUAL_ENV", env)
        self.assertEqual(env["PATH"], self.other_entry, "PATH keeps its other entries")
        self.assertEqual(env["SPAWN_ENV_TEST_BENIGN"], "keep-me")

    def test_the_adapter_spawn_withholds_the_data_root(self):
        with self.hidden():
            env = self.run_adapter()
        self.assertEqual(_names_naming(env, self.data_root), [])
        self.assertEqual(env["PATH"], self.other_entry)

    def test_the_series_engine_withholds_the_data_root(self):
        with self.hidden():
            env = self.run_engine()
        self.assertEqual(_names_naming(env, self.data_root), [])
        self.assertEqual(env["PATH"], self.other_entry)

    def test_the_registration_ends_with_the_block(self):
        from fathom.adapters.claude_cli import hidden_dirs

        with self.hidden():
            self.assertEqual(len(hidden_dirs()), 1)
        self.assertEqual(hidden_dirs(), ())
        self.assertIn("VIRTUAL_ENV", make_spawn_env("cfg-dir"), "nothing is withheld outside")

    def test_a_directory_that_shares_a_prefix_is_not_withheld(self):
        sibling = {"SIBLING": str(self.data_root) + "-old", "INSIDE": str(self.data_root / "x")}
        env = without_harness_vars(sibling, hidden=[self.data_root])
        self.assertEqual(sorted(env), ["SIBLING"])

    def test_an_msys_spelling_is_withheld(self):
        resolved = self.data_root.resolve().as_posix()
        if os.name != "nt" or resolved[1:3] != ":/":
            self.skipTest("the MSYS spelling is a Windows drive path")
        msys = f"/{resolved[0].lower()}/{resolved[3:]}/.venv"
        env = without_harness_vars(
            {"FROM_GIT_BASH": msys, "OTHER": "/c/elsewhere"}, hidden=[self.data_root]
        )
        self.assertEqual(sorted(env), ["OTHER"])

    def test_a_directory_holding_the_home_directory_is_not_withheld(self):
        # Every child needs HOME/USERPROFILE and the PATH entries under them; withholding
        # an ancestor of the home directory would break every spawn instead.
        home = Path.home()
        env = {"HOME_LIKE": str(home), "PATH": str(home / "bin")}
        self.assertEqual(without_harness_vars(env, hidden=[home]), env)
        self.assertEqual(without_harness_vars(env, hidden=[home.parent]), env)


if __name__ == "__main__":
    unittest.main()
