"""A native run lock with a heartbeat — fathom's own mutual exclusion (FATH-B53).

A paid matrix consumes one seat's credential and rate budget, so two concurrent runs
on the same seat interfere. fathom shipped no lock, and serialization was delegated
to whatever convention each caller invented. With several concurrent sessions on one
seat that produced **three deadlocks in a single day** — twice from a holder that had
finished spending and never released, once from a process that had died still holding
the claim — and, over the three waves since, four hand-written stop/pause scripts, two
of them on the same day.

The cost was never the waiting. A session blocked on a phantom holder either stalls a
whole wave or talks itself into overriding, and **neither is decidable from the
artifacts**, because nothing in the claim recorded whether its holder was alive.

## The two properties the ad-hoc conventions lacked

**A heartbeat.** The holder rewrites its own ticket every
:data:`HEARTBEAT_INTERVAL_S`, so staleness is decidable from the lock's own timestamps
against a stated horizon (:data:`STALE_AFTER_S`) rather than by guessing at process
tables. A finished or dead holder expires instead of blocking forever. Release happens
in a ``finally``, which covers an exception, a ``SystemExit`` and a Ctrl-C; it does not
and cannot cover a hard kill, which is exactly why the heartbeat is the load-bearing
half rather than a nicety.

**A FIFO ticket directory** rather than a single flag. Each acquirer creates its own
ticket with ``O_EXCL`` — so creation never contends — and the holder is the
lowest-ordered *live* ticket. The release-to-relock window stops being a race that the
politest poller always loses.

## Why the seam is per-heartbeat and not per-trial

A series trial can run for an hour. A per-trial beat therefore gives a staleness horizon
no shorter than the longest trial, which is precisely the horizon that made the three
observed deadlocks undecidable. A background thread beating every 15s gives a 120s
horizon — eight missed beats, so a stalled writer is not mistaken for a dead one.

## Why this is testable, when FATH-B53 said it was not

The row was deferred partly because "its failure mode is multi-process on one
authenticated seat, which this repo's gate cannot exercise at all". That is true of the
*seat* and false of the *lock*: the lock is a directory, and who holds it is a pure
function of the ticket files in it. So this module splits the way ``smoke`` and
``arming`` already do — :func:`decide` and its helpers are pure over
:class:`Ticket` records and unit-tested against handwritten tickets, while the I/O
below them is exercised by a real multi-process contention test that spends nothing.

Stdlib only.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Iterator, Sequence
from pathlib import Path

# The lock lives OUTSIDE `ledger/`. `ledger/` is tracked and `.gitignore` has no entry
# for it, so a lock file under it becomes a committed artifact the first time anyone
# runs `git add ledger/` after a matrix. `/.fathom/` is gitignored in the same change
# that introduced this module — the other half of FATH-B53's stated trigger.
LOCK_ROOT = Path(".fathom") / "locks"

HEARTBEAT_INTERVAL_S = 15.0
STALE_AFTER_S = 120.0
POLL_INTERVAL_S = 1.0

_TICKET_SUFFIX = ".ticket.json"
_CHOOSING_SUFFIX = ".choosing"
_STOP_FILE = "stop.json"

# How long a "choosing" marker may stand before it is ignored.  Picking a number and
# writing one small file takes microseconds; a marker older than this belongs to a
# process that died between the two, and honouring it forever would be the very
# phantom-holder deadlock this module exists to end.
CHOOSING_STALE_AFTER_S = 30.0


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Ticket:
    """One acquirer's claim on a bank's lock.

    ``name`` is the ticket's file name and carries the FIFO key; ``heartbeat_s`` is
    wall-clock seconds, rewritten by the holder's own beat thread and the only
    evidence anyone else has that the holder is alive.
    """

    name: str
    pid: int
    created_ns: int
    heartbeat_s: float
    host: str = ""
    label: str = ""

    @property
    def order_key(self) -> tuple[int, int, str]:
        """FIFO order: creation instant, then pid, then the name — total and stable."""
        return (self.created_ns, self.pid, self.name)

    def age_s(self, now_s: float) -> float:
        return now_s - self.heartbeat_s

    def describe(self, now_s: float) -> str:
        who = f"pid {self.pid}" + (f" on {self.host}" if self.host else "")
        what = f" ({self.label})" if self.label else ""
        return f"{who}{what}, last heartbeat {self.age_s(now_s):.0f}s ago"


@dataclasses.dataclass(frozen=True)
class LockDecision:
    """Who holds the lock, who is stale, and whether *me* may proceed."""

    holder: Ticket | None
    stale: tuple[Ticket, ...]
    holds: bool


@dataclasses.dataclass(frozen=True)
class StopRequest:
    """A recorded request that the current holder stop."""

    requested_at_s: float
    at_boundary: bool
    reason: str = ""


# ---------------------------------------------------------------------------
# Pure decisions — no I/O, unit-tested against handwritten tickets
# ---------------------------------------------------------------------------


def is_stale(ticket: Ticket, *, now_s: float, stale_after_s: float = STALE_AFTER_S) -> bool:
    """A ticket whose holder has not beaten within the horizon.

    A heartbeat in the *future* (a clock that moved, or a shared directory across hosts
    with skewed clocks) is not stale: treating it as stale would let a second run start
    beside a live one, which is the failure this lock exists to prevent. Erring toward
    "still held" costs waiting; erring the other way costs two matrices on one seat.
    """
    return ticket.age_s(now_s) > stale_after_s


def decide(
    tickets: Sequence[Ticket],
    me: str | None,
    *,
    now_s: float,
    stale_after_s: float = STALE_AFTER_S,
) -> LockDecision:
    """Who holds the lock, given every ticket currently in the directory.

    The holder is the lowest-ordered ticket that is not stale. Stale tickets are named
    separately so a waiter can prune them — the self-healing half: a holder that died
    without releasing expires from its own timestamps rather than blocking forever.
    """
    stale = tuple(
        sorted(
            (t for t in tickets if is_stale(t, now_s=now_s, stale_after_s=stale_after_s)),
            key=lambda t: t.order_key,
        )
    )
    live = sorted((t for t in tickets if t not in stale), key=lambda t: t.order_key)
    holder = live[0] if live else None
    return LockDecision(
        holder=holder,
        stale=stale,
        holds=holder is not None and me is not None and holder.name == me,
    )


# ---------------------------------------------------------------------------
# Ticket directory I/O
# ---------------------------------------------------------------------------


def lock_dir_for(bank: str, lock_root: Path | None = None) -> Path:
    return (Path(lock_root) if lock_root is not None else LOCK_ROOT) / bank


def _parse_ticket(path: Path) -> Ticket | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # A ticket being written right now, or one whose writer died mid-write. It is
        # not evidence of a live holder, and it is not evidence of anything else either.
        return None
    if not isinstance(data, dict):
        return None
    try:
        return Ticket(
            name=path.name,
            pid=int(data["pid"]),
            created_ns=int(data["created_ns"]),
            heartbeat_s=float(data["heartbeat_s"]),
            host=str(data.get("host", "")),
            label=str(data.get("label", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def read_tickets(lock_dir: Path) -> list[Ticket]:
    """Every parsable ticket in *lock_dir*, in FIFO order."""
    try:
        entries = sorted(Path(lock_dir).iterdir())
    except OSError:
        return []
    tickets = [
        t
        for p in entries
        if p.name.endswith(_TICKET_SUFFIX) and (t := _parse_ticket(p)) is not None
    ]
    return sorted(tickets, key=lambda t: t.order_key)


def choosing_now(
    lock_dir: Path, *, exclude: str | None = None, now_s: float | None = None
) -> list[str]:
    """Acquirers that have picked a number but whose ticket is not visible yet.

    The window between "decide my number" and "my ticket file exists" is small and it
    is not zero, and a waiter that reads the directory inside it can see no earlier
    ticket, conclude it holds, and start beside the run that was already choosing.
    A four-process contention test caught exactly that.  So an acquirer raises this
    flag *before* it picks, drops it once its ticket is written, and nobody decides
    while a flag is up — Lamport's bakery, with the marker doing the ordering work the
    filesystem will not do.
    """
    now = time.time() if now_s is None else now_s
    out: list[str] = []
    try:
        entries = sorted(Path(lock_dir).iterdir())
    except OSError:
        return out
    for p in entries:
        if not p.name.endswith(_CHOOSING_SUFFIX) or p.name == exclude:
            continue
        try:
            age = now - p.stat().st_mtime
        except OSError:
            continue
        if age <= CHOOSING_STALE_AFTER_S:
            out.append(p.name)
        else:
            with contextlib.suppress(OSError):
                p.unlink()
    return out


def holders(
    bank: str, *, lock_root: Path | None = None, now_s: float | None = None
) -> LockDecision:
    """Who, if anyone, currently holds *bank*'s lock."""
    now = time.time() if now_s is None else now_s
    return decide(read_tickets(lock_dir_for(bank, lock_root)), None, now_s=now)


