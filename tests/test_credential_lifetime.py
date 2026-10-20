"""A matrix outlives the access token it started with (FATH-B55) — stdlib-runnable.

Run directly:  python tests/test_credential_lifetime.py
Run via pytest: uv run pytest tests/test_credential_lifetime.py

Each spawn runs under a throwaway ``CLAUDE_CONFIG_DIR`` holding a copy of the seat's
credential. When the access token has expired, the CLI inside the spawn redeems the
refresh token, which the server then rotates: the old refresh token is spent, and the new
pair is written into the spawn's directory. Before this fix that directory was deleted
with the new pair in it, so the next spawn started again from the seat's original file,
whose refresh token was already spent, and died on auth part-way through the matrix.

No real spawns and no real credential: the subprocess boundary is a stub that plays a
rotating OAuth server against a simulated clock, and ``Path.home`` points at a temporary
directory holding a synthetic credential file.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

os.environ.pop("FATHOM_HOME", None)

from fathom.adapters.base import ExitStatus
from fathom.adapters.claude_cli import ClaudeCliRunner, cleanup_dir
from fathom.credentials import CredentialStore
from fathom.scenario import LimitsOverride, ResolvedScenario, ToolsConfig
from fathom.strategies.series import SeriesExecutor

FIXTURES = Path(__file__).parent / "fixtures"
CREDENTIAL_FILE = ".credentials.json"

HOUR_S = 3600.0
ACCESS_LIFE_S = 1 * HOUR_S
REFRESH_LIFE_S = 30 * 24 * HOUR_S
# Each simulated spawn takes longer than the access token lives, so every spawn after the
# first meets an expired access token and has to refresh.
SPAWN_S = 2 * HOUR_S


class RotatingOAuthSeat:
    """A seat whose refresh tokens are single-use, on a clock the spawns advance.

    ``spawn`` has the signature of the adapter's subprocess seam. It reads the credential
    the spawn was given, refreshes it when the access token has expired (rotating the
    refresh token and writing the new pair back into the spawn's own config dir, as the
    CLI does), and answers with an auth failure when the refresh token it was handed has
    already been redeemed.
    """

    def __init__(self, start_s: float) -> None:
        self.now_s = start_s
        self._serial = 0
        self.live_refresh: set[str] = set()
        self.auth_failures = 0
        self.refreshes = 0
        self.spawns = 0

    def issue(self) -> dict:
        self._serial += 1
        refresh = f"refresh-{self._serial}"
        self.live_refresh.add(refresh)
        return {
            "claudeAiOauth": {
                "accessToken": f"access-{self._serial}",
                "refreshToken": refresh,
                "expiresAt": int((self.now_s + ACCESS_LIFE_S) * 1000),
                "refreshTokenExpiresAt": int((self.now_s + REFRESH_LIFE_S) * 1000),
            }
        }

    def spawn(self, argv, *, input, timeout, env, cwd):
        self.spawns += 1
        path = Path(env["CLAUDE_CONFIG_DIR"]) / CREDENTIAL_FILE
        oauth = json.loads(path.read_text(encoding="utf-8"))["claudeAiOauth"]
        if oauth["expiresAt"] <= self.now_s * 1000:
            if oauth["refreshToken"] not in self.live_refresh:
                self.auth_failures += 1
                return subprocess.CompletedProcess(
                    argv, 1, stdout="", stderr="OAuth token has expired; please run /login"
                )
            self.live_refresh.discard(oauth["refreshToken"])
            self.refreshes += 1
            path.write_text(json.dumps(self.issue()), encoding="utf-8")
        self.now_s += SPAWN_S
        stdout = (FIXTURES / "stream_complete.jsonl").read_text(encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")


def _write_bank(root: Path) -> None:
    bank_dir = root / "tasks" / "b"
    (bank_dir / "t1" / "fixtures").mkdir(parents=True)
    (bank_dir / "t1" / "fixtures" / "README.md").write_text("x\n", encoding="utf-8")
    (bank_dir / "bank.toml").write_text(
        'name = "b"\ndataset_version = "1"\nholdout = []\n', encoding="utf-8"
    )
    (bank_dir / "t1" / "task.toml").write_text(
        'id = "t1"\ninstruction = "x"\n[limits]\ntrial_timeout_s = 60\n'
        '[verify]\nentry = "verify.py"\n',
        encoding="utf-8",
    )
    (bank_dir / "t1" / "verify.py").write_text(
        'import json\nprint(json.dumps({"score": 1.0, "passed": True}))\n', encoding="utf-8"
    )
    sc_dir = root / "scenarios"
    sc_dir.mkdir()
    (sc_dir / "arm.toml").write_text(
        'name = "arm"\nadapter = "claude-cli"\nmodel = "m"\n'
        'strategy = "single-session"\neffort = "high"\n'
        '[tools]\nsource = "none"\nallowed = ["Read"]\n',
        encoding="utf-8",
    )


def _run_args(root: Path, repeats: int) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        command="run",
        bank="b",
        dry_run=False,
        limit=None,
        tasks=None,
        repeats=repeats,
        tasks_dir=root / "tasks",
        scenarios_dir=root / "scenarios",
        ledger_dir=root / "ledger",
        include_holdout=False,
        max_spawn_usd=None,
        legacy_max_budget_usd=None,
        max_run_usd=None,
        skip_bank_validation=True,
        skip_arming_check=True,
        skip_credential_check=False,
        no_lock=True,
        lock_wait_s=None,
    )


class MatrixOutlivesAccessTokenTests(unittest.TestCase):
    """`fathom run` end to end, with only the spawn seam and the home directory stubbed."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="fathom_b55_"))
        self.addCleanup(cleanup_dir, str(self.root))
        self.home = self.root / "home"
        (self.home / ".claude").mkdir(parents=True)
        _write_bank(self.root)
        self.seat = RotatingOAuthSeat(start_s=time.time())
        self.real_credential = self.home / ".claude" / CREDENTIAL_FILE
        self.real_credential.write_text(json.dumps(self.seat.issue()), encoding="utf-8")

    def _run(self, repeats: int) -> tuple[int, str]:
        from fathom.cli import _cmd_run

        out = io.StringIO()
        with (
            mock.patch.object(pathlib.Path, "home", return_value=self.home),
            mock.patch.dict(ClaudeCliRunner.__init__.__kwdefaults__, {"spawn": self.seat.spawn}),
            mock.patch.dict(os.environ, {"FATHOM_STREAM_DIR": str(self.root / "streams")}),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(out),
        ):
            code = _cmd_run(_run_args(self.root, repeats))
        return code, out.getvalue()

    def _ledger_statuses(self) -> list[str]:
        ledger = self.root / "ledger" / "b.jsonl"
        if not ledger.is_file():
            return []
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        return [row["status"] for row in rows if row.get("status")]

    def test_sequential_spawns_carry_the_refreshed_credential_forward(self):
        code, out = self._run(repeats=4)

        self.assertEqual(self.seat.auth_failures, 0, out)
        self.assertEqual(code, 0, out)
        self.assertEqual(self._ledger_statuses(), ["completed"] * 4, out)
        # Spawns 2..4 each met an expired access token and refreshed exactly once, each
        # time with the refresh token the previous refresh issued.
        self.assertEqual(self.seat.refreshes, 3)

    def test_the_seat_file_is_left_as_it_was(self):
        """The run carries the refreshed credential in a copy of its own; writing it back
        to the seat's file is a separate decision this change does not take."""
        before = self.real_credential.read_bytes()
        self._run(repeats=3)
        self.assertEqual(self.real_credential.read_bytes(), before)

    def test_no_copy_of_the_credential_outlives_the_run(self):
        tmp = Path(tempfile.gettempdir())
        before = {p.name for p in tmp.glob("fathom_cred_*")}
        self._run(repeats=2)
        after = {p.name for p in tmp.glob("fathom_cred_*")}
        self.assertEqual(after - before, set())


