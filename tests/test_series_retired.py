"""The `series` strategy is retired (0.13.0): the clauses that say so, and the text that says so.

fathom once drove an external multi-PR engine as a strategy of its own. These tests hold what
retiring it left behind: the strategy, its smoke check group and its contract spec are gone;
an arm that names it, or sets ``[tools] source = "repo"``, is refused; what other code reads
(the argv shim, the ``config_hash`` preimage keys, ``PIN_SERIES``) stays; and every shipped
document says the strategy is retired rather than describing it as usable.

The closing greps below walk the working tree, not git, so they hold in a copy without ``.git``.

Stdlib only; runs without uv as ``python tests/test_series_retired.py``.
"""

from __future__ import annotations

import contextlib
import importlib
import inspect
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE / "src"))

from fathom import cli, scenario, smoke  # noqa: E402
from fathom.cli import main  # noqa: E402
from fathom.strategies import KNOWN_STRATEGIES  # noqa: E402

SKILL = ENGINE / "skills" / "fathom-eval" / "SKILL.md"
ARMING = ENGINE / "skills" / "fathom-eval" / "reference" / "arming.md"

# Strings are built from parts where they would otherwise make this file a hit of the closing
# greps below, which scan `tests/` for the removed names and allow only this file.
REMAINING_STRATEGIES = ("single-session", "gated-session", "gated-review", "reprompt-session")
REMOVED_FILES = (
    "src/fathom/strategies/series.py",
    "docs/specs/2026-07-03-series-engine-contract.md",
    "docs/method/series-toml-skeleton.md",
    "tests/test_series_contract_convoy_080.py",
    "tests/fixtures/convoy-0.8.0-spawns.jsonl",
    "tests/fixtures/convoy-0.8.0-spawns-abandoned.jsonl",
    "tests/fixtures/scenarios/series.toml",
)


# ---------------------------------------------------------------------------
# The strategy and its code
# ---------------------------------------------------------------------------


class TheStrategyIsGoneTests(unittest.TestCase):
    def test_the_module_does_not_import(self) -> None:
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("fathom.strategies.series")

    def test_the_registry_lists_the_four_that_remain(self) -> None:
        self.assertEqual(
            KNOWN_STRATEGIES,
            frozenset({"single-session", "gated-session", "gated-review", "reprompt-session"}),
        )

    def test_the_executor_and_its_outcome_are_not_exported(self) -> None:
        import fathom.strategies as strategies

        self.assertFalse(hasattr(strategies, "SeriesExecutor"))
        self.assertFalse(hasattr(strategies, "EngineOutcome"))
        self.assertNotIn("SeriesExecutor", strategies.__all__)

    def test_the_pin_level_old_ledger_rows_carry_stays(self) -> None:
        import fathom.strategies as strategies

        self.assertEqual(strategies.PIN_SERIES, "series")

    def test_the_removed_names_are_gone(self) -> None:
        for module, names in (
            (
                smoke,
                (
                    "assert_no_bypass_in_engine_spawn",
                    "permission_mode_of",
                    "_DefaultSmokeResolver",
                    "_SMOKE_SERIES_TEMPLATE",
                    "NON_BYPASS_PERMISSION_MODE",
                    "DEFAULT_ENGINE_TIMEOUT_S",
                    "_write_smoke_task_assets",
                ),
            ),
            (scenario, ("resolve_repo_invocation_cmd",)),
            (cli, ("_series_spawn_plan", "_SeriesSpawnPlan")),
        ):
            for name in names:
                with self.subTest(module=module.__name__, name=name):
                    self.assertFalse(hasattr(module, name))

    def test_the_resolver_protocol_no_longer_resolves_a_tool_repo(self) -> None:
        for name in ("resolve_tool_repo_sha", "build_tool_invocation_cmd"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(scenario.ScenarioResolver, name))
                self.assertFalse(hasattr(cli._DefaultResolver, name))

    def test_the_argv_shim_the_acceptance_harness_uses_stays(self) -> None:
        self.assertTrue(callable(smoke.forge_claude_shim))
        self.assertTrue(callable(smoke.read_argv_log))

    def test_the_seven_whole_files_are_deleted(self) -> None:
        for relative in REMOVED_FILES:
            with self.subTest(file=relative):
                self.assertFalse((ENGINE / relative).exists())


# ---------------------------------------------------------------------------
# A series arm is refused
# ---------------------------------------------------------------------------


