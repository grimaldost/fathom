"""Tests for the [env] scenario extension — stdlib-runnable.

Run directly:  python tests/test_env_injection.py
Run via pytest: uv run pytest tests/test_env_injection.py

Covers the parse (sorted, absent==empty), the config_hash inclusion rule
(non-empty [env] forks the hash; an empty/absent [env] does NOT — ADR-0002),
and the spawn-time substitution (${workspace}, ${VAR} passthrough for PATH).
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.adapters.claude_cli import _apply_env_template, _subst_env
from fathom.scenario import load_scenario, resolve_scenario


class _Stub:
    """Deterministic resolver — no git/CLI calls."""

    def resolve_model_id(self, model: str) -> str:
        return model + "-x"

    def resolve_tool_repo_sha(self, repo: str) -> str:
        return "sha"

    def build_tool_invocation_cmd(self, repo: str) -> str:
        return "cmd"

    def resolve_plugin_meta(self, plugin_dir: str) -> tuple[str, str, str]:
        return ("n", "v", "t")


BASE = """name = "a"
adapter = "claude-cli"
model = "claude-opus-4-8"
strategy = "single-session"
effort = "high"
[tools]
source = "none"
allowed = ["Read"]
[limits]
trial_timeout_s = 600
"""


def _write(tmp: str, body: str) -> Path:
    p = Path(tmp) / "s.toml"
    p.write_text(body, encoding="utf-8")
    return p


class TestEnvParse(unittest.TestCase):
    def test_parse_sorted(self):
        with tempfile.TemporaryDirectory() as t:
            sc = load_scenario(_write(t, BASE + '[env]\nZED = "1"\nALPHA = "2"\n'))
        self.assertEqual(sc.env.vars, (("ALPHA", "2"), ("ZED", "1")))

    def test_absent_env_is_empty(self):
        with tempfile.TemporaryDirectory() as t:
            sc = load_scenario(_write(t, BASE))
        self.assertEqual(sc.env.vars, ())


class TestEnvHash(unittest.TestCase):
    def test_env_forks_hash(self):
        with tempfile.TemporaryDirectory() as t:
            no = resolve_scenario(load_scenario(_write(t, BASE)), _Stub())
        with tempfile.TemporaryDirectory() as t:
            yes = resolve_scenario(load_scenario(_write(t, BASE + '[env]\nA = "b"\n')), _Stub())
        self.assertNotEqual(no.config_hash, yes.config_hash)

    def test_empty_env_table_same_as_absent(self):
        """ADR-0002: an empty [env] must not shift a scenario's resume key."""
        with tempfile.TemporaryDirectory() as t:
            absent = resolve_scenario(load_scenario(_write(t, BASE)), _Stub())
        with tempfile.TemporaryDirectory() as t:
            empty = resolve_scenario(load_scenario(_write(t, BASE + "[env]\n")), _Stub())
        self.assertEqual(absent.config_hash, empty.config_hash)


class TestSubst(unittest.TestCase):
    def test_workspace_and_path_prepend(self):
        env = {"PATH": "/usr/bin", "CLAUDE_CONFIG_DIR": "/cfg"}
        out = _apply_env_template(
            env,
            (("ENVMEMORY__DIR", "${workspace}/.store"), ("PATH", "/tu/bin;${PATH}")),
            workspace="/ws",
        )
        self.assertEqual(out["ENVMEMORY__DIR"], "/ws/.store")
        self.assertEqual(out["PATH"], "/tu/bin;/usr/bin")
        self.assertEqual(out["CLAUDE_CONFIG_DIR"], "/cfg")  # untouched
        self.assertEqual(env["PATH"], "/usr/bin")  # input not mutated

    def test_unknown_var_becomes_empty(self):
        self.assertEqual(_subst_env("x=${NOPE}", {}, "/ws"), "x=")


if __name__ == "__main__":
    unittest.main()
