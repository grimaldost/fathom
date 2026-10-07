"""Where a command is started does not change what it does.

Every fathom command that reads or writes data resolves one data root (:mod:`fathom.home`):
``--home``, else ``FATHOM_HOME``, else the nearest marked directory at or above the working
directory, else an unmarked working directory that holds data (with a warning). These tests
run the same commands against copies of ``examples/data-root`` from four places — inside the
root, a sibling directory with ``FATHOM_HOME``, a sibling directory with a relative
``--home``, and a directory nested inside the root — and require the same result each time:
the same ledger rows appended to the root's ledger, locks and kept streams under the root's
``.fathom/``, the same scorecard, the same resume keys, and nothing written where the
command was started.

They also pin ``engine_version`` and ``written_at``, the provenance every new ledger row
carries: rows written before either existed read, report, reconcile and resume exactly as
before. ``written_at`` is the moment of writing, so it is the one field that differs between
otherwise identical runs; the cross-location comparison sets it aside.

No spawns: the executor and runner are stubbed, and the arming and credential gates, which
would spawn or read this seat's credential, are skipped with their own flags.

Stdlib only; runs without uv as ``python tests/test_cli_data_root.py``.
"""

from __future__ import annotations

import contextlib
import datetime
import io
import json
import os
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

ENGINE = Path(__file__).resolve().parent.parent
FIXTURE = ENGINE / "examples" / "data-root"
sys.path.insert(0, str(ENGINE / "src"))

# A developer's own FATHOM_HOME must not steer these tests (tests/conftest.py does the same
# under pytest; this covers a bare run).
os.environ.pop("FATHOM_HOME", None)

from fathom import home, ledgerindex  # noqa: E402
from fathom import ledger as _ledger  # noqa: E402
from fathom import reconcile as _reconcile  # noqa: E402
from fathom.adapters.base import ExitStatus  # noqa: E402
from fathom.adapters.base import RunRecord as AdapterRunRecord  # noqa: E402
from fathom.cli import main  # noqa: E402
from fathom.strategies.base import PIN_STRONG, TrialResult, TrialStatus  # noqa: E402

BANK = "example"
MODES = ("inside", "FATHOM_HOME", "--home", "nested")
# Every gate that would spawn or read this seat's credential is skipped by its own flag;
# the lock is kept, because where it lives is part of what is tested.
RUN = ["run", BANK, "--repeats", "3", "--skip-arming-check", "--skip-credential-check"]


def _copy_fixture(base: Path, name: str = "data-root") -> Path:
    root = base / name
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("__pycache__", "report"))
    return root


def _ledger_path(root: Path) -> Path:
    return root / "ledger" / f"{BANK}.jsonl"


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _without_written_at(line: str) -> str:
    """A ledger line with its write time removed, for comparing rows across runs."""
    row = json.loads(line)
    row.pop(_ledger.WRITTEN_AT_KEY)
    return json.dumps(row, sort_keys=True)