def _arm(name: str, *, strategy: str, tools: str = "") -> str:
    return (
        f'name = "{name}"\nadapter = "claude-cli"\nmodel = "claude-haiku-5-5"\n'
        f'strategy = "{strategy}"\neffort = "low"\n{tools}'
    )


class ASeriesArmIsRefusedTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)

    def test_a_repo_tools_source_does_not_load_and_the_message_says_why(self) -> None:
        arm = self.base / "repo.toml"
        arm.write_text(
            _arm(
                "armed", strategy="single-session", tools='[tools]\nsource = "repo"\nrepo = "x"\n'
            ),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError) as caught:
            scenario.load_scenario(arm)
        message = str(caught.exception)
        for word in ("repo", "series", "0.13.0", "remove", "none"):
            self.assertIn(word, message)

    def test_a_none_tools_source_still_loads(self) -> None:
        arm = self.base / "none.toml"
        arm.write_text(
            _arm("plain", strategy="single-session", tools='[tools]\nsource = "none"\n'),
            encoding="utf-8",
        )
        self.assertEqual(scenario.load_scenario(arm).tools.source, "none")

    def test_the_strategy_name_alone_loads_and_the_run_refuses_it(self) -> None:
        root = self.base / "data-root"
        shutil.copytree(
            ENGINE / "examples" / "data-root",
            root,
            ignore=shutil.ignore_patterns("__pycache__", "report"),
        )
        arms = root / "scenarios" / "mixed"
        arms.mkdir()
        (arms / "plain.toml").write_text(
            _arm("plain", strategy="single-session", tools='[tools]\nallowed = ["Read"]\n'),
            encoding="utf-8",
        )
        retired = arms / "retired.toml"
        retired.write_text(_arm("retired", strategy="series"), encoding="utf-8")
        # Loading checks no strategy, so the refusal is the run's.
        self.assertEqual(scenario.load_scenario(retired).strategy, "series")

        out, err = io.StringIO(), io.StringIO()
        argv = ["--home", str(root), "run", "example", "--dry-run", "--scenarios-dir", str(arms)]
        env = {k: v for k, v in os.environ.items() if k != "FATHOM_HOME"}
        with (
            contextlib.chdir(self.base),
            mock.patch.dict(os.environ, env, clear=True),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            code = main(argv)
        self.assertNotEqual(code, 0, out.getvalue())
        self.assertRegex(err.getvalue(), r"unknown strategy.*series")

    def test_the_executor_factory_refuses_it(self) -> None:
        arm = self.base / "retired.toml"
        arm.write_text(_arm("retired", strategy="series"), encoding="utf-8")

        class _Resolver:
            def resolve_model_id(self, model: str) -> str | None:
                return None

            def resolve_plugin_meta(self, plugin_dir: str) -> tuple[str, str, str]:
                raise AssertionError("no plugin is mounted")

        resolved = scenario.resolve_scenario(scenario.load_scenario(arm), _Resolver())
        with self.assertRaises(ValueError) as caught:
            cli._default_executor_factory(resolved)
        self.assertIn("series", str(caught.exception))


# ---------------------------------------------------------------------------
# The smoke gate without its engine group
# ---------------------------------------------------------------------------


class _StubProbes:
    """The probes of the seven groups that remain, and no engine probe."""

    def __init__(self) -> None:
        from fathom.adapters.base import ExitStatus, RunRecord
        from fathom.credentials import CredentialStatus
        from fathom.smoke import CANARY_SKILL, INJECTION_CANARY, MEMORY_INSIDE_CANARY

        ok = RunRecord(status=ExitStatus.OK, num_turns=2, tokens_in=10, tokens_out=5)
        now_ms = int(__import__("time").time() * 1000)
        self._credential = CredentialStatus(
            found=True,
            readable=True,
            expires_at_ms=now_ms + 3600_000,
            refresh_expires_at_ms=now_ms + 30 * 86400_000,
        )
        self._ok = ok
        self._injection = (
            ["claude", "--append-system-prompt-file", "/skill.md"],
            RunRecord(status=ExitStatus.OK, num_turns=1, result_text=f"hi {INJECTION_CANARY}"),
        )
        self._memory = RunRecord(
            status=ExitStatus.OK, num_turns=1, result_text=f"hi {MEMORY_INSIDE_CANARY}"
        )
        self._treatment = [CANARY_SKILL, "other:skill"]

    def credential_status(self):
        return self._credential

    def isolated_config_contents(self):
        return [".credentials.json"]

    def authed_spawn(self):
        return self._ok

    def deny_spawn(self):
        return [], self._ok

    def injection_spawn(self):
        return self._injection

    def memory_spawn(self):
        return self._memory

    def mount_treatment_skills(self):
        return self._treatment

    def mount_control_skills(self):
        return ["other:skill"]


class TheSmokeGateHasNoEngineGroupTests(unittest.TestCase):
    def test_it_reports_eleven_checks_and_names_no_engine_boundary(self) -> None:
        out = io.StringIO()
        code = smoke.run_smoke(_StubProbes(), out=out)
        text = out.getvalue()
        self.assertEqual(code, 0, text)
        self.assertIn("(11/11 checks)", text)
        self.assertNotIn("engine-boundary", text)

    def test_the_engine_group_has_no_parameter_left(self) -> None:
        self.assertNotIn("include_engine", inspect.signature(smoke.run_smoke).parameters)
        probes = inspect.signature(smoke.RealProbes).parameters
        self.assertNotIn("scenarios_dir", probes)
        self.assertNotIn("engine_timeout_s", probes)

    def test_the_probe_protocol_has_no_engine_probe(self) -> None:
        self.assertFalse(hasattr(smoke.SmokeProbes, "engine_spawn_argvs"))
        self.assertFalse(hasattr(smoke.RealProbes, "engine_spawn_argvs"))

    def test_the_module_docstring_counts_the_groups_that_remain(self) -> None:
        doc = smoke.__doc__ or ""
        self.assertIn("Seven assertion", doc)
        self.assertIn("(0 to 6)", doc)
        numbered = re.findall(r"^(\d)\. \*\*", doc, re.M)
        self.assertEqual(numbered, [str(n) for n in range(7)])


# ---------------------------------------------------------------------------
# The authoring guide
# ---------------------------------------------------------------------------


def _first_cells_of_table(text: str, header: str) -> list[str]:
    """The first-column cells, without backticks, of the table headed by *header*."""
    rows = text.splitlines()
    for start, line in enumerate(rows):
        cells = [c.strip().strip("`").strip() for c in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and cells and cells[0] == header:
            found: list[str] = []
            for row in rows[start + 2 :]:
                if not row.lstrip().startswith("|"):
                    break
                found.append(row.strip().strip("|").split("|")[0].strip().strip("`").strip())
            return found
    raise AssertionError(f"no table whose first header cell is {header!r}")


class TheGuideSaysSoTests(unittest.TestCase):
    def test_section_twelve_is_a_retired_stub(self) -> None:
        text = ARMING.read_text(encoding="utf-8")
        self.assertIn("## 12. Series arms (retired)", text.splitlines())
        stub = text.split("## 12. Series arms (retired)", 1)[1]
        self.assertLess(len(stub.strip().splitlines()), 12, "a stub, not the old section")

    def test_both_strategy_tables_list_exactly_the_known_strategies(self) -> None:
        for path in (SKILL, ARMING):
            with self.subTest(file=path.name):
                listed = _first_cells_of_table(path.read_text(encoding="utf-8"), "strategy")
                self.assertEqual(sorted(listed), sorted(REMAINING_STRATEGIES))
                self.assertEqual(set(listed), set(KNOWN_STRATEGIES))

    def test_the_skill_description_lists_no_series_strategy(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        description = text.split("---", 2)[1]
        self.assertNotRegex(description, r"reprompt-session,\s*series")
        self.assertNotRegex(description, r"as the series arm|series strategy")


# ---------------------------------------------------------------------------
# The closing greps
# ---------------------------------------------------------------------------

# Everything the retirement names, in any case. A line matching it must say the thing is
# retired (or that the flag is ignored), on the prose surface and in the code alike.
PHRASES = re.compile(
    "|".join(
        (
            r"series arm",
            r"series strategy",
            r"series engine",
            r"series-engine",
            r"engine-boundary",
            r"engine boundary",
            r"`series`",
            r"series trial",
            r"multi-PR series",
            r"reprompt-session, series",
            r"series executor",
            r"series-toml-skeleton",
            r"series-engine-contract",
            r'strategy *= *"series"',
            r'source *= *"repo"',
        )
    ),
    re.IGNORECASE,
)
FLAG = re.compile(r"--no-engine-boundary|no_engine_boundary")
FLAG_LITERALS = ('"--no-engine-boundary"', "no_engine_boundary")

PROSE_FILES = ("README.md", "README-plugin.md", "CLAUDE.md", "CONTRIBUTING.md", "mcp/README.md")
PROSE_DIRS = ("commands", "skills", "docs")
PROSE_SKIPPED = ("docs/specs/", "docs/adr/", "docs/backlog.md")
SKIPPED_PARTS = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache", ".ruff_cache"}


def _files(*roots: str, suffix: str | None = None) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        base = ENGINE / root
        paths = [base] if base.is_file() else sorted(base.rglob("*")) if base.is_dir() else []
        for path in paths:
            if not path.is_file() or SKIPPED_PARTS & set(path.relative_to(ENGINE).parts):
                continue
            if suffix is None or path.suffix == suffix:
                found.append(path)
    return found


def _lines(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    yield from enumerate(text.splitlines(), 1)


def _relative(path: Path) -> str:
    return path.relative_to(ENGINE).as_posix()


def _prose_surface() -> list[Path]:
    paths = _files(*PROSE_FILES, *PROSE_DIRS)
    return [p for p in paths if not _relative(p).startswith(PROSE_SKIPPED)]


def _code_surface() -> list[Path]:
    mcp_modules = sorted((ENGINE / "mcp").glob("*.py"))
    return [*_files("src", "tools"), *mcp_modules]


class TheClosingGrepsTests(unittest.TestCase):
    def test_a_prose_line_naming_the_retired_thing_says_it_is_retired(self) -> None:
        bad = []
        for path in _prose_surface():
            for number, line in _lines(path):
                names_it = PHRASES.search(line) and not FLAG.search(line)
                if names_it and "retired" not in line and "0.13.0" not in line:
                    bad.append(f"{_relative(path)}:{number}: {line.strip()}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_a_line_naming_the_flag_says_it_is_ignored_or_retired(self) -> None:
        bad = []
        for path in _prose_surface():
            for number, line in _lines(path):
                if FLAG.search(line) and "ignored" not in line and "retired" not in line:
                    bad.append(f"{_relative(path)}:{number}: {line.strip()}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_the_arming_guide_names_the_retired_thing_only_in_section_twelve(self) -> None:
        bad = []
        section = None
        for number, line in _lines(ARMING):
            heading = re.match(r"## (\d+)\.", line)
            if heading:
                section = int(heading.group(1))
            if PHRASES.search(line) and section != 12:
                bad.append(f"arming.md:{number}: {line.strip()}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_a_code_line_naming_the_retired_thing_says_so(self) -> None:
        bad = []
        for path in _code_surface():
            for number, line in _lines(path):
                if PHRASES.search(line) and not (
                    "retired" in line
                    or "0.13.0" in line
                    or any(literal in line for literal in FLAG_LITERALS)
                ):
                    bad.append(f"{_relative(path)}:{number}: {line.strip()}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_no_code_or_test_outside_this_file_names_a_removed_symbol(self) -> None:
        removed = re.compile(
            "|".join(
                (
                    r"strategies\.series",
                    r"SeriesExecutor",
                    r"EngineOutcome",
                    r"engine_spawn_argvs",
                    r"include_engine",
                    r"resolve_repo_invocation_cmd",
                    r"NON_BYPASS_PERMISSION_MODE",
                    r"_SMOKE_SERIES_TEMPLATE",
                    r"_series_spawn_plan",
                    r"_SeriesSpawnPlan",
                )
            )
        )
        here = Path(__file__).resolve()
        found = []
        for path in _files("src", "tools", "mcp", "tests", suffix=".py"):
            if path.resolve() == here:
                continue
            for number, line in _lines(path):
                if removed.search(line):
                    found.append(f"{_relative(path)}:{number}: {line.strip()}")
        self.assertEqual(found, [], "\n".join(found))


# ---------------------------------------------------------------------------
# What must keep working
# ---------------------------------------------------------------------------


class WhatStaysTests(unittest.TestCase):
    def test_the_preimage_keeps_the_tool_keys_with_empty_values(self) -> None:
        import json

        class _Resolver:
            def resolve_model_id(self, model: str) -> str | None:
                return None

            def resolve_plugin_meta(self, plugin_dir: str) -> tuple[str, str, str]:
                raise AssertionError("no plugin is mounted")

        bare = ENGINE / "tests" / "fixtures" / "scenarios" / "bare.toml"
        resolved = scenario.resolve_scenario(scenario.load_scenario(bare), _Resolver())
        preimage = json.loads(resolved.config_preimage)
        self.assertIsNone(preimage["tool_repo_sha"])
        self.assertIsNone(preimage["tool_invocation_cmd"])
        self.assertIsNone(preimage["tools"]["repo"])
        self.assertEqual(preimage["tools"]["source"], "none")


if __name__ == "__main__":
    unittest.main(verbosity=2)
