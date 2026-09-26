"""Tests for src/fathom/runlock.py — the native run lock (FATH-B53 / T24).

Stdlib-runnable:
    python tests/test_runlock.py
Via pytest:
    uv run pytest tests/test_runlock.py

FATH-B53 was deferred partly because "its failure mode is multi-process on one
authenticated seat, which this repo's gate cannot exercise at all".  That is true of
the seat and false of the lock: nothing here needs a credential, a spawn or a dollar.

Three layers, cheapest first:
  1. the pure decision (who holds, who is stale) against handwritten tickets;
  2. the ticket directory, driven in-process;
  3. real contention — several OS processes racing for the same lock directory,
     each recording when it entered and left, asserted for non-overlap.
"""

from __future__ import annotations

import errno
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import itertools

from fathom.runlock import (
    HEARTBEAT_INTERVAL_S,
    STALE_AFTER_S,
    LockTimeout,
    RunLock,
    Ticket,
    ancestors_of,
    choosing_now,
    clear_stop_request,
    decide,
    descendants_of,
    holders,
    is_stale,
    next_ticket_number,
    parse_ps_output,
    read_stop_request,
    read_tickets,
    request_stop,
    terminate_process_tree,
    ticket_number,
)

_NOW = 1_700_000_000.0
# Every handwritten ticket shares one clock reading unless a test says otherwise, so each
# ordering assertion below also shows that the clock is not what orders the queue.
_ONE_TICK_NS = 1_700_000_000_000_000_000


def _ticket(
    number: int,
    *,
    pid: int = 100,
    created_ns: int = _ONE_TICK_NS,
    beat: float = _NOW,
    name: str | None = None,
):
    return Ticket(
        name=name or f"{number:020d}-{pid:07d}-abcdef01.ticket.json",
        number=number,
        pid=pid,
        created_ns=created_ns,
        heartbeat_s=beat,
        host="h",
        label="fathom run",
    )


# ---------------------------------------------------------------------------
# 1. The pure decision
# ---------------------------------------------------------------------------


class TestStaleness(unittest.TestCase):
    def test_fresh_beat_is_live(self):
        self.assertFalse(is_stale(_ticket(1, beat=_NOW - 5), now_s=_NOW))

    def test_beat_older_than_the_horizon_is_stale(self):
        self.assertTrue(is_stale(_ticket(1, beat=_NOW - STALE_AFTER_S - 1), now_s=_NOW))

    def test_exactly_at_the_horizon_is_still_live(self):
        self.assertFalse(is_stale(_ticket(1, beat=_NOW - STALE_AFTER_S), now_s=_NOW))

    def test_a_future_beat_is_not_stale(self):
        """Clock skew must never let a second run start beside a live one."""
        self.assertFalse(is_stale(_ticket(1, beat=_NOW + 3600), now_s=_NOW))

    def test_the_horizon_is_several_missed_beats(self):
        """A stalled writer must not be mistaken for a dead one."""
        self.assertGreaterEqual(STALE_AFTER_S / HEARTBEAT_INTERVAL_S, 4)


class TestDecide(unittest.TestCase):
    def test_empty_directory_has_no_holder(self):
        d = decide([], "mine", now_s=_NOW)
        self.assertIsNone(d.holder)
        self.assertFalse(d.holds)

    def test_earliest_ticket_holds(self):
        first, second = _ticket(10), _ticket(20)
        self.assertEqual(decide([second, first], None, now_s=_NOW).holder, first)

    def test_a_later_arrival_does_not_hold(self):
        first, second = _ticket(10), _ticket(20)
        self.assertFalse(decide([first, second], second.name, now_s=_NOW).holds)

    def test_fifo_means_the_queue_order_is_arrival_order(self):
        tickets = [_ticket(n) for n in (30, 10, 20)]
        d = decide(tickets, None, now_s=_NOW)
        self.assertEqual(d.holder.number, 10)

    def test_the_number_decides_not_the_clock_or_the_pid(self):
        """T24d across processes: a lower number holds even when its clock reading is
        later and its pid is higher, which is what an ordering by created_ns got wrong."""
        earlier = _ticket(1, pid=900, created_ns=_ONE_TICK_NS + 5)
        later = _ticket(2, pid=100, created_ns=_ONE_TICK_NS)
        self.assertEqual(decide([later, earlier], None, now_s=_NOW).holder, earlier)
        self.assertFalse(decide([earlier, later], later.name, now_s=_NOW).holds)

    def test_a_dead_holder_is_stale_and_the_next_in_line_holds(self):
        """The three observed deadlocks, in one assertion: a holder that finished
        spending or died without releasing must expire from its own timestamps."""
        dead = _ticket(10, pid=1, beat=_NOW - STALE_AFTER_S - 1)
        waiting = _ticket(20, pid=2)
        d = decide([dead, waiting], waiting.name, now_s=_NOW)
        self.assertEqual(d.stale, (dead,))
        self.assertEqual(d.holder, waiting)
        self.assertTrue(d.holds)

    def test_every_ticket_stale_means_no_holder(self):
        old = [_ticket(n, beat=_NOW - STALE_AFTER_S - 1) for n in (10, 20)]
        d = decide(old, None, now_s=_NOW)
        self.assertIsNone(d.holder)
        self.assertEqual(len(d.stale), 2)

    def test_order_is_total_when_two_tickets_share_a_number(self):
        """Two acquirers choosing at once draw the same number; everyone breaks the tie
        the same way."""
        a = _ticket(10, pid=1)
        b = _ticket(10, pid=2)
        self.assertEqual(decide([b, a], None, now_s=_NOW).holder, a)
        self.assertEqual(decide([a, b], None, now_s=_NOW).holder, a)


