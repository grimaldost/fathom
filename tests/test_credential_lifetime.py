"""A matrix outlives the access token it started with (FATH-B55) — stdlib-runnable.

Run directly:  python tests/test_credential_lifetime.py
Run via pytest: uv run pytest tests/test_credential_lifetime.py

Each spawn runs under a throwaway ``CLAUDE_CONFIG_DIR`` holding a copy of the seat's
credential. When the access token has expired, the CLI inside the spawn redeems the
refresh token, which the server then rotates: the old refresh token is spent, and the new
pair is written into the spawn's directory. Before this fix that directory was deleted
with the new pair in it, so the next spawn started again from the seat's original file,
whose refresh token was already spent, and died on auth part-way through the matrix.

When the run or the smoke ends, the newer pair is written back to the seat's own file
(T53b), but only when it is newer by both expiry timestamps and the seat's file is
byte-identical to what was copied; and neither starts a spend while the seat's access token
has already expired.

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

from fathom import credentials
from fathom.adapters.base import ExitStatus
from fathom.adapters.claude_cli import ClaudeCliRunner, cleanup_dir
from fathom.credentials import CredentialStore, write_back_to_seat
from fathom.scenario import LimitsOverride, ResolvedScenario, ToolsConfig

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

    def test_the_seat_ends_with_the_live_pair(self):
        """The problem itself (T53): after a run that refreshed, the seat's own file held a
        spent refresh token and the owner's next ``claude`` asked for /login. Now the run
        writes the newer pair back, so a spawn straight from the seat's file authenticates."""
        code, out = self._run(repeats=3)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.seat.refreshes, 2, out)
        oauth = json.loads(self.real_credential.read_text(encoding="utf-8"))["claudeAiOauth"]
        self.assertIn(oauth["refreshToken"], self.seat.live_refresh, out)
        self.assertIn("written back", out)
        # The owner's next session, from the seat's own directory, after the access token
        # has expired once more.
        self.seat.now_s += 2 * ACCESS_LIFE_S
        failures = self.seat.auth_failures
        self.seat.spawn(
            ["claude"],
            input="",
            timeout=1,
            env={"CLAUDE_CONFIG_DIR": str(self.home / ".claude")},
            cwd=None,
        )
        self.assertEqual(self.seat.auth_failures, failures)

    def test_a_seat_changed_during_the_run_is_left_as_it_is_and_said_so(self):
        """Another session wrote the seat's file after the run last copied it: the run
        leaves that file alone and says so (option 2 of T53b, the fallback)."""
        changed = json.dumps({**json.loads(self.real_credential.read_text()), "touched": 1})
        spawn = self.seat.spawn

        def spawn_then_touch_the_seat(argv, *, input, timeout, env, cwd):
            result = spawn(argv, input=input, timeout=timeout, env=env, cwd=cwd)
            self.real_credential.write_text(changed, encoding="utf-8")
            return result

        self.seat.spawn = spawn_then_touch_the_seat
        code, out = self._run(repeats=3)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.real_credential.read_text(encoding="utf-8"), changed)
        self.assertIn("changed while the run went on", out)
        self.assertIn("left as it is", out)

    def test_an_expired_seat_access_token_refuses_the_run_with_the_cure(self):
        """Option 2 of T53b: the first spawn would redeem the seat's refresh token inside a
        copy, so the run does not start; running any claude command once lets the seat
        refresh its own file in place."""
        self.seat.now_s = time.time() - 2 * ACCESS_LIFE_S
        self.real_credential.write_text(json.dumps(self.seat.issue()), encoding="utf-8")
        before = self.real_credential.read_bytes()
        code, out = self._run(repeats=2)
        from fathom.cli import EXIT_CREDENTIAL

        self.assertEqual(code, EXIT_CREDENTIAL, out)
        self.assertEqual(self.seat.spawns, 0, out)
        self.assertIn("access token has expired", out)
        self.assertIn("refreshes its own credential in place", out)
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