def _scenario() -> ResolvedScenario:
    return ResolvedScenario(
        name="t",
        adapter="claude-cli",
        model="m",
        strategy="single-session",
        effort="high",
        tools=ToolsConfig(source="none"),
        limits=LimitsOverride(trial_timeout_s=None),
        model_id=None,
        tool_repo_sha=None,
        tool_invocation_cmd=None,
        config_hash="x" * 64,
    )


def _credential(expires_at_s: float, refresh_expires_at_s: float, tag: str) -> str:
    return json.dumps(
        {
            "claudeAiOauth": {
                "accessToken": f"access-{tag}",
                "refreshToken": f"refresh-{tag}",
                "expiresAt": int(expires_at_s * 1000),
                "refreshTokenExpiresAt": int(refresh_expires_at_s * 1000),
            }
        }
    )


class RunnerCarriesTheCredentialTests(unittest.TestCase):
    """The adapter with and without a store, on the same rotating seat."""

    def setUp(self) -> None:
        self.real = Path(tempfile.mkdtemp(prefix="fake_real_cfg_"))
        self.addCleanup(cleanup_dir, str(self.real))
        self.seat = RotatingOAuthSeat(start_s=1_000_000.0)
        (self.real / CREDENTIAL_FILE).write_text(json.dumps(self.seat.issue()), encoding="utf-8")
        self.workspace = Path(tempfile.mkdtemp(prefix="ws_"))
        self.addCleanup(cleanup_dir, str(self.workspace))
        self.config_contents: list[list[str]] = []

    def _spawn(self, argv, *, input, timeout, env, cwd):
        self.config_contents.append(sorted(os.listdir(env["CLAUDE_CONFIG_DIR"])))
        return self.seat.spawn(argv, input=input, timeout=timeout, env=env, cwd=cwd)

    def _three_trials(self, store: CredentialStore | None) -> list[ExitStatus]:
        statuses = []
        for _ in range(3):
            # A runner per trial, as `fathom run` builds one per trial.
            runner = ClaudeCliRunner(
                spawn=self._spawn,
                sleep=lambda _s: None,
                real_config_dir=str(self.real),
                credential_store=store,
            )
            statuses.append(runner.execute("p", self.workspace, _scenario()).status)
        return statuses

    def test_without_a_store_the_spawn_after_a_refresh_dies_on_auth(self):
        """The defect, kept as a test of the stub: what a run did before FATH-B55."""
        self.assertEqual(
            self._three_trials(None), [ExitStatus.OK, ExitStatus.OK, ExitStatus.INFRASTRUCTURE]
        )
        self.assertEqual(self.seat.auth_failures, 1)

    def test_with_a_store_every_spawn_authenticates(self):
        with CredentialStore(self.real) as store:
            self.assertEqual(self._three_trials(store), [ExitStatus.OK] * 3)
        self.assertEqual(self.seat.auth_failures, 0)
        self.assertEqual(self.seat.refreshes, 2)

    def test_the_spawn_config_still_holds_only_the_credential_and_the_isolation_layer(self):
        with CredentialStore(self.real) as store:
            self._three_trials(store)
        self.assertEqual(len(self.config_contents), 3)
        for contents in self.config_contents:
            self.assertEqual(contents, [CREDENTIAL_FILE, "isolation-settings.json"])


class CredentialStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.real = Path(tempfile.mkdtemp(prefix="fake_real_cfg_"))
        self.addCleanup(cleanup_dir, str(self.real))
        self.spawn_dir = Path(tempfile.mkdtemp(prefix="fake_spawn_cfg_"))
        self.addCleanup(cleanup_dir, str(self.spawn_dir))
        self.seat_file = self.real / CREDENTIAL_FILE
        self.seat_file.write_text(_credential(100, 1000, "seat"), encoding="utf-8")

    def _spawn_leaves(self, text: str) -> None:
        (self.spawn_dir / CREDENTIAL_FILE).write_text(text, encoding="utf-8")

    @staticmethod
    def _held(store: CredentialStore) -> str:
        return (Path(store.seed_dir()) / CREDENTIAL_FILE).read_text(encoding="utf-8")

    def test_nothing_is_copied_before_the_first_spawn(self):
        before = {p.name for p in Path(tempfile.gettempdir()).glob("fathom_cred_*")}
        with CredentialStore(self.real) as store:
            self.assertFalse(store.absorb(self.spawn_dir))
            after = {p.name for p in Path(tempfile.gettempdir()).glob("fathom_cred_*")}
        self.assertEqual(after - before, set())

    def test_a_newer_credential_from_a_spawn_is_kept_and_the_seat_is_not_written(self):
        seat_bytes = self.seat_file.read_bytes()
        with CredentialStore(self.real) as store:
            store.seed_dir()
            self._spawn_leaves(_credential(200, 1000, "refreshed"))
            self.assertTrue(store.absorb(self.spawn_dir))
            self.assertIn("refresh-refreshed", self._held(store))
        self.assertEqual(self.seat_file.read_bytes(), seat_bytes)

    def test_an_unchanged_or_older_credential_is_not_taken(self):
        with CredentialStore(self.real) as store:
            store.seed_dir()
            self._spawn_leaves(_credential(100, 1000, "same"))
            self.assertFalse(store.absorb(self.spawn_dir))
            self._spawn_leaves(_credential(50, 1000, "older"))
            self.assertFalse(store.absorb(self.spawn_dir))
            self.assertIn("refresh-seat", self._held(store))

    def test_a_half_written_credential_is_never_carried(self):
        with CredentialStore(self.real) as store:
            store.seed_dir()
            self._spawn_leaves('{"claudeAiOauth": {')
            self.assertFalse(store.absorb(self.spawn_dir))
            self.assertIn("refresh-seat", self._held(store))
            self.assertEqual(os.listdir(store.seed_dir()), [CREDENTIAL_FILE])

    def test_a_new_login_on_the_seat_replaces_the_carried_copy(self):
        """The operator logs in again mid-run, or their own CLI refreshes the seat's file:
        the seat's file is then the newer one, and the next spawn starts from it."""
        with CredentialStore(self.real) as store:
            store.seed_dir()
            self._spawn_leaves(_credential(200, 1000, "refreshed"))
            store.absorb(self.spawn_dir)
            self.seat_file.write_text(_credential(300, 5000, "relogin"), encoding="utf-8")
            self.assertIn("refresh-relogin", self._held(store))

    def test_a_carried_refresh_wins_over_the_older_seat_file(self):
        with CredentialStore(self.real) as store:
            store.seed_dir()
            self._spawn_leaves(_credential(200, 1000, "refreshed"))
            store.absorb(self.spawn_dir)
            self.assertIn("refresh-refreshed", self._held(store))

    def test_close_removes_the_copy(self):
        store = CredentialStore(self.real)
        held = Path(store.seed_dir())
        self.assertTrue((held / CREDENTIAL_FILE).is_file())
        store.close()
        self.assertFalse(held.exists())
        store.close()