# ---------------------------------------------------------------------------
# Stop requests
# ---------------------------------------------------------------------------


def request_stop(
    bank: str, *, lock_root: Path | None = None, at_boundary: bool = True, reason: str = ""
) -> StopRequest:
    """Record a request that *bank*'s holder stop; return what was written."""
    d = lock_dir_for(bank, lock_root)
    d.mkdir(parents=True, exist_ok=True)
    req = StopRequest(requested_at_s=time.time(), at_boundary=at_boundary, reason=reason)
    _atomic_write_json(d / _STOP_FILE, dataclasses.asdict(req))
    return req


def read_stop_request(bank: str, *, lock_root: Path | None = None) -> StopRequest | None:
    return _read_stop_request(lock_dir_for(bank, lock_root))


def _read_stop_request(lock_dir: Path) -> StopRequest | None:
    path = Path(lock_dir) / _STOP_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        return StopRequest(
            requested_at_s=float(data["requested_at_s"]),
            at_boundary=bool(data.get("at_boundary", True)),
            reason=str(data.get("reason", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def clear_stop_request(bank: str, *, lock_root: Path | None = None) -> None:
    with contextlib.suppress(OSError):
        (lock_dir_for(bank, lock_root) / _STOP_FILE).unlink()


# ---------------------------------------------------------------------------
# Process-tree termination — the `--now` escalation
# ---------------------------------------------------------------------------


def parse_ps_output(text: str) -> dict[int, int]:
    """``{pid: ppid}`` from ``ps -A -o pid=,ppid=`` output. Pure, so it is testable.

    Unparsable lines are dropped rather than guessed at: a process this cannot see is
    simply not in the tree, which is the safe direction — the walk then signals fewer
    processes, never more.
    """
    parents: dict[int, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            parents[int(parts[0])] = int(parts[1])
        except ValueError:
            continue
    return parents


def _posix_parents() -> dict[int, int]:
    """``{pid: ppid}`` for every visible process, via POSIX ``ps``.

    Walking the tree explicitly is the only safe way to reach a holder's descendants:
    see :func:`terminate_process_tree` for why the process group is not.
    """
    proc = subprocess.run(  # noqa: S603
        ["ps", "-A", "-o", "pid=,ppid="],  # noqa: S607
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return parse_ps_output(proc.stdout or "")


def descendants_of(pid: int, parents: dict[int, int]) -> list[int]:
    """Every descendant of *pid*, deepest first, never including *pid* itself.

    Pure over a ``{pid: ppid}`` map, so the walk is unit-testable without spawning
    anything — and a cycle in a malformed map terminates rather than hanging.
    """
    children: dict[int, list[int]] = {}
    for child, parent in parents.items():
        children.setdefault(parent, []).append(child)
    out: list[int] = []
    seen = {pid}
    frontier = [pid]
    while frontier:
        current = frontier.pop()
        for child in sorted(children.get(current, ())):
            if child in seen:
                continue
            seen.add(child)
            out.append(child)
            frontier.append(child)
    out.reverse()  # deepest first: a parent outliving its children respawns nothing
    return out


def ancestors_of(pid: int, parents: dict[int, int]) -> list[int]:
    """Every process *pid* descends from, nearest first. Cycle-safe."""
    out: list[int] = []
    seen = {pid}
    current = parents.get(pid)
    while current is not None and current > 0 and current not in seen:
        seen.add(current)
        out.append(current)
        current = parents.get(current)
    return out


def terminate_process_tree(pid: int) -> tuple[bool, str]:
    """Kill *pid* and its descendants; return ``(killed, detail)``.

    The recorded incident: stopping the wrapper left ``uv -> fathom -> claude`` alive
    and ~$2 went over ~15 minutes on killing it by hand. The tree, not the process, is
    the unit that has to go.

    **Not the process group.** A first implementation sent ``SIGTERM`` to
    ``os.getpgid(pid)``, which is correct only when the target leads its own group. A
    process started by ``Popen`` inherits its parent's group, so that call reaches the
    *caller* — on CI it killed the test runner mid-suite, which is exactly the
    "a stop took out more than it meant to" failure this verb exists to end. The group
    is used only when the target genuinely leads one that is not ours; otherwise the
    descendants are walked explicitly and signalled deepest-first.
    """
    if os.name == "nt":
        proc = subprocess.run(  # noqa: S603
            ["taskkill", "/PID", str(pid), "/T", "/F"],  # noqa: S607
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        detail = ((proc.stdout or "") + (proc.stderr or "")).strip()
        return proc.returncode == 0, detail or f"taskkill exited {proc.returncode}"

    import signal

    if pid == os.getpid():
        return False, "refusing to terminate this process"
    try:
        own_group = os.getpgid(0)
        target_group = os.getpgid(pid)
    except OSError as exc:
        return False, f"{type(exc).__name__}: {exc}"

    if target_group == pid and target_group != own_group:
        try:
            os.killpg(target_group, signal.SIGTERM)
            return True, f"SIGTERM to process group {target_group} (the holder leads it)"
        except OSError as exc:
            return False, f"{type(exc).__name__}: {exc}"

    try:
        parents = _posix_parents()
    except OSError as exc:
        parents = {}
        note = f" (child walk unavailable: {type(exc).__name__})"
    else:
        note = ""
    # Reaching UPWARD is how a stop becomes an outage. A holder this process is running
    # inside — `fathom stop --now` issued from the very shell that launched the matrix —
    # is not a coherent request: honouring it would take this process with it.
    ours = {os.getpid(), *ancestors_of(os.getpid(), parents)}
    if pid in ours:
        return False, f"refusing: {pid} is an ancestor of this process"
    victims = [*descendants_of(pid, parents), pid]
    signalled: list[int] = []
    for victim in victims:
        if victim in ours:
            continue
        try:
            os.kill(victim, signal.SIGTERM)
            signalled.append(victim)
        except OSError:
            continue
    if not signalled:
        return False, f"nothing signalled for {pid} (already gone?){note}"
    return True, f"SIGTERM to {len(signalled)} process(es) under {pid}: {signalled}{note}"


# ---------------------------------------------------------------------------
# The lock itself
# ---------------------------------------------------------------------------


class LockTimeout(RuntimeError):
    """The wait for the lock exceeded its bound."""


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Write *payload* to *path* atomically, so a reader never sees a half file."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


class RunLock:
    """Serialize paid runs of one bank across processes.

    Typical use is :meth:`held`, which acquires, beats, and releases in a ``finally``::

        with RunLock("my-bank", label="fathom run").held(out=sys.stdout) as lock:
            ...
            if lock.stop_requested():
                return EXIT_STOPPED
    """

    def __init__(
        self,
        bank: str,
        *,
        lock_root: Path | None = None,
        label: str = "",
        stale_after_s: float = STALE_AFTER_S,
        heartbeat_interval_s: float = HEARTBEAT_INTERVAL_S,
    ) -> None:
        self.bank = bank
        self.dir = lock_dir_for(bank, lock_root)
        self.label = label
        self.stale_after_s = stale_after_s
        self.heartbeat_interval_s = heartbeat_interval_s
        self.ticket_name: str | None = None
        self._ticket_path: Path | None = None
        self._choosing_path: Path | None = None
        self._created_ns = 0
        self._beat_stop = threading.Event()
        self._beat_thread: threading.Thread | None = None

    # -- ticket lifecycle ---------------------------------------------------

    def _write_ticket(self, heartbeat_s: float) -> None:
        assert self._ticket_path is not None
        _atomic_write_json(
            self._ticket_path,
            {
                "pid": os.getpid(),
                "created_ns": self._created_ns,
                "heartbeat_s": heartbeat_s,
                "host": socket.gethostname(),
                "label": self.label,
            },
        )

    def _take_ticket(self) -> None:
        """Pick a number and publish a ticket, under a `choosing` flag.

        The flag goes up BEFORE the number is picked and comes down only once the
        ticket is on disk, so no waiter can decide inside the window where this
        acquirer has a number but no visible ticket. Without it a four-process race
        put two runs inside the lock at once.
        """
        self.dir.mkdir(parents=True, exist_ok=True)
        uid = uuid.uuid4().hex[:8]
        self._choosing_path = self.dir / f"{os.getpid():07d}-{uid}{_CHOOSING_SUFFIX}"
        self._choosing_path.touch()
        try:
            self._created_ns = time.time_ns()
            # A unique name means O_EXCL creation never contends; ordering is decided
            # by the recorded instant, not by who won a filesystem race.
            name = f"{self._created_ns:020d}-{os.getpid():07d}-{uid}{_TICKET_SUFFIX}"
            self.ticket_name = name
            self._ticket_path = self.dir / name
            self._write_ticket(time.time())
        finally:
            path, self._choosing_path = self._choosing_path, None
            with contextlib.suppress(OSError):
                path.unlink()

    def _prune(self, stale: Sequence[Ticket]) -> None:
        for ticket in stale:
            if ticket.name == self.ticket_name:
                continue
            with contextlib.suppress(OSError):
                (self.dir / ticket.name).unlink()

    # -- acquisition --------------------------------------------------------

    def acquire(
        self,
        *,
        timeout_s: float | None = None,
        poll_s: float = POLL_INTERVAL_S,
        out: object | None = None,
    ) -> None:
        """Queue for the lock and return once this process holds it.

        Waits indefinitely by default, because a bounded wait that gives up is how a
        caller ends up running two matrices on one seat anyway. A holder that has died
        is not a reason to wait: its ticket goes stale within
        :data:`STALE_AFTER_S` and is pruned here.
        """
        self._take_ticket()
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        announced = ""
        held_by = "nobody (raced)"
        while True:
            now = time.time()
            # The bound is checked FIRST, so every branch below honours it. A bound
            # applied only on one path is not a bound: a waiter blocked on an
            # abandoned `choosing` marker sat for the marker's whole horizon and
            # returned success, ignoring the timeout it had been given.
            if deadline is not None and time.monotonic() >= deadline:
                self.release()
                raise LockTimeout(
                    f"waited {timeout_s:.0f}s for bank {self.bank!r}; held by {held_by}"
                )
            # Nobody decides while another acquirer sits between its number and its
            # published ticket: inside that window the directory understates the queue,
            # and a waiter reading it concludes it holds when it does not.
            choosing = choosing_now(self.dir, now_s=now)
            if choosing:
                held_by = f"an acquirer still choosing ({', '.join(choosing)})"
                time.sleep(min(poll_s, 0.02))
                continue
            decision = decide(
                read_tickets(self.dir),
                self.ticket_name,
                now_s=now,
                stale_after_s=self.stale_after_s,
            )
            if decision.stale:
                self._prune(decision.stale)
                continue
            if decision.holds:
                self._start_heartbeat()
                return
            if decision.holder is not None:
                held_by = decision.holder.describe(now)
            if out is not None and decision.holder is not None:
                line = decision.holder.describe(now)
                if line != announced:
                    announced = line
                    print(
                        f"lock: waiting for bank {self.bank!r} — held by {line}; "
                        f"a holder silent for {self.stale_after_s:.0f}s is treated as dead "
                        f"and its claim released",
                        file=out,  # type: ignore[arg-type]
                    )
            time.sleep(poll_s)

    def release(self) -> None:
        """Drop this process's ticket and stop beating. Safe to call twice."""
        self._beat_stop.set()
        thread, self._beat_thread = self._beat_thread, None
        if thread is not None:
            thread.join(timeout=self.heartbeat_interval_s)
        for path in (self._ticket_path, self._choosing_path):
            if path is not None:
                with contextlib.suppress(OSError):
                    path.unlink()
        self._ticket_path = None
        self._choosing_path = None
        self.ticket_name = None

    @contextlib.contextmanager
    def held(
        self,
        *,
        timeout_s: float | None = None,
        poll_s: float = POLL_INTERVAL_S,
        out: object | None = None,
    ) -> Iterator[RunLock]:
        self.acquire(timeout_s=timeout_s, poll_s=poll_s, out=out)
        try:
            yield self
        finally:
            # Covers a raised exception, a SystemExit and a Ctrl-C. It cannot cover a
            # hard kill of this process — which is what the heartbeat is for.
            self.release()

    # -- heartbeat ----------------------------------------------------------

    def _start_heartbeat(self) -> None:
        self._beat_stop.clear()

        def _beat() -> None:
            while not self._beat_stop.wait(self.heartbeat_interval_s):
                if self._ticket_path is None:
                    return
                with contextlib.suppress(OSError):
                    self._write_ticket(time.time())

        self._beat_thread = threading.Thread(
            target=_beat, name=f"fathom-runlock-{self.bank}", daemon=True
        )
        self._beat_thread.start()

    def beat(self) -> None:
        """Beat once, synchronously. The thread does this; callers rarely need to."""
        if self._ticket_path is not None:
            with contextlib.suppress(OSError):
                self._write_ticket(time.time())

    # -- stop requests ------------------------------------------------------

    def stop_requested(self) -> StopRequest | None:
        """A stop request placed after this holder took its ticket, if any.

        Scoped by time so a request left behind by an earlier run cannot halt this one
        before it has bought anything — a stale stop is exactly as bad as a stale lock.
        """
        req = _read_stop_request(self.dir)
        if req is None:
            return None
        if req.requested_at_s < self._created_ns / 1e9:
            return None
        return req

    def clear_stop_request(self) -> None:
        with contextlib.suppress(OSError):
            (self.dir / _STOP_FILE).unlink()


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - convenience entry
    """`python -m fathom.runlock <bank>` — report who holds a bank's lock."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: python -m fathom.runlock <bank>", file=sys.stderr)
        return 1
    now = time.time()
    decision = holders(args[0])
    if decision.holder is None:
        print(f"nothing holds the lock for bank {args[0]!r}")
        return 0
    print(f"bank {args[0]!r} held by {decision.holder.describe(now)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