# ---------------------------------------------------------------------------
# 2. The ticket directory
# ---------------------------------------------------------------------------


class TestTicketDirectory(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="fathom-lock-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _lock(self, **kw):
        return RunLock("b", lock_root=self.root, label="test", **kw)

    def test_acquire_writes_one_ticket_and_release_removes_it(self):
        lock = self._lock()
        lock.acquire()
        try:
            tickets = read_tickets(lock.dir)
            self.assertEqual(len(tickets), 1)
            self.assertEqual(tickets[0].name, lock.ticket_name)
        finally:
            lock.release()
        self.assertEqual(read_tickets(lock.dir), [])

    def test_the_lock_never_lands_under_ledger(self):
        """FATH-B53's stated trigger: `ledger/` is tracked, so a lock there gets committed."""
        from fathom.runlock import LOCK_ROOT

        self.assertNotIn("ledger", LOCK_ROOT.parts)

    def test_held_releases_on_an_exception(self):
        lock = self._lock()
        with self.assertRaises(ValueError), lock.held():
            raise ValueError("boom")
        self.assertEqual(read_tickets(lock.dir), [])

    def test_a_second_acquirer_waits_and_then_holds(self):
        first = self._lock()
        first.acquire()
        second = self._lock()
        with self.assertRaises(LockTimeout):
            second.acquire(timeout_s=0.3, poll_s=0.05)
        # A refused waiter drops its own ticket, so it cannot block the next in line.
        self.assertEqual([t.name for t in read_tickets(first.dir)], [first.ticket_name])
        first.release()
        second.acquire(timeout_s=2.0, poll_s=0.05)
        self.addCleanup(second.release)
        self.assertEqual([t.name for t in read_tickets(second.dir)], [second.ticket_name])

    def test_a_stale_ticket_is_pruned_rather_than_honoured(self):
        lock = self._lock()
        lock.dir.mkdir(parents=True, exist_ok=True)
        dead = lock.dir / "00000000000000000001-0000001-deadbeef.ticket.json"
        dead.write_text(
            json.dumps(
                {
                    "pid": 1,
                    "created_ns": 1,
                    "heartbeat_s": time.time() - STALE_AFTER_S - 10,
                    "host": "h",
                    "label": "a run that died holding the claim",
                }
            ),
            encoding="utf-8",
        )
        lock.acquire(timeout_s=5.0, poll_s=0.05)
        self.addCleanup(lock.release)
        self.assertFalse(dead.exists(), "a dead holder's claim must be released, not waited on")

    def test_an_acquirer_still_choosing_blocks_a_decision(self):
        """The window a four-process race actually found: a number picked, no ticket yet.

        A waiter that reads the directory inside it sees no earlier ticket and starts
        beside the run that was already choosing. The marker closes the window.
        """
        lock = self._lock()
        lock.dir.mkdir(parents=True, exist_ok=True)
        marker = lock.dir / "0000001-cafebabe.choosing"
        marker.touch()
        with self.assertRaises(LockTimeout):
            lock.acquire(timeout_s=0.3, poll_s=0.02)
        self.assertEqual(choosing_now(lock.dir), [marker.name])

    def test_an_abandoned_choosing_marker_does_not_deadlock(self):
        """A process that died between picking and publishing must not block forever."""
        import os

        from fathom.runlock import CHOOSING_STALE_AFTER_S

        lock = self._lock()
        lock.dir.mkdir(parents=True, exist_ok=True)
        marker = lock.dir / "0000001-abandoned.choosing"
        marker.touch()
        old = time.time() - CHOOSING_STALE_AFTER_S - 10
        os.utime(marker, (old, old))
        lock.acquire(timeout_s=5.0, poll_s=0.02)
        self.addCleanup(lock.release)
        self.assertFalse(marker.exists())

    def test_a_malformed_ticket_is_not_evidence_of_a_holder(self):
        lock = self._lock()
        lock.dir.mkdir(parents=True, exist_ok=True)
        (lock.dir / "00000000000000000001-0000001-garbage.ticket.json").write_text(
            "{half written", encoding="utf-8"
        )
        lock.acquire(timeout_s=5.0, poll_s=0.05)
        self.addCleanup(lock.release)
        self.assertTrue(lock.ticket_name)

    def test_heartbeat_moves_the_ticket_forward(self):
        lock = self._lock(heartbeat_interval_s=0.05)
        lock.acquire()
        self.addCleanup(lock.release)
        before = read_tickets(lock.dir)[0].heartbeat_s
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            if read_tickets(lock.dir)[0].heartbeat_s > before:
                return
            time.sleep(0.05)
        self.fail("the heartbeat never advanced — staleness would not be decidable")

    def test_holders_reports_who_has_it(self):
        lock = self._lock()
        lock.acquire()
        self.addCleanup(lock.release)
        decision = holders("b", lock_root=self.root)
        self.assertIsNotNone(decision.holder)
        self.assertIn("pid", decision.holder.describe(time.time()))


# Windows under Python 3.12 reads `time.time_ns()` from GetSystemTimeAsFileTime, which
# advances in 15.625 ms steps (`time.get_clock_info("time").resolution`), and CI pins 3.12.
_COARSE_TICK_NS = 15_625_000


class TestTicketOrderIsNotAClockReading(unittest.TestCase):
    """T24d. Two acquirers inside one clock tick still queue in arrival order.

    The CI failure this pins (windows-latest, CPython 3.12): `a second acquirer waits
    and then holds` raised `LockTimeout not raised`, because the second acquirer held
    while the first still did. Ordered by `(created_ns, pid, name)`, two tickets taken
    inside one 15.625 ms tick tie on the clock. In one process the pid ties too, and the
    order falls to the random uid in the name, so a later arrival can sort ahead of a
    holder that has already decided it holds.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="fathom-lock-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_a_later_arrival_in_the_same_tick_waits(self):
        """Deterministic: the clock is read inside one tick, and the uids are chosen so
        the later arrival's name sorts first (the losing half of the coin flip)."""
        tick = time.time_ns() // _COARSE_TICK_NS * _COARSE_TICK_NS
        uids = iter([uuid.UUID(int=(1 << 128) - 1), uuid.UUID(int=0)])
        with (
            mock.patch("fathom.runlock.time.time_ns", return_value=tick),
            mock.patch("fathom.runlock.uuid.uuid4", side_effect=lambda: next(uids)),
        ):
            first = RunLock("b", lock_root=self.root, label="first")
            first.acquire(timeout_s=2.0, poll_s=0.02)
            self.addCleanup(first.release)
            second = RunLock("b", lock_root=self.root, label="second")
            with self.assertRaises(LockTimeout):
                second.acquire(timeout_s=0.3, poll_s=0.02)

    def test_a_quantised_clock_never_admits_two_holders(self):
        """The triage's scratch repro, kept: with the clock quantised to 15.625 ms and
        real random uids, the second acquirer held beside the first in 53 of 200.

        Against the clock-ordered code this fails in most runs but not every run, since
        the uids are random. The test above is the deterministic regression pin. Against
        the bakery number this passes every run, because no round depends on the clock."""
        real_time_ns = time.time_ns

        def coarse() -> int:
            return real_time_ns() // _COARSE_TICK_NS * _COARSE_TICK_NS

        admitted = 0
        with mock.patch("fathom.runlock.time.time_ns", side_effect=coarse):
            for _ in range(50):
                with tempfile.TemporaryDirectory(prefix="fathom-lock-") as tmp:
                    first = RunLock("b", lock_root=Path(tmp))
                    first.acquire(timeout_s=2.0, poll_s=0.005)
                    second = RunLock("b", lock_root=Path(tmp))
                    try:
                        second.acquire(timeout_s=0.02, poll_s=0.005)
                    except LockTimeout:
                        pass
                    else:
                        admitted += 1
                        second.release()
                    first.release()
        self.assertEqual(admitted, 0, "a second acquirer held while the first still did")

    def test_the_next_number_is_one_more_than_the_highest_visible(self):
        d = self.root / "b"
        d.mkdir()
        self.assertEqual(next_ticket_number(d), 1)
        for name in (
            "00000000000000000003-0000001-aaaaaaaa.ticket.json",
            "00000000000000000007-0000002-bbbbbbbb.ticket.json",
            "00000000000000000009-0000003-cccccccc.choosing",  # a marker is not a ticket
            ".tmp-99999999999999999999.json",
            "stop.json",
        ):
            (d / name).write_text("{}", encoding="utf-8")
        self.assertEqual(next_ticket_number(d), 8)

    def test_acquirers_take_consecutive_numbers(self):
        first = RunLock("b", lock_root=self.root)
        first.acquire(timeout_s=2.0, poll_s=0.02)
        self.addCleanup(first.release)
        self.assertEqual(ticket_number(first.ticket_name), 1)
        self.assertEqual(next_ticket_number(first.dir), 2)

    def test_a_ticket_written_by_0_6_2_keeps_its_place(self):
        """A 0.6.2 ticket has no number of its own; its name leads with its created_ns,
        which is read as its number. A 0.7.0 acquirer behind it takes a larger one and
        waits, rather than sorting ahead of a holder that is still beating."""
        d = self.root / "b"
        d.mkdir()
        legacy_ns = time.time_ns()
        legacy = d / f"{legacy_ns:020d}-{4242:07d}-0a0b0c0d.ticket.json"
        legacy.write_text(
            json.dumps(
                {
                    "pid": 4242,
                    "created_ns": legacy_ns,
                    "heartbeat_s": time.time(),
                    "host": "h",
                    "label": "a 0.6.2 run",
                }
            ),
            encoding="utf-8",
        )
        (parsed,) = read_tickets(d)
        self.assertEqual(parsed.number, legacy_ns)
        self.assertEqual(next_ticket_number(d), legacy_ns + 1)
        waiter = RunLock("b", lock_root=self.root)
        with self.assertRaises(LockTimeout):
            waiter.acquire(timeout_s=0.3, poll_s=0.02)
        self.assertTrue(legacy.exists())


def _unreadable(target_matches):
    """A `Path.read_text` that fails the way Windows does while the file is being
    replaced (a heartbeat's `os.replace`), for every path *target_matches* accepts."""
    real_read_text = Path.read_text

    def read_text(self, *args, **kwargs):
        if target_matches(self):
            raise PermissionError(errno.EACCES, "Permission denied", str(self))
        return real_read_text(self, *args, **kwargs)

    return mock.patch.object(Path, "read_text", read_text)


class TestATicketThatCannotBeReadIsStillThere(unittest.TestCase):
    """A ticket file that exists but cannot be read right now still holds its place.

    On Windows, a read that lands while the owner's heartbeat replaces the ticket
    fails with PermissionError (measured: 663 of 7353 reads failed under a writer
    replacing the file in a loop). `_parse_ticket` returned None for it, so the
    holder's ticket was treated as absent, and a waiter that read the directory at
    that moment found no one ahead of it and held.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="fathom-lock-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_a_holder_whose_ticket_cannot_be_read_still_holds(self):
        holder = RunLock("b", lock_root=self.root, label="holder")
        holder.acquire(timeout_s=2.0, poll_s=0.02)
        self.addCleanup(holder.release)
        held = holder.dir / holder.ticket_name
        waiter = RunLock("b", lock_root=self.root, label="waiter")
        with _unreadable(lambda p: p == held), self.assertRaises(LockTimeout):
            waiter.acquire(timeout_s=0.3, poll_s=0.02)

    def test_an_unreadable_ticket_untouched_past_the_horizon_is_pruned(self):
        """Counting an unreadable ticket as present must not become a new way to wait
        forever: its file's modification time stands in for the heartbeat it hides."""
        d = self.root / "b"
        d.mkdir()
        dead = d / "00000000000000000001-0000001-deadbeef.ticket.json"
        dead.write_text("{}", encoding="utf-8")
        old = time.time() - STALE_AFTER_S - 10
        os.utime(dead, (old, old))
        waiter = RunLock("b", lock_root=self.root, label="waiter")
        with _unreadable(lambda p: p == dead):
            waiter.acquire(timeout_s=2.0, poll_s=0.02)
        self.addCleanup(waiter.release)
        self.assertFalse(dead.exists(), "a dead, unreadable ticket must be released")


def _refusing_unlink(target_matches, refusals: int | None):
    """An `os.unlink` that fails the way Windows does while another process has the
    file open (a sharing violation surfaces as PermissionError), *refusals* times for
    the matching path — or every time when *refusals* is None."""
    real_unlink = os.unlink
    refused: list[str] = []

    def unlink(target, *args, **kwargs):
        if target_matches(Path(target)) and (refusals is None or len(refused) < refusals):
            refused.append(str(target))
            raise PermissionError(
                errno.EACCES, "the file is being used by another process", str(target)
            )
        return real_unlink(target, *args, **kwargs)

    return unlink, refused


class TestReleaseRemovesItsTicket(unittest.TestCase):
    """T24e. A released ticket does not outlive its release.

    The CI failure this pins (windows-latest): `no two holders overlap` raised
    `LockTimeout: waited 60s … last heartbeat 60s ago`, because a contender that held
    for 0.15 s left a ticket nobody was beating. On Windows an unlink fails with a
    sharing violation while another process has the file open, and a waiter inside
    `_parse_ticket` has it open for one read. `release()` swallowed that failure, so
    the ticket read as a live holder until the 120 s staleness horizon.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="fathom-lock-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _held(self) -> tuple[RunLock, Path]:
        lock = RunLock("b", lock_root=self.root, label="test")
        lock.acquire(timeout_s=2.0, poll_s=0.02)
        self.addCleanup(lock.release)
        return lock, lock.dir / lock.ticket_name

    def test_a_reader_holding_the_ticket_open_does_not_keep_it(self):
        """Real handles. On Windows the first unlink fails while the reader is open; on
        POSIX it succeeds and this passes trivially. The reader closes inside release()'s
        first backoff step, so the retry itself drives the close and no timing is involved."""
        lock, path = self._held()
        reader = open(path, encoding="utf-8")  # noqa: SIM115 - held open across release()
        self.addCleanup(reader.close)
        with mock.patch("fathom.runlock.time.sleep", side_effect=lambda _s: reader.close()):
            lock.release()
        self.assertFalse(path.exists(), "the released ticket survived its release")
        self.assertEqual(read_tickets(lock.dir), [])

    def test_a_refused_unlink_is_retried(self):
        """The same sharing violation, simulated, so the Linux leg holds the retry too."""
        lock, path = self._held()
        unlink, refused = _refusing_unlink(lambda p: p == path, refusals=2)
        with (
            mock.patch("os.unlink", side_effect=unlink),
            mock.patch("fathom.runlock.time.sleep"),
        ):
            lock.release()
        self.assertEqual(len(refused), 2)
        self.assertFalse(path.exists(), "the released ticket survived its release")

    def test_an_unlink_that_never_succeeds_is_reported_not_swallowed(self):
        lock, path = self._held()
        unlink, refused = _refusing_unlink(lambda p: p == path, refusals=None)
        with (
            mock.patch("os.unlink", side_effect=unlink),
            mock.patch("fathom.runlock.time.sleep"),
            self.assertWarns(UserWarning) as caught,
        ):
            lock.release()
        self.assertGreater(
            len(refused), 1, "a refused unlink must be retried before it is reported"
        )
        self.assertIn(path.name, str(caught.warning))
        self.assertIsNone(
            lock.ticket_name, "release() still completes; it reports, it does not raise"
        )

    def test_the_choosing_marker_is_retried_too(self):
        """A marker left behind blocks every acquirer, this one included, for
        CHOOSING_STALE_AFTER_S — the same stall one step earlier."""
        lock = RunLock("b", lock_root=self.root, label="test")
        unlink, refused = _refusing_unlink(lambda p: p.name.endswith(".choosing"), refusals=1)
        with mock.patch("os.unlink", side_effect=unlink):
            lock.acquire(timeout_s=2.0, poll_s=0.02)
        self.addCleanup(lock.release)
        self.assertEqual(len(refused), 1)
        self.assertEqual(choosing_now(lock.dir), [])


class _Interrupted(Exception):
    """Stands in for a Ctrl-C arriving while an acquirer waits."""


class TestAWaiterStaysInTheQueue(unittest.TestCase):
    """A waiter keeps its ticket alive, and its wait loop pauses on every pass.

    Only the holder used to beat, so a waiter's ticket kept the heartbeat it was
    written with. Once the wait outlasted STALE_AFTER_S (120 s), the waiter judged its
    own ticket stale: it could never hold, and the `continue` after pruning (which
    skips the waiter's own ticket) re-read the directory without sleeping. A second
    `fathom run` that waited more than two minutes therefore never started, and it
    spun a CPU core while it waited.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="fathom-lock-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _counting(self):
        """Wrap `read_tickets` and `time.sleep` to count calls made on this thread.

        Every pass of the wait loop either decides or pauses, so a loop that does not
        spin reads the directory at most once more than it sleeps. That ratio does not
        depend on how fast the machine is.
        """
        me = threading.get_ident()
        counts = {"reads": 0, "sleeps": 0}
        real_read, real_sleep = read_tickets, time.sleep

        def read(lock_dir):
            if threading.get_ident() == me:
                counts["reads"] += 1
            return real_read(lock_dir)

        def sleep(seconds):
            if threading.get_ident() == me:
                counts["sleeps"] += 1
            real_sleep(seconds)

        patches = (
            mock.patch("fathom.runlock.read_tickets", side_effect=read),
            mock.patch("fathom.runlock.time.sleep", side_effect=sleep),
        )
        return counts, patches

    def test_a_wait_longer_than_the_horizon_still_acquires(self):
        """Horizon 0.5 s, holder releases at 1.0 s: the waiter must then hold."""
        kw = {"lock_root": self.root, "stale_after_s": 0.5, "heartbeat_interval_s": 0.1}
        first = RunLock("b", label="holder", **kw)
        first.acquire(timeout_s=2.0, poll_s=0.02)
        self.addCleanup(first.release)
        release_at = threading.Timer(1.0, first.release)
        self.addCleanup(release_at.cancel)
        release_at.start()
        second = RunLock("b", label="waiter", **kw)
        counts, (patch_read, patch_sleep) = self._counting()
        with patch_read, patch_sleep:
            second.acquire(timeout_s=5.0, poll_s=0.02)
        self.addCleanup(second.release)
        release_at.join(timeout=5.0)
        self.assertLessEqual(
            counts["reads"], counts["sleeps"] + 1, "the wait loop re-read without pausing"
        )

    def test_a_stale_ticket_that_cannot_be_pruned_does_not_make_the_loop_spin(self):
        """Deterministic spin check: a dead ticket whose unlink is refused stays stale on
        every pass. Before the fix each pass pruned it, failed, and went round again
        without sleeping."""
        holder = RunLock("b", lock_root=self.root, label="holder")
        holder.acquire(timeout_s=2.0, poll_s=0.02)
        self.addCleanup(holder.release)
        dead = holder.dir / "00000000000000000000-0000001-deadbeef.ticket.json"
        dead.write_text(
            json.dumps(
                {
                    "pid": 1,
                    "created_ns": 1,
                    "heartbeat_s": time.time() - STALE_AFTER_S - 10,
                    "host": "h",
                    "label": "a dead holder whose ticket cannot be removed",
                }
            ),
            encoding="utf-8",
        )
        self.addCleanup(dead.unlink, missing_ok=True)
        unlink, refused = _refusing_unlink(lambda p: p == dead, refusals=None)
        waiter = RunLock("b", lock_root=self.root, label="waiter")
        counts, (patch_read, patch_sleep) = self._counting()
        with (
            patch_read,
            patch_sleep,
            mock.patch("os.unlink", side_effect=unlink),
            self.assertRaises(LockTimeout),
        ):
            waiter.acquire(timeout_s=0.3, poll_s=0.05)
        self.assertTrue(refused, "the dead ticket was never offered for pruning")
        self.assertLessEqual(
            counts["reads"], counts["sleeps"] + 1, "the wait loop re-read without pausing"
        )

    def test_an_interrupted_wait_drops_its_ticket_and_stops_beating(self):
        """A waiter now beats from the moment it queues, so an exception mid-wait must
        release, or the ticket would be kept alive for as long as the process lives."""
        holder = RunLock("b", lock_root=self.root, label="holder")
        holder.acquire(timeout_s=2.0, poll_s=0.02)
        self.addCleanup(holder.release)
        waiter = RunLock("b", lock_root=self.root, label="waiter")

        def interrupt(_seconds):
            raise _Interrupted

        with (
            mock.patch("fathom.runlock.time.sleep", side_effect=interrupt),
            self.assertRaises(_Interrupted),
        ):
            waiter.acquire(poll_s=0.05)
        self.assertEqual([t.name for t in read_tickets(holder.dir)], [holder.ticket_name])
        self.assertIsNone(waiter._beat_thread)


# ---------------------------------------------------------------------------
# Stop requests (T24b)
# ---------------------------------------------------------------------------


class TestStopRequests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="fathom-stop-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_no_request_by_default(self):
        self.assertIsNone(read_stop_request("b", lock_root=self.root))

    def test_a_request_reaches_the_holder(self):
        lock = RunLock("b", lock_root=self.root)
        lock.acquire()
        self.addCleanup(lock.release)
        self.assertIsNone(lock.stop_requested())
        request_stop("b", lock_root=self.root, reason="cap reached")
        req = lock.stop_requested()
        self.assertIsNotNone(req)
        self.assertTrue(req.at_boundary)
        self.assertEqual(req.reason, "cap reached")

    def test_a_request_older_than_this_holder_does_not_halt_it(self):
        """A stop left behind by yesterday's run must not kill today's before it buys."""
        request_stop("b", lock_root=self.root, reason="yesterday")
        time.sleep(0.01)
        lock = RunLock("b", lock_root=self.root)
        lock.acquire()
        self.addCleanup(lock.release)
        self.assertIsNone(lock.stop_requested())

    def test_clearing_removes_it(self):
        request_stop("b", lock_root=self.root)
        clear_stop_request("b", lock_root=self.root)
        self.assertIsNone(read_stop_request("b", lock_root=self.root))


# ---------------------------------------------------------------------------
# 3. Real contention — several OS processes, one lock directory, $0
# ---------------------------------------------------------------------------


_CONTENDER = textwrap.dedent(
    """
    import json, os, sys, time
    sys.path.insert(0, sys.argv[1])
    from fathom.runlock import RunLock

    root, log, label = sys.argv[2], sys.argv[3], sys.argv[4]
    lock = RunLock("b", lock_root=root, label=label, heartbeat_interval_s=0.2)
    with lock.held(timeout_s=60.0, poll_s=0.02):
        enter = time.time()
        time.sleep(0.15)          # a "trial"
        leave = time.time()
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"pid": os.getpid(), "enter": enter, "leave": leave}) + "\\n")
    """
)


class TestRealContention(unittest.TestCase):
    """Six OS processes race for one lock; no two may be inside it at once.

    Non-vacuity was checked by hand: replacing RunLock with a no-op in the contender
    makes 3 of 3 adjacent pairs overlap, so this assertion fails for the right reason
    rather than because the processes happened not to collide.
    """

    def test_no_two_holders_overlap(self):
        src = str(Path(__file__).parent.parent / "src")
        with tempfile.TemporaryDirectory(prefix="fathom-race-") as tmp:
            tmp_p = Path(tmp)
            script = tmp_p / "contender.py"
            script.write_text(_CONTENDER, encoding="utf-8")
            log = tmp_p / "log.jsonl"
            root = str(tmp_p / "locks")
            procs = [
                subprocess.Popen(
                    [sys.executable, str(script), src, root, str(log), f"run-{i}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                for i in range(6)
            ]
            for p in procs:
                _out, err = p.communicate(timeout=120)
                self.assertEqual(p.returncode, 0, err.decode("utf-8", "replace"))

            spans = [
                json.loads(line)
                for line in log.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(len(spans), 6, "every contender must eventually get the lock")
        spans.sort(key=lambda s: s["enter"])
        for earlier, later in itertools.pairwise(spans):
            self.assertLessEqual(
                earlier["leave"],
                later["enter"],
                "two processes were inside the lock at the same time",
            )


# A two-level tree for the `--now` escalation: this script starts a grandchild that
# touches a beat file every 50ms and then sleeps. Killing only the parent leaves the
# grandchild beating, which is exactly the `uv -> fathom -> claude` survival that cost
# ~$2 and ~15 minutes to clear by hand.
_TREE_GRANDCHILD = textwrap.dedent(
    """
    import sys, time
    while True:
        with open(sys.argv[1], "w", encoding="utf-8") as fh:
            fh.write(str(time.time()))
        time.sleep(0.05)
    """
)

_TREE_PARENT = textwrap.dedent(
    """
    import subprocess, sys, tempfile, time, pathlib
    src = pathlib.Path(tempfile.mkdtemp()) / "grandchild.py"
    src.write_text(sys.argv[2], encoding="utf-8")
    subprocess.Popen([sys.executable, str(src), sys.argv[1]])
    time.sleep(60)
    """
)


class TestDescendantWalk(unittest.TestCase):
    """Pure over a {pid: ppid} map — the walk that replaced killing a process group."""

    def test_children_and_grandchildren_deepest_first(self):
        parents = {1: 0, 10: 1, 11: 10, 12: 11, 20: 1}
        self.assertEqual(descendants_of(10, parents), [12, 11])

    def test_a_leaf_has_no_descendants(self):
        self.assertEqual(descendants_of(12, {10: 1, 11: 10, 12: 11}), [])

    def test_the_target_is_never_its_own_descendant(self):
        self.assertNotIn(10, descendants_of(10, {10: 1, 11: 10}))

    def test_a_cycle_terminates(self):
        """A malformed map must not hang the stop verb."""
        self.assertEqual(descendants_of(10, {10: 11, 11: 10}), [11])

    def test_siblings_are_not_swept_in(self):
        parents = {10: 1, 11: 10, 20: 1, 21: 20}
        self.assertEqual(descendants_of(10, parents), [11])

    def test_ancestors_are_listed_nearest_first(self):
        self.assertEqual(ancestors_of(12, {10: 1, 11: 10, 12: 11, 1: 0}), [11, 10, 1])

    def test_ancestors_of_a_root_is_empty(self):
        self.assertEqual(ancestors_of(1, {1: 0}), [])

    def test_ancestor_cycle_terminates(self):
        self.assertEqual(ancestors_of(10, {10: 11, 11: 10}), [11])

    def test_ps_output_parses_padded_columns(self):
        text = "    1     0\n  842     1\n  900   842\n"
        self.assertEqual(parse_ps_output(text), {1: 0, 842: 1, 900: 842})

    def test_ps_header_and_junk_lines_are_dropped_not_guessed(self):
        text = "  PID  PPID\n  842     1\n\ngarbage\n  900   842  extra\n"
        self.assertEqual(parse_ps_output(text), {842: 1, 900: 842})

    def test_empty_ps_output_is_an_empty_tree(self):
        self.assertEqual(parse_ps_output(""), {})


class TestTerminateProcessTree(unittest.TestCase):
    """`fathom stop --now` must take the tree, not just the process it names.

    And it must take NOTHING above it. The first implementation signalled
    `os.getpgid(pid)`, which a Popen child shares with its parent — on CI that killed
    the test runner mid-suite, the same "a stop took out more than it meant to" shape
    the verb exists to end.
    """

    def test_refuses_to_terminate_the_calling_process(self):
        import os

        if os.name == "nt":
            self.skipTest("the upward guards live on the POSIX path")
        killed, detail = terminate_process_tree(os.getpid())
        self.assertFalse(killed)
        self.assertIn("refusing", detail)

    def test_refuses_to_terminate_an_ancestor(self):
        """`fathom stop --now` from the shell that launched the matrix takes the
        stopper with it. Refuse rather than honour it."""
        import os

        if os.name == "nt":
            self.skipTest("the upward guards live on the POSIX path")
        killed, detail = terminate_process_tree(os.getppid())
        self.assertFalse(killed, detail)
        self.assertIn("refusing", detail)

    def test_a_sibling_in_the_same_group_survives(self):
        """The regression CI paid for: a bystander sharing our process group lives."""
        bystander = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        target = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            terminate_process_tree(target.pid)
            target.wait(timeout=30)
            self.assertIsNone(
                bystander.poll(), "terminating one holder must not reach its siblings"
            )
        finally:
            for p in (bystander, target):
                if p.poll() is None:
                    p.kill()
                    p.wait(timeout=10)

    def test_a_grandchild_dies_with_the_tree(self):
        """`uv -> fathom -> claude`: the unit that has to go is the tree."""
        with tempfile.TemporaryDirectory(prefix="fathom-tree-") as tmp:
            beat = Path(tmp) / "grandchild.beat"
            child_src = Path(tmp) / "child.py"
            child_src.write_text(_TREE_PARENT, encoding="utf-8")
            parent = subprocess.Popen(
                [sys.executable, str(child_src), str(beat), _TREE_GRANDCHILD],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline and not beat.exists():
                    time.sleep(0.05)
                self.assertTrue(beat.exists(), "the grandchild never started beating")

                terminate_process_tree(parent.pid)
                time.sleep(1.5)
                # Liveness by artifact, not by pid: robust to zombies and reparenting.
                stopped_at = beat.stat().st_mtime
                time.sleep(1.5)
                self.assertEqual(
                    beat.stat().st_mtime,
                    stopped_at,
                    "the grandchild outlived the tree it belonged to",
                )
            finally:
                if parent.poll() is None:
                    parent.kill()
                    parent.wait(timeout=10)

    def test_kills_a_live_child(self):
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            killed, detail = terminate_process_tree(proc.pid)
            self.assertTrue(killed, detail)
            proc.wait(timeout=30)
        finally:
            if proc.poll() is None:  # pragma: no cover - only on a failed kill
                proc.kill()
                proc.wait(timeout=10)

    def test_a_pid_that_is_gone_is_reported_not_raised(self):
        proc = subprocess.Popen([sys.executable, "-c", "pass"])
        proc.wait(timeout=30)
        killed, detail = terminate_process_tree(proc.pid)
        self.assertIsInstance(killed, bool)
        self.assertIsInstance(detail, str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