def _seat_text(expires_at_s: float, refresh_expires_at_s: float, tag: str) -> str:
    """A seat file with keys besides the OAuth block, which a write-back must keep."""
    data = json.loads(_credential(expires_at_s, refresh_expires_at_s, tag))
    data["mcpOAuth"] = {"server": {"accessToken": f"mcp-{tag}"}}
    data["otherKey"] = tag
    return json.dumps(data, indent=2)


class SeatWriteBackTests(unittest.TestCase):
    """:func:`write_back_to_seat` on fake files under a temporary home (T53b)."""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="fake_home_"))
        self.addCleanup(cleanup_dir, str(self.home))
        self.seat = self.home / ".claude" / CREDENTIAL_FILE
        self.seat.parent.mkdir()
        self.seat.write_text(_seat_text(100, 1000, "seat"), encoding="utf-8")
        self.copy_dir = self.home / "copy"
        self.copy_dir.mkdir()
        self.copy = self.copy_dir / CREDENTIAL_FILE
        self.copied = credentials.copy_credential(self.seat, self.copy)

    def _copy_becomes(self, expires_at_s: float, refresh_expires_at_s: float, tag: str) -> None:
        self.copy.write_text(_seat_text(expires_at_s, refresh_expires_at_s, tag), encoding="utf-8")

    def _seat(self) -> dict:
        return json.loads(self.seat.read_text(encoding="utf-8"))

    def test_the_copy_records_the_digest_of_what_it_copied(self):
        self.assertEqual(self.copy.read_bytes(), self.seat.read_bytes())
        self.assertEqual(self.copied, credentials.file_digest(self.seat))

    def test_a_newer_copy_is_written_back_when_the_seat_is_unchanged(self):
        self._copy_becomes(200, 2000, "refreshed")
        result = write_back_to_seat(self.copy, self.seat, self.copied)
        self.assertTrue(result.written, result.detail)
        self.assertEqual(result.outcome, "written")
        seat = self._seat()
        self.assertEqual(seat["claudeAiOauth"]["refreshToken"], "refresh-refreshed")
        # The seat's other keys are the seat's, not the copy's.
        self.assertEqual(seat["mcpOAuth"], {"server": {"accessToken": "mcp-seat"}})
        self.assertEqual(seat["otherKey"], "seat")
        self.assertEqual(list(seat), ["claudeAiOauth", "mcpOAuth", "otherKey"])
        self.assertEqual(sorted(os.listdir(self.seat.parent)), [CREDENTIAL_FILE])

    def test_a_seat_changed_since_the_copy_is_left_untouched_and_reported(self):
        self._copy_becomes(200, 2000, "refreshed")
        changed = _seat_text(100, 1000, "seat").replace('"otherKey"', '"otherKey2"')
        self.seat.write_text(changed, encoding="utf-8")
        result = write_back_to_seat(self.copy, self.seat, self.copied)
        self.assertFalse(result.written)
        self.assertEqual(result.outcome, "seat-changed")
        self.assertTrue(result.notable)
        self.assertIn("left as it is", result.detail)
        self.assertEqual(self.seat.read_text(encoding="utf-8"), changed)

    def test_an_older_or_equal_copy_is_left_untouched(self):
        before = self.seat.read_bytes()
        cases = {
            "equal": (100, 1000),
            "older": (50, 500),
            "newer access only": (200, 1000),
            "newer refresh only": (100, 2000),
        }
        for label, (access, refresh) in cases.items():
            with self.subTest(label):
                self._copy_becomes(access, refresh, label)
                result = write_back_to_seat(self.copy, self.seat, self.copied)
                self.assertFalse(result.written)
                self.assertEqual(result.outcome, "not-newer")
                self.assertEqual(self.seat.read_bytes(), before)

    def test_nothing_copied_means_nothing_written(self):
        before = self.seat.read_bytes()
        self._copy_becomes(200, 2000, "refreshed")
        result = write_back_to_seat(self.copy, self.seat, None)
        self.assertEqual(result.outcome, "nothing-to-write")
        self.assertFalse(result.notable)
        self.assertEqual(self.seat.read_bytes(), before)

    def test_the_replace_is_atomic(self):
        """The new file is written in full beside the seat's file and moved over it in one
        rename; until that rename the seat's file is the old one, byte for byte."""
        self._copy_becomes(200, 2000, "refreshed")
        before = self.seat.read_bytes()
        calls: list[tuple[Path, Path]] = []
        real_replace = os.replace

        def recording_replace(src, dst):
            calls.append((Path(src), Path(dst)))
            self.assertEqual(self.seat.read_bytes(), before)
            self.assertEqual(Path(src).parent, self.seat.parent)
            self.assertIn("refresh-refreshed", Path(src).read_text(encoding="utf-8"))
            real_replace(src, dst)

        with mock.patch.object(credentials.os, "replace", recording_replace):
            result = write_back_to_seat(self.copy, self.seat, self.copied)
        self.assertTrue(result.written, result.detail)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], self.seat)

    def test_a_failed_replace_leaves_the_seat_and_no_temporary_file(self):
        self._copy_becomes(200, 2000, "refreshed")
        before = self.seat.read_bytes()

        def failing_replace(src, dst):
            raise PermissionError("locked")

        with mock.patch.object(credentials.os, "replace", failing_replace):
            result = write_back_to_seat(self.copy, self.seat, self.copied)
        self.assertEqual(result.outcome, "failed")
        self.assertTrue(result.notable)
        self.assertEqual(self.seat.read_bytes(), before)
        self.assertEqual(sorted(os.listdir(self.seat.parent)), [CREDENTIAL_FILE])

    def test_no_credential_value_reaches_the_report(self):
        self._copy_becomes(200, 2000, "refreshed")
        for result in (
            write_back_to_seat(self.copy, self.seat, "0" * 64),
            write_back_to_seat(self.copy, self.seat, self.copied),
        ):
            for value in ("access-", "refresh-", "mcp-"):
                self.assertNotIn(value, result.detail)