class SeriesExecutorCarriesTheCredentialTests(unittest.TestCase):
    """The series engine's spawns share one config dir per trial; the store carries what
    they refreshed on to the next trial's dir."""

    def test_the_trial_config_is_made_from_the_store_and_handed_back_to_it(self):
        real = Path(tempfile.mkdtemp(prefix="fake_real_cfg_"))
        self.addCleanup(cleanup_dir, str(real))
        (real / CREDENTIAL_FILE).write_text(_credential(100, 1000, "seat"), encoding="utf-8")
        sources: list[str | None] = []

        def make_config(source):
            sources.append(source)
            cfg = Path(tempfile.mkdtemp(prefix="fake_series_cfg_"))
            # The engine refreshed the credential during the trial.
            (cfg / CREDENTIAL_FILE).write_text(_credential(200, 1000, "engine"), encoding="utf-8")
            return str(cfg)

        task_dir = Path(tempfile.mkdtemp(prefix="fake_task_"))
        self.addCleanup(cleanup_dir, str(task_dir))
        (task_dir / "series.toml").write_text("[paths]\n", encoding="utf-8")
        task = types.SimpleNamespace(task_dir=str(task_dir), id="t")
        ws = Path(tempfile.mkdtemp(prefix="ws_"))
        self.addCleanup(cleanup_dir, str(ws))
        with CredentialStore(real) as store:
            executor = SeriesExecutor(
                make_config=make_config,
                credential_store=store,
                template_name="series.toml",
            )
            # The template names no prompts, so the trial stops before any engine runs;
            # the config was made by then, and the store takes it back on the way out.
            with self.assertRaises(KeyError):
                executor.run_trial(task, ws, _scenario(), runner=None)
            self.assertEqual(sources, [store.seed_dir()])
            held = (Path(store.seed_dir()) / CREDENTIAL_FILE).read_text(encoding="utf-8")
        self.assertIn("refresh-engine", held)