def _call(argv: list[str], *, cwd: Path, env: dict[str, str] | None = None):
    """``main(argv)`` from *cwd* with *env* added: (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with (
        contextlib.chdir(cwd),
        mock.patch.dict(os.environ, env or {}),
        contextlib.redirect_stdout(out),
        contextlib.redirect_stderr(err),
    ):
        try:
            code = main(argv)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


def _invoke(mode: str, root: Path, argv: list[str]):
    """Run *argv* against *root*, started from the place *mode* names."""
    elsewhere = root.parent / "elsewhere"
    elsewhere.mkdir(exist_ok=True)
    if mode == "inside":
        return _call(argv, cwd=root)
    if mode == "FATHOM_HOME":
        return _call(argv, cwd=elsewhere, env={"FATHOM_HOME": str(root)})
    if mode == "--home":
        relative = os.path.relpath(root, elsewhere)
        return _call(["--home", relative, *argv], cwd=elsewhere)
    if mode == "nested":
        return _call(argv, cwd=root / "tasks" / BANK / "add")
    raise ValueError(mode)


class _StubExecutor:
    """What an agent and the adapter would leave behind, with nothing spawned.

    It writes the task's reference solution into the workspace, and tees a stream file
    into FATHOM_STREAM_DIR when the run loop set one, as the adapter does.
    """

    def run_trial(self, task, workspace, scenario, runner):
        shutil.copy(Path(task.task_dir) / "solution" / "calc.py", Path(workspace) / "calc.py")
        stream_dir = os.environ.get("FATHOM_STREAM_DIR")
        if stream_dir:
            Path(stream_dir).mkdir(parents=True, exist_ok=True)
            tag = os.environ.get("FATHOM_STREAM_TAG", "untagged")
            (Path(stream_dir) / f"{tag}.ndjson").write_text("{}\n", encoding="utf-8")
        run = AdapterRunRecord(
            status=ExitStatus.OK,
            tokens_in=100,
            tokens_out=50,
            num_turns=3,
            duration_s=10.0,
            cost_usd_est=0.01,
            cli_version="0.0.0 (stub)",
            usage={"input_tokens": 100, "output_tokens": 50},
            model_id="stub-model",
        )
        return TrialResult(
            status=TrialStatus.COMPLETED, runs=[run], pin_level=PIN_STRONG, wall_clock_s=10.0
        )


@contextlib.contextmanager
def _no_spawns():
    with (
        mock.patch("fathom.cli._default_executor_factory", lambda sc, **kw: _StubExecutor()),
        mock.patch("fathom.cli._default_runner_factory", lambda sc, **kw: object()),
    ):
        yield


class SameResultFromAnywhereTests(unittest.TestCase):
    """One paid-path run, one report, one index and one reconcile per starting place."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.results: dict[str, dict] = {}
        base = Path(cls._tmp.name)
        for mode in MODES:
            root = _copy_fixture(base / mode.strip("-").lower())
            before = _lines(_ledger_path(root))
            with _no_spawns():
                run = _invoke(mode, root, RUN)
            report = _invoke(mode, root, ["report", BANK])
            index = _invoke(mode, root, ["index", "--write"])
            reconcile = _invoke(mode, root, ["reconcile"])
            cls.results[mode] = {
                "root": root,
                "before": before,
                "after": _lines(_ledger_path(root)),
                "run": run,
                "report": report,
                "index": index,
                "reconcile": reconcile,
            }

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _each(self):
        for mode, result in self.results.items():
            with self.subTest(mode=mode):
                yield mode, result

    def test_every_command_succeeds(self) -> None:
        for _mode, r in self._each():
            for step in ("run", "report", "index", "reconcile"):
                code, out, err = r[step]
                self.assertEqual(code, 0, f"{step}: {out}{err}")
            self.assertIn(f"data root: {r['root']}", r["run"][1])
            self.assertNotIn("WARNING", r["run"][2], "a marked root draws no warning")

    def test_the_same_rows_are_appended_to_the_roots_own_ledger(self) -> None:
        appended = {}
        for mode, r in self._each():
            self.assertEqual(r["after"][: len(r["before"])], r["before"], "append-only")
            new = r["after"][len(r["before"]) :]
            self.assertEqual(len(new), 4, "two trials, each a run row and a trial row")
            for line in new:
                self.assertIn("written_at", json.loads(line), "every new row is stamped")
            appended[mode] = [_without_written_at(line) for line in new]
        # written_at is the one field that differs by design: it is the moment of writing.
        self.assertEqual(
            len({tuple(rows) for rows in appended.values()}),
            1,
            "identical rows everywhere, apart from when they were written",
        )

    def test_config_hashes_match_the_committed_rows(self) -> None:
        """Where the command runs never enters an arm's identity."""
        for _mode, r in self._each():
            committed = {}
            for line in r["before"]:
                row = json.loads(line)
                if row["kind"] == "trial":
                    committed.setdefault(row["scenario"], row["config_hash"])
            for line in r["after"][len(r["before"]) :]:
                row = json.loads(line)
                if row["kind"] == "trial":
                    self.assertEqual(row["config_hash"], committed[row["scenario"]])

    def test_resume_keys_are_shared_across_starting_places(self) -> None:
        root = self.results["inside"]["root"]
        for mode in MODES:
            with self.subTest(mode=mode):
                code, out, err = _invoke(mode, root, ["run", BANK, "--repeats", "3", "--dry-run"])
                self.assertEqual(code, 0, err)
                self.assertIn("planned:  0 trials (6 already done)", out)

    def test_locks_and_streams_live_under_the_roots_own_fathom_dir(self) -> None:
        for mode, r in self._each():
            root = r["root"]
            self.assertTrue((root / ".fathom" / "locks" / BANK).is_dir())
            streams = sorted(p.name for p in (root / ".fathom" / "streams" / BANK).iterdir())
            self.assertEqual(
                streams,
                [f"{BANK}--bare--add--r2.ndjson", f"{BANK}--nudge--add--r2.ndjson"],
            )
            started_in = {
                "inside": root,
                "FATHOM_HOME": root.parent / "elsewhere",
                "--home": root.parent / "elsewhere",
                "nested": root / "tasks" / BANK / "add",
            }[mode]
            if started_in != root:
                for stray in (".fathom", "ledger", "report", "docs"):
                    self.assertFalse((started_in / stray).exists(), f"{stray} beside the caller")

    def test_the_same_scorecard_is_written_in_the_root(self) -> None:
        cards = {}
        for mode, r in self._each():
            card = r["root"] / "report" / f"scorecard-{BANK}.md"
            self.assertIn(str(card), r["report"][1])
            cards[mode] = card.read_bytes()
        self.assertEqual(len(set(cards.values())), 1)

    def test_the_index_is_rewritten_in_the_root_and_reconciles(self) -> None:
        for _mode, r in self._each():
            self.assertTrue(ledgerindex.is_current(r["root"]))
            self.assertIn(f"reconciling the data root at {r['root']}", r["reconcile"][1])
            self.assertIn("RECONCILE: OK", r["reconcile"][1])

    def test_new_rows_record_when_they_were_written(self) -> None:
        for _mode, r in self._each():
            for line in r["after"][len(r["before"]) :]:
                stamp = datetime.datetime.fromisoformat(json.loads(line)["written_at"])
                self.assertEqual(stamp.utcoffset(), datetime.timedelta(0))

    def test_new_run_rows_name_their_scenario(self) -> None:
        for _mode, r in self._each():
            runs = [json.loads(line) for line in r["after"][len(r["before"]) :]]
            runs = [row for row in runs if row["kind"] == "run"]
            self.assertEqual(len(runs), 2)
            for row in runs:
                self.assertTrue(row["scenario"], "an arm name, not the legacy empty default")

    def test_new_rows_record_the_engine_version(self) -> None:
        for _mode, r in self._each():
            for line in r["after"][len(r["before"]) :]:
                self.assertEqual(json.loads(line)["engine_version"], _ledger.engine_version())