class CredentialStoreWriteBackTests(unittest.TestCase):
    """The run's carried copy hands its newest pair back to the seat (T53b)."""

    def setUp(self) -> None:
        self.real = Path(tempfile.mkdtemp(prefix="fake_real_cfg_"))
        self.addCleanup(cleanup_dir, str(self.real))
        self.spawn_dir = Path(tempfile.mkdtemp(prefix="fake_spawn_cfg_"))
        self.addCleanup(cleanup_dir, str(self.spawn_dir))
        self.seat_file = self.real / CREDENTIAL_FILE
        self.seat_file.write_text(_credential(100, 1000, "seat"), encoding="utf-8")

    def _spawn_leaves(self, text: str) -> None:
        (self.spawn_dir / CREDENTIAL_FILE).write_text(text, encoding="utf-8")

    def test_a_store_that_never_copied_writes_nothing(self):
        before = self.seat_file.read_bytes()
        with CredentialStore(self.real) as store:
            self.assertEqual(store.write_back().outcome, "nothing-to-write")
        self.assertEqual(self.seat_file.read_bytes(), before)

    def test_the_refreshed_copy_is_written_back(self):
        with CredentialStore(self.real) as store:
            store.seed_dir()
            self._spawn_leaves(_credential(200, 2000, "refreshed"))
            store.absorb(self.spawn_dir)
            self.assertTrue(store.write_back().written)
        self.assertIn("refresh-refreshed", self.seat_file.read_text(encoding="utf-8"))

    def test_a_seat_changed_after_the_last_copy_is_left_untouched(self):
        with CredentialStore(self.real) as store:
            store.seed_dir()
            self._spawn_leaves(_credential(200, 2000, "refreshed"))
            store.absorb(self.spawn_dir)
            # Not newer, so the store does not take it; but it is not what was copied.
            self.seat_file.write_text(_credential(100, 1000, "other"), encoding="utf-8")
            result = store.write_back()
        self.assertEqual(result.outcome, "seat-changed")
        self.assertIn("refresh-other", self.seat_file.read_text(encoding="utf-8"))

    def test_a_new_login_taken_mid_run_is_what_the_guard_compares_against(self):
        with CredentialStore(self.real) as store:
            store.seed_dir()
            self.seat_file.write_text(_credential(300, 3000, "relogin"), encoding="utf-8")
            store.seed_dir()  # the next spawn takes the newer seat file
            self._spawn_leaves(_credential(400, 4000, "refreshed"))
            store.absorb(self.spawn_dir)
            self.assertTrue(store.write_back().written)
        self.assertIn("refresh-refreshed", self.seat_file.read_text(encoding="utf-8"))