class SmokeCarriesTheCredentialTests(unittest.TestCase):
    """`fathom smoke` runs its spawns in sequence; each must start from the newest
    credential, as a run's spawns do.

    The seat's access token has already expired, so the first spawn refreshes and the
    seat's own file is left holding a refresh token the server has spent. Before smoke
    carried a store, every spawn after the first started from that file and died on auth,
    and the gate reported a dead seat it had itself killed. The check outcomes do not
    matter here (the stub's canned stream satisfies only some of them); what the seat saw
    does.
    """

    def setUp(self) -> None:
        self.real = Path(tempfile.mkdtemp(prefix="fake_real_cfg_"))
        self.addCleanup(cleanup_dir, str(self.real))
        self.seat = RotatingOAuthSeat(start_s=1_000_000.0)
        self.seat_file = self.real / CREDENTIAL_FILE
        self.seat_file.write_text(json.dumps(self.seat.issue()), encoding="utf-8")
        # The access token issued above is already past its expiry when smoke starts.
        self.seat.now_s += 2 * ACCESS_LIFE_S
        self.seat_bytes = self.seat_file.read_bytes()
        self.refresh_seen: list[str] = []
        self.copies_during: list[int] = []

    def _spawn(self, argv, *, input, timeout, env, cwd):
        path = Path(env["CLAUDE_CONFIG_DIR"]) / CREDENTIAL_FILE
        self.copies_during.append(len(list(Path(tempfile.gettempdir()).glob("fathom_cred_*"))))
        self.refresh_seen.append(
            json.loads(path.read_text(encoding="utf-8"))["claudeAiOauth"]["refreshToken"]
        )
        return self.seat.spawn(argv, input=input, timeout=timeout, env=env, cwd=cwd)

    def _smoke(self) -> str:
        from fathom.smoke import RealProbes, run_smoke

        # A temporary directory of this test's own, so another process's fathom run
        # holding a copy at the same moment cannot be mistaken for one this smoke left.
        tmp = Path(tempfile.mkdtemp(prefix="smoke_tmp_"))
        self.addCleanup(cleanup_dir, str(tmp))
        probes = RealProbes(real_config_dir=str(self.real), spawn=self._spawn, scenarios_dir=None)
        out = io.StringIO()
        with mock.patch.dict(os.environ), mock.patch.object(tempfile, "tempdir", str(tmp)):
            os.environ.pop("FATHOM_STREAM_DIR", None)
            run_smoke(probes, include_engine=False, out=out, now_s=self.seat.now_s)
        self.cred_dirs_after = sorted(p.name for p in tmp.glob("fathom_cred_*"))
        return out.getvalue()

    def test_every_spawn_after_the_first_starts_from_the_refreshed_pair(self):
        out = self._smoke()
        self.assertEqual(self.seat.auth_failures, 0, out)
        # authed, deny, injection, memory, mount treatment, mount control.
        self.assertEqual(self.seat.spawns, 6, out)
        self.assertEqual(self.seat.refreshes, 6, out)
        # The seat file's pair is serial 1; each refresh issues the next serial, and the
        # next spawn is handed exactly that one.
        self.assertEqual(self.refresh_seen, [f"refresh-{n}" for n in range(1, 7)], out)
        self.assertNotIn("could not be refreshed", out)

    def test_the_seat_file_is_left_as_it_was(self):
        self._smoke()
        self.assertEqual(self.seat_file.read_bytes(), self.seat_bytes)

    def test_no_copy_of_the_credential_outlives_the_smoke(self):
        self._smoke()
        # One carried copy while the spawns ran (so the check below is not vacuous), and
        # none once the gate ended.
        self.assertEqual(set(self.copies_during), {1})
        self.assertEqual(self.cred_dirs_after, [])


if __name__ == "__main__":
    unittest.main()