class PrecedenceTests(unittest.TestCase):
    """--home, then FATHOM_HOME, then the walk up, then an unmarked working directory."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.a = _copy_fixture(base, "a")
        self.b = _copy_fixture(base, "b")
        self.plain = base / "plain"
        self.plain.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _root_of(self, argv: list[str], *, cwd: Path, env: dict[str, str] | None = None):
        code, out, err = _call([*argv, "run", BANK, "--dry-run"], cwd=cwd, env=env)
        return code, out, err

    def test_home_beats_fathom_home(self) -> None:
        code, out, err = self._root_of(
            ["--home", str(self.b)], cwd=self.a, env={"FATHOM_HOME": str(self.a)}
        )
        self.assertEqual(code, 0, err)
        self.assertIn(f"data root: {self.b}", out)

    def test_fathom_home_beats_the_walk_up(self) -> None:
        code, out, err = self._root_of([], cwd=self.a / "ledger", env={"FATHOM_HOME": str(self.b)})
        self.assertEqual(code, 0, err)
        self.assertIn(f"data root: {self.b}", out)

    def test_a_named_root_that_is_not_one_is_an_error_not_a_fall_through(self) -> None:
        """Inside a good root, a bad FATHOM_HOME still stops the command."""
        code, out, err = self._root_of([], cwd=self.a, env={"FATHOM_HOME": str(self.plain)})
        self.assertEqual(code, 1, out + err)
        self.assertIn("FATHOM_HOME names", err)
        self.assertIn("fathom init", err)
        self.assertNotIn("data root:", out)

    def test_nothing_found_says_how_to_make_or_name_one(self) -> None:
        code, _out, err = self._root_of([], cwd=self.plain)
        self.assertEqual(code, 1, err)
        for phrase in ("no fathom data root found", "fathom init", "--home", "FATHOM_HOME"):
            self.assertIn(phrase, err)

    def test_explicit_paths_are_relative_to_where_the_command_started(self) -> None:
        """--ledger-dir given from elsewhere means elsewhere; left out, it means the root's."""
        elsewhere = self.plain
        code, out, err = _call(
            ["--home", str(self.a), "run", BANK, "--dry-run", "--ledger-dir", "scratch-ledger"],
            cwd=elsewhere,
        )
        self.assertEqual(code, 0, err)
        self.assertIn("planned:  4 trials (0 already done)", out, "a fresh, empty ledger dir")
        code, out, err = _call(
            ["--home", str(self.a), "run", BANK, "--dry-run", "--scenarios-dir", "nowhere"],
            cwd=elsewhere,
        )
        self.assertEqual(code, 1)
        self.assertIn(str(elsewhere / "nowhere"), err)

    def test_a_relative_stream_dir_is_relative_to_where_the_command_started(self) -> None:
        elsewhere = self.plain
        with _no_spawns():
            code, out, err = _call(
                ["--home", str(self.a), *RUN, "--limit", "1"],
                cwd=elsewhere,
                env={"FATHOM_STREAM_DIR": "kept-streams"},
            )
        self.assertEqual(code, 0, out + err)
        self.assertTrue((elsewhere / "kept-streams").is_dir())
        self.assertFalse((self.a / "kept-streams").exists())

    def test_an_empty_home_is_an_error_not_a_fall_through(self) -> None:
        """`fathom --home "$DATA" run` with DATA unset must not run against another root."""
        code, out, err = _call(
            ["--home", "", "run", BANK, "--dry-run"],
            cwd=self.plain,
            env={"FATHOM_HOME": str(self.a)},
        )
        self.assertEqual(code, 1, out + err)
        self.assertIn("--home was given an empty value", err)
        self.assertNotIn("data root:", out)
        code, out, err = _call(["--home", " ", "reconcile"], cwd=self.a)
        self.assertEqual(code, 13, out + err)
        self.assertIn("--home was given an empty value", err)
        self.assertNotIn("RECONCILE", out)
        code, out, err = _call(["--home", "", "index", "--write"], cwd=self.a)
        self.assertEqual(code, 2, out + err)
        self.assertIn("--home was given an empty value", err)

    def test_a_data_root_of_a_later_schema_is_refused(self) -> None:
        (self.b / "fathom.toml").write_text("[data_root]\nschema = 2\n", encoding="utf-8")
        for argv, cwd, env, expected in (
            (["run", BANK, "--dry-run"], self.plain, {"FATHOM_HOME": str(self.b)}, 1),
            (["--home", str(self.b), "report", BANK], self.plain, None, 1),
            (["reconcile"], self.b / "tasks", None, 13),
            (["index"], self.b, None, 2),
        ):
            with self.subTest(argv=argv):
                code, out, err = _call(argv, cwd=cwd, env=env)
                self.assertEqual(code, expected, out + err)
                self.assertIn("schema = 2", err)
                self.assertIn("Upgrade fathom", err)

    def test_a_trial_spawn_does_not_inherit_fathom_home(self) -> None:
        """FATHOM_HOME names the data root, which holds each task's reference solution and
        verifier; an agent that could read its environment would find them there."""
        from fathom.adapters.claude_cli import make_spawn_env

        seen: list[tuple[bool, str | None]] = []

        class _Recording(_StubExecutor):
            def run_trial(self, task, workspace, scenario, runner):
                seen.append(("FATHOM_HOME" in make_spawn_env("cfg"), os.environ.get("FATHOM_HOME")))
                return super().run_trial(task, workspace, scenario, runner)

        out, err = io.StringIO(), io.StringIO()
        with (
            mock.patch("fathom.cli._default_executor_factory", lambda sc, **kw: _Recording()),
            mock.patch("fathom.cli._default_runner_factory", lambda sc, **kw: object()),
            contextlib.chdir(self.plain),
            mock.patch.dict(os.environ, {"FATHOM_HOME": str(self.a)}),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            code = main([*RUN, "--limit", "1"])
            after = os.environ.get("FATHOM_HOME")
        self.assertEqual(code, 0, out.getvalue() + err.getvalue())
        self.assertEqual(seen, [(False, None)])
        self.assertEqual(after, str(self.a), "the variable is restored once the command ends")


class RelativePathMissTests(unittest.TestCase):
    """A relative path option that misses under the working directory names the data root's."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.root = _copy_fixture(base)
        self.plain = base / "plain"
        self.plain.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_a_missing_scenarios_dir_names_the_data_roots(self) -> None:
        code, out, err = _call(
            ["--home", str(self.root), "run", BANK, "--dry-run", "--scenarios-dir", "scenarios"],
            cwd=self.plain,
        )
        self.assertEqual(code, 1, out + err)
        self.assertIn(str(self.root / "scenarios"), err)
        self.assertIn("did you mean", err)
        self.assertIn("is relative to the working directory", err)

    def test_the_same_through_fathom_home(self) -> None:
        code, out, err = _call(
            ["run", BANK, "--dry-run", "--scenarios-dir", "scenarios"],
            cwd=self.plain,
            env={"FATHOM_HOME": str(self.root)},
        )
        self.assertEqual(code, 1, out + err)
        self.assertIn(str(self.root / "scenarios"), err)

    def test_a_missing_tasks_dir_names_the_data_roots(self) -> None:
        for command in ("validate", "run"):
            with self.subTest(command=command):
                argv = ["--home", str(self.root), command, BANK, "--tasks-dir", "tasks"]
                if command == "run":
                    argv.append("--dry-run")
                code, out, err = _call(argv, cwd=self.plain)
                self.assertEqual(code, 1, out + err)
                self.assertIn(str(self.root / "tasks"), err)
                self.assertIn("could not load bank", err)

    def test_a_relative_path_that_exists_gets_no_note(self) -> None:
        (self.plain / "scenarios").mkdir()
        code, out, err = _call(
            ["--home", str(self.root), "run", BANK, "--dry-run", "--scenarios-dir", "scenarios"],
            cwd=self.plain,
        )
        self.assertEqual(code, 1, out + err)
        self.assertNotIn("did you mean", err)
        self.assertNotIn("is relative to the working directory", err)

    def test_a_path_missing_in_both_places_gets_no_note(self) -> None:
        code, out, err = _call(
            ["--home", str(self.root), "run", BANK, "--dry-run", "--scenarios-dir", "nowhere"],
            cwd=self.plain,
        )
        self.assertEqual(code, 1, out + err)
        self.assertNotIn("did you mean", err)
        self.assertNotIn("is relative to the working directory", err)

    def test_an_absolute_path_and_an_omitted_option_get_no_note(self) -> None:
        missing = str(self.plain / "absent")
        for extra in (["--scenarios-dir", missing], []):
            with self.subTest(extra=extra):
                _code, _out, err = _call(
                    ["--home", str(self.root), "run", BANK, "--dry-run", *extra],
                    cwd=self.plain,
                )
                self.assertNotIn("did you mean", err)
                self.assertNotIn("is relative to the working directory", err)

    def test_from_inside_the_root_nothing_is_noted(self) -> None:
        code, out, err = _call(
            ["run", BANK, "--dry-run", "--scenarios-dir", "nowhere"], cwd=self.root
        )
        self.assertEqual(code, 1, out + err)
        self.assertNotIn("did you mean", err)


class ValidateGatePathTests(unittest.TestCase):
    """`fathom validate` reads the data root's arms and refuses a gate path that dangles.

    End to end on a copy of the example data root: real staging, the example's real
    verifier, and the arms loaded from its `scenarios/` (FATH-B54).
    """

    _PROBE_ARM = """\
name = "probe"
adapter = "claude-cli"
model = "claude-haiku-4-5"
strategy = "gated-session"
effort = "low"

[tools]
source = "none"
allowed = ["Read", "Write", "Edit", "Glob", "Grep"]

[gate]
extra = ["python ${task_dir}/probe.py"]
"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _copy_fixture(Path(self._tmp.name))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _validate(self) -> tuple[int, str]:
        code, out, err = _call(["--home", str(self.root), "validate", BANK], cwd=self.root)
        return code, out + err

    def test_the_example_data_root_validates_with_no_gate_path_check(self) -> None:
        code, out = self._validate()
        self.assertEqual(code, 0, out)
        self.assertNotIn("gate commands name paths", out)

    def test_an_arm_extra_naming_a_missing_probe_is_refused_with_exit_12(self) -> None:
        (self.root / "scenarios" / "probe.toml").write_text(self._PROBE_ARM, encoding="utf-8")
        code, out = self._validate()
        self.assertEqual(code, 12, out)
        self.assertIn("${task_dir}/probe.py", out)
        self.assertIn("arm `probe`", out)

    def test_the_same_arm_validates_once_the_probe_exists(self) -> None:
        (self.root / "scenarios" / "probe.toml").write_text(self._PROBE_ARM, encoding="utf-8")
        (self.root / "tasks" / BANK / "add" / "probe.py").write_text("", encoding="utf-8")
        code, out = self._validate()
        self.assertEqual(code, 0, out)
        self.assertIn("[PASS] gate commands name paths that exist", out)


class EngineVersionTests(unittest.TestCase):
    """Old rows, which carry no engine_version, behave exactly as rows that do."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.old = _copy_fixture(base, "old")
        self.new = _copy_fixture(base, "new")
        rows = [json.loads(line) for line in _lines(_ledger_path(self.old))]
        self.assertFalse(any("engine_version" in row for row in rows), "the fixture predates it")
        _ledger_path(self.new).write_text(
            "".join(
                json.dumps({**row, "engine_version": "9.9.9"}, sort_keys=True) + "\n"
                for row in rows
            ),
            encoding="utf-8",
            newline="\n",
        )
        ledgerindex.write(self.new)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_records_and_resume_keys_are_the_same(self) -> None:
        old = list(_ledger.iter_records(BANK, ledger_dir=self.old / "ledger"))
        new = list(_ledger.iter_records(BANK, ledger_dir=self.new / "ledger"))
        self.assertEqual(old, new)
        self.assertEqual(
            _ledger.completed_keys(BANK, ledger_dir=self.old / "ledger"),
            _ledger.completed_keys(BANK, ledger_dir=self.new / "ledger"),
        )
        for root in (self.old, self.new):
            with self.subTest(root=root.name):
                code, out, err = _call(["run", BANK, "--dry-run"], cwd=root)
                self.assertEqual(code, 0, err)
                self.assertIn("planned:  0 trials (4 already done)", out)

    def test_the_scorecard_is_the_same(self) -> None:
        for root in (self.old, self.new):
            code, out, err = _call(["report", BANK], cwd=root)
            self.assertEqual(code, 0, out + err)
        self.assertEqual(
            (self.old / "report" / f"scorecard-{BANK}.md").read_bytes(),
            (self.new / "report" / f"scorecard-{BANK}.md").read_bytes(),
        )

    def test_reconcile_finds_the_same(self) -> None:
        old, new = _reconcile.run(self.old), _reconcile.run(self.new)
        self.assertTrue(old.ok and new.ok)
        self.assertEqual(old.found, new.found)
        self.assertEqual(old.excused, new.excused)
        self.assertEqual(_reconcile.preimage_coverage(self.old), (10, 10))
        self.assertEqual(_reconcile.preimage_coverage(self.new), (10, 10))

    def test_it_never_enters_the_hash_or_the_resume_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            trial = _ledger.TrialRecord(
                bank=BANK,
                task_id="add",
                repeat=0,
                status="completed",
                dataset_version="1",
                config_hash="c" * 64,
                tool_git_sha="",
                cli_version="",
                pin_level=PIN_STRONG,
            )
            _ledger.append_record(BANK, trial, ledger_dir=d)
            _ledger.append_record(BANK, {**trial.__dict__, "engine_version": "1.2.3"}, ledger_dir=d)
            rows = [json.loads(line) for line in _lines(d / f"{BANK}.jsonl")]
            self.assertEqual(rows[0]["engine_version"], _ledger.engine_version())
            self.assertEqual(rows[1]["engine_version"], "1.2.3", "an explicit value is kept")
            self.assertEqual(len(_ledger.completed_keys(BANK, ledger_dir=d)), 1)
            self.assertNotIn("engine_version", set(trial.__dataclass_fields__))


class WrittenAtTests(unittest.TestCase):
    """Old rows, which carry no written_at or scenario, behave exactly as rows that do."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.old = _copy_fixture(base, "old")
        self.new = _copy_fixture(base, "new")
        rows = [json.loads(line) for line in _lines(_ledger_path(self.old))]
        self.assertFalse(any("written_at" in row for row in rows), "the fixture predates it")
        _ledger_path(self.new).write_text(
            "".join(
                json.dumps({**row, "written_at": "2031-01-02T03:04:05+00:00"}, sort_keys=True)
                + "\n"
                for row in rows
            ),
            encoding="utf-8",
            newline="\n",
        )
        ledgerindex.write(self.new)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_records_and_resume_keys_are_the_same(self) -> None:
        old = list(_ledger.iter_records(BANK, ledger_dir=self.old / "ledger"))
        new = list(_ledger.iter_records(BANK, ledger_dir=self.new / "ledger"))
        self.assertEqual(old, new)
        self.assertEqual(
            _ledger.completed_keys(BANK, ledger_dir=self.old / "ledger"),
            _ledger.completed_keys(BANK, ledger_dir=self.new / "ledger"),
        )
        for root in (self.old, self.new):
            with self.subTest(root=root.name):
                code, out, err = _call(["run", BANK, "--dry-run"], cwd=root)
                self.assertEqual(code, 0, err)
                self.assertIn("planned:  0 trials (4 already done)", out)

    def test_the_scorecard_is_the_same(self) -> None:
        for root in (self.old, self.new):
            code, out, err = _call(["report", BANK], cwd=root)
            self.assertEqual(code, 0, out + err)
        self.assertEqual(
            (self.old / "report" / f"scorecard-{BANK}.md").read_bytes(),
            (self.new / "report" / f"scorecard-{BANK}.md").read_bytes(),
        )

    def test_reconcile_finds_the_same(self) -> None:
        old, new = _reconcile.run(self.old), _reconcile.run(self.new)
        self.assertTrue(old.ok and new.ok)
        self.assertEqual(old.found, new.found)
        self.assertEqual(old.excused, new.excused)
        self.assertEqual(_reconcile.preimage_coverage(self.new), (10, 10))

    def test_it_never_enters_the_hash_or_the_resume_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            trial = _ledger.TrialRecord(
                bank=BANK,
                task_id="add",
                repeat=0,
                status="completed",
                dataset_version="1",
                config_hash="c" * 64,
                tool_git_sha="",
                cli_version="",
                pin_level=PIN_STRONG,
            )
            _ledger.append_record(BANK, trial, ledger_dir=d)
            stamp = "2031-01-02T03:04:05+00:00"
            _ledger.append_record(BANK, {**trial.__dict__, "written_at": stamp}, ledger_dir=d)
            rows = [json.loads(line) for line in _lines(d / f"{BANK}.jsonl")]
            datetime.datetime.fromisoformat(rows[0]["written_at"])
            self.assertEqual(rows[1]["written_at"], stamp, "an explicit value is kept")
            self.assertEqual(len(_ledger.completed_keys(BANK, ledger_dir=d)), 1)
            self.assertEqual(rows[0]["config_hash"], rows[1]["config_hash"])
            self.assertNotIn("written_at", set(trial.__dataclass_fields__))


class InitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_it_creates_a_data_root_that_every_command_finds(self) -> None:
        code, out, err = _call(["init", "evals"], cwd=self.base)
        self.assertEqual(code, 0, err)
        root = self.base / "evals"
        config = tomllib.loads((root / "fathom.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["data_root"], {"schema": 1})
        for sub in ("tasks", "scenarios", "ledger", "docs/reports"):
            self.assertTrue((root / sub).is_dir(), sub)
        ignored = _lines(root / ".gitignore")
        self.assertIn(".fathom/", ignored)
        self.assertIn("report/", ignored)
        attributes = _lines(root / ".gitattributes")
        for pattern in ("*.md", "*.toml", "*.py", "*.json", "*.jsonl"):
            self.assertIn(f"{pattern} text eol=lf", attributes)
        for name in ("fathom.toml", ".gitignore", ".gitattributes"):
            self.assertNotIn(b"\r\n", (root / name).read_bytes(), name)
        self.assertIn("Next steps", out)
        self.assertIn("fathom validate", out)
        found = home.resolve(None, env={}, cwd=root / "tasks")
        self.assertEqual((found.path, found.marked), (root, True))
        code, out, err = _call(["reconcile"], cwd=root / "scenarios")
        self.assertEqual(code, 0, out + err)
        self.assertIn("RECONCILE: OK", out)

    def test_it_never_overwrites_a_file(self) -> None:
        root = self.base / "evals"
        root.mkdir()
        (root / ".gitignore").write_text("*.log\n", encoding="utf-8")
        code, out, err = _call(["init"], cwd=root)
        self.assertEqual(code, 0, err)
        self.assertEqual((root / ".gitignore").read_text(encoding="utf-8"), "*.log\n")
        self.assertIn("kept     .gitignore", out)
        self.assertIn("does not list .fathom/, report/", out)
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        code, out, _ = _call(["init", str(root)], cwd=self.base)
        self.assertEqual(code, 0)
        self.assertEqual(before, {p: p.read_bytes() for p in root.rglob("*") if p.is_file()})
        self.assertNotIn("created", out)

    def test_home_names_the_target_and_fathom_home_does_not(self) -> None:
        target = self.base / "named"
        code, _, err = _call(["--home", str(target), "init"], cwd=self.base)
        self.assertEqual(code, 0, err)
        self.assertTrue((target / "fathom.toml").is_file())

        other = self.base / "other"
        other.mkdir()
        code, out, err = _call(["init"], cwd=other, env={"FATHOM_HOME": str(target)})
        self.assertEqual(code, 0, err)
        self.assertTrue((other / "fathom.toml").is_file(), "init works where it is started")
        self.assertIn("FATHOM_HOME is set", out, "and says the variable still wins")

    def test_it_refuses_what_it_must_not_touch(self) -> None:
        engine = self.base / "engine"
        (engine / "src" / "fathom").mkdir(parents=True)
        (engine / "pyproject.toml").write_text(
            '[project]\nname = "fathom"\nversion = "0.0.0"\n', encoding="utf-8"
        )
        unmarked = self.base / "unmarked"
        unmarked.mkdir()
        (unmarked / "fathom.toml").write_text("[other]\nkey = 1\n", encoding="utf-8")
        wide = self.base / "wide"
        wide.mkdir()
        (wide / "fathom.toml").write_bytes("[data_root]\nschema = 1\n".encode("utf-16"))
        cases = {
            engine: "engine checkout",
            unmarked: "has no [data_root] table",
            wide: "UTF-16",
        }
        for target, phrase in cases.items():
            with self.subTest(target=target.name):
                before = sorted(p.name for p in target.rglob("*"))
                code, _, err = _call(["init", str(target)], cwd=self.base)
                self.assertEqual(code, 1, err)
                self.assertIn(phrase, err)
                self.assertEqual(sorted(p.name for p in target.rglob("*")), before)

    def test_it_refuses_a_directory_inside_an_engine_checkout(self) -> None:
        """A data root inside the engine's working tree is one `git add` from publication."""
        engine = self.base / "engine"
        (engine / "src" / "fathom").mkdir(parents=True)
        (engine / "pyproject.toml").write_text(
            '[project]\nname = "fathom"\nversion = "0.0.0"\n', encoding="utf-8"
        )
        code, out, err = _call(["init", "my-evals"], cwd=engine)
        self.assertEqual(code, 1, out + err)
        self.assertIn("inside the fathom engine checkout", err)
        self.assertFalse((engine / "my-evals").exists())

    def test_an_empty_target_is_an_error_not_the_working_directory(self) -> None:
        for argv in (["init", ""], ["--home", "", "init"], ["init", "  "]):
            with self.subTest(argv=argv):
                code, out, err = _call(argv, cwd=self.base)
                self.assertEqual(code, 1, out + err)
                self.assertIn("was given an empty value", err)
                self.assertFalse((self.base / "fathom.toml").exists())

    def test_it_notes_a_data_root_inside_another(self) -> None:
        code, _, err = _call(["init", "outer"], cwd=self.base)
        self.assertEqual(code, 0, err)
        code, out, err = _call(["init", "second"], cwd=self.base / "outer" / "docs")
        self.assertEqual(code, 0, err)
        self.assertIn(f"inside another data root, {self.base / 'outer'}", out)

    def test_it_notes_an_existing_gitattributes_without_the_lf_rule(self) -> None:
        root = self.base / "evals"
        root.mkdir()
        (root / ".gitattributes").write_text("*.md text eol=lf\n", encoding="utf-8")
        code, out, err = _call(["init"], cwd=root)
        self.assertEqual(code, 0, err)
        self.assertEqual(
            (root / ".gitattributes").read_text(encoding="utf-8"), "*.md text eol=lf\n"
        )
        self.assertIn("* text=auto eol=lf", out)

    def test_the_next_steps_reach_the_guide_and_the_example_without_a_clone(self) -> None:
        """A tool install has no copy of the repository, so the next steps link it."""
        code, out, err = _call(["init", "evals"], cwd=self.base)
        self.assertEqual(code, 0, err)
        self.assertIn("fathom smoke", out)
        self.assertIn("skills/fathom-eval/reference/authoring.md", out)
        links = [line.strip() for line in out.splitlines() if line.strip().startswith("https://")]
        self.assertEqual(len(links), 2, out)
        self.assertTrue(links[0].endswith("/skills/fathom-eval/reference/authoring.md"), links)
        self.assertTrue(links[1].endswith("/examples/data-root"), links)
        for relative in ("skills/fathom-eval/reference/authoring.md", "examples/data-root"):
            self.assertTrue((ENGINE / relative).exists(), f"the link to {relative} is dead")


class SmokeFindsItsDataRootTests(unittest.TestCase):
    """Only the engine-boundary check reads data, so only it needs a data root.

    ``run_smoke`` and ``RealProbes`` are replaced: nothing spawns and no credential is read.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.root = _copy_fixture(self.base)
        self.seen: dict = {}

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _smoke(
        self,
        argv: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        smoke_args: tuple[str, ...] = (),
    ):
        seen = self.seen

        class _Probes:
            def __init__(self, *, scenarios_dir=None, **kw) -> None:
                seen["scenarios_dir"] = scenarios_dir

        def _run_smoke(probes, *, force_fail=False, include_engine=True, **kw):
            seen["cwd"] = Path.cwd()
            seen["include_engine"] = include_engine
            # The smoke spawns copy this environment; FATHOM_HOME must not reach them.
            seen["FATHOM_HOME"] = os.environ.get("FATHOM_HOME")
            return 0

        with (
            mock.patch("fathom.smoke.RealProbes", _Probes),
            mock.patch("fathom.smoke.run_smoke", _run_smoke),
        ):
            return _call([*argv, "smoke", *smoke_args], cwd=cwd, env=env)

    def test_a_data_root_found_from_anywhere_is_the_one_read(self) -> None:
        for mode, (argv, cwd, env) in {
            "inside": ([], self.root / "tasks", None),
            "FATHOM_HOME": ([], self.base, {"FATHOM_HOME": str(self.root)}),
            "--home": (["--home", str(self.root)], self.base, None),
        }.items():
            with self.subTest(mode=mode):
                self.seen.clear()
                code, _, err = self._smoke(argv, cwd=cwd, env=env)
                self.assertEqual(code, 0, err)
                self.assertEqual(self.seen["scenarios_dir"], self.root / "scenarios")
                self.assertEqual(self.seen["cwd"], self.root)
                self.assertIsNone(self.seen["FATHOM_HOME"])

    def test_without_a_data_root_the_other_checks_still_run(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        code, _, err = self._smoke([], cwd=plain)
        self.assertEqual(code, 0, err)
        self.assertIsNone(self.seen["scenarios_dir"])
        self.assertTrue(self.seen["include_engine"])

    def test_a_bad_fathom_home_stops_it_only_when_the_root_is_needed(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        bad = {"FATHOM_HOME": str(plain / "absent")}
        code, _, err = self._smoke([], cwd=plain, env=bad)
        self.assertEqual(code, 1, err)
        self.assertIn("FATHOM_HOME names", err)
        self.assertEqual(self.seen, {}, "no probe was built")
        code, _, err = self._smoke([], cwd=plain, env=bad, smoke_args=("--no-engine-boundary",))
        self.assertEqual(code, 0, err)
        self.assertFalse(self.seen["include_engine"])
        self.assertIsNone(self.seen["scenarios_dir"])
        self.assertIsNone(self.seen["FATHOM_HOME"])


if __name__ == "__main__":
    unittest.main()