class SmokeCarriesTheCredentialTests(unittest.TestCase):
    """`fathom smoke` runs its spawns in sequence; each must start from the newest
    credential, as a run's spawns do.

    The seat's access token expires during the first spawn, so the second spawn refreshes
    and the seat's own file is left holding a refresh token the server has spent. Before
    smoke carried a store, every spawn after that started from that file and died on auth,
    and the gate reported a dead seat it had itself killed. When the gate ends, the newer
    pair is written back to the seat (T53b). The check outcomes do not
    matter here (the stub's canned stream satisfies only some of them); what the seat saw
    does.
    """

    def setUp(self) -> None:
        self.real = Path(tempfile.mkdtemp(prefix="fake_real_cfg_"))
        self.addCleanup(cleanup_dir, str(self.real))
        self.seat = RotatingOAuthSeat(start_s=1_000_000.0)
        self.seat_file = self.real / CREDENTIAL_FILE
        self.seat_file.write_text(json.dumps(self.seat.issue()), encoding="utf-8")
        # The access token issued above is live when smoke starts and expires during the
        # first spawn, so every spawn after the first has to refresh.
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
        probes = RealProbes(real_config_dir=str(self.real), spawn=self._spawn)
        out = io.StringIO()
        with mock.patch.dict(os.environ), mock.patch.object(tempfile, "tempdir", str(tmp)):
            os.environ.pop("FATHOM_STREAM_DIR", None)
            run_smoke(probes, out=out, now_s=self.seat.now_s)
        self.cred_dirs_after = sorted(p.name for p in tmp.glob("fathom_cred_*"))
        return out.getvalue()

    def test_every_spawn_after_the_first_starts_from_the_refreshed_pair(self):
        out = self._smoke()
        self.assertEqual(self.seat.auth_failures, 0, out)
        # authed, deny, injection, memory, mount treatment, mount control.
        self.assertEqual(self.seat.spawns, 6, out)
        self.assertEqual(self.seat.refreshes, 5, out)
        # The seat file's pair is serial 1 and the first spawn uses it unrefreshed; each
        # refresh issues the next serial, and the next spawn is handed exactly that one.
        self.assertEqual(
            self.refresh_seen, ["refresh-1", *(f"refresh-{n}" for n in range(1, 6))], out
        )
        self.assertNotIn("could not be refreshed", out)

    def test_the_seat_ends_with_the_live_pair(self):
        out = self._smoke()
        oauth = json.loads(self.seat_file.read_text(encoding="utf-8"))["claudeAiOauth"]
        self.assertIn(oauth["refreshToken"], self.seat.live_refresh, out)
        self.assertIn("written back", out)

    def test_an_expired_seat_access_token_refuses_the_smoke_before_any_spawn(self):
        self.seat.now_s += 2 * ACCESS_LIFE_S
        out = self._smoke()
        self.assertEqual(self.seat.spawns, 0, out)
        self.assertIn("access token has expired", out)
        self.assertIn("refreshes its own credential in place", out)
        self.assertEqual(self.seat_file.read_bytes(), self.seat_bytes)

    def test_no_copy_of_the_credential_outlives_the_smoke(self):
        self._smoke()
        # One carried copy while the spawns ran (so the check below is not vacuous), and
        # none once the gate ended.
        self.assertEqual(set(self.copies_during), {1})
        self.assertEqual(self.cred_dirs_after, [])


if __name__ == "__main__":
    unittest.main()
