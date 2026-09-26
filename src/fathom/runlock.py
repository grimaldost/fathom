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

**A heartbeat.** Every queued acquirer, the holder included, rewrites its own ticket every
:data:`HEARTBEAT_INTERVAL_S`, so staleness is decidable from the lock's own timestamps
against a stated horizon (:data:`STALE_AFTER_S`) rather than by guessing at process
tables. A finished or dead holder expires instead of blocking forever. Release happens
in a ``finally``, which covers an exception, a ``SystemExit`` and a Ctrl-C; it does not
and cannot cover a hard kill, which is exactly why the heartbeat is the load-bearing
half rather than a nicety.

**A FIFO ticket directory** rather than a single flag. Each acquirer creates its own
uniquely named ticket, so creation never contends, and the holder is the
lowest-ordered *live* ticket. The release-to-relock window stops being a race that the
politest poller always loses.

## Why the order is a bakery number and not a clock reading

The order is Lamport's bakery: under a ``choosing`` flag an acquirer takes one more than
the highest number visible in the directory, and tickets are ordered by
``(number, pid, name)``. Until 0.7.0 it was ``(created_ns, pid, name)`` with
``created_ns = time.time_ns()``. On Windows under Python 3.12 that clock advances in
15.625 ms steps, so two tickets taken inside one step tied. The tie then fell to the pid,
or to the random uid in the name, and a later arrival could sort ahead of a holder that
had already decided it held. Two runs were then inside the lock at once. A number taken
from what is visible cannot tie with a ticket that was already visible, whatever the
clock's resolution. ``created_ns`` is still recorded, because a stop request is scoped by
it, but it orders nothing.

The number is the leading field of the ticket's file name, not a JSON field, so every
number is read from one directory listing. Read from file contents, a ticket whose read
failed would be missed, and a missed ticket lets the next acquirer take a number at or
below it. A ticket written by 0.6.2 or earlier leads its name with its ``created_ns``
in the same position, so it is read as that number, deliberately. A 0.7.0 acquirer that
sees it takes a larger one, and a 0.6.2 ticket created after a 0.7.0 one carries a
nanosecond timestamp far above any number counted up from an empty directory. A queue
that mixes the two versions therefore stays in arrival order, except for two tickets
taken inside one clock step, which is the window 0.6.2 already had.

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
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import warnings
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

# Pauses between attempts to remove a lock file this process owns (0.785 s in total).
# On Windows an unlink fails with a sharing violation while any other process has the
# file open, and a waiter reading a ticket has it open for one small read. Retrying
# across a short bounded backoff outlasts that read. Giving up at once left the ticket
# reading as a live holder until STALE_AFTER_S.
UNLINK_BACKOFF_S = (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4)

# A ticket's file name leads with its FIFO number, then the pid that took it.
_TICKET_NUMBER = re.compile(r"(\d+)-(?:(\d+)-)?", flags=re.ASCII)


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Ticket:
    """One acquirer's claim on a bank's lock.

    ``name`` is the ticket's file name, and it leads with ``number``, the FIFO key.
    ``created_ns`` is when the ticket was taken; it is recorded and orders nothing.
    ``heartbeat_s`` is wall-clock seconds, rewritten by the owner's beat thread while
    it waits and while it holds, and the only evidence anyone else has that the owner
    is alive.
    """

    name: str
    number: int
    pid: int
    created_ns: int
    heartbeat_s: float
    host: str = ""
    label: str = ""

    @property
    def order_key(self) -> tuple[int, int, str]:
        """FIFO order: the bakery number, then pid, then the name — total and stable.

        Equal numbers only come from two acquirers choosing at the same time, and the
        ``choosing`` flag makes every decider wait until both tickets are visible, so the
        tie is broken the same way by everyone who reads it.
        """
        return (self.number, self.pid, self.name)

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


def ticket_number(name: str) -> int | None:
    """The FIFO number a ticket's file name leads with; None for any other file.

    A name written by 0.6.2 or earlier leads with its ``created_ns`` in the same
    position and is read as that number (see the module docstring for why that keeps
    a mixed queue in order).
    """
    if not name.endswith(_TICKET_SUFFIX):
        return None
    match = _TICKET_NUMBER.match(name)
    return int(match.group(1)) if match else None


def next_ticket_number(lock_dir: Path) -> int:
    """One more than the highest ticket number visible in *lock_dir*; 1 when there is none.

    Read from the directory listing alone. Every ticket counts, stale or unparsable
    ones included, because a number that is too high only costs a place in the queue,
    while one that is too low can jump it. A listing that fails raises: guessing an
    empty directory here would put this acquirer at the front.
    """
    numbers = [n for p in Path(lock_dir).iterdir() if (n := ticket_number(p.name)) is not None]
    return 1 + max(numbers, default=0)


def _parse_ticket(path: Path) -> Ticket | None:
    match = _TICKET_NUMBER.match(path.name) if path.name.endswith(_TICKET_SUFFIX) else None
    if match is None:
        return None
    number = int(match.group(1))
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # Released or pruned since the directory was listed.
        return None
    except OSError:
        return _unread_ticket(path, number, int(match.group(2) or 0))
    try:
        data = json.loads(text)
    except ValueError:
        # Writes are atomic (`_atomic_write_json`), so no reader sees a half-written
        # ticket. A file that does not parse was not written whole by this module, and
        # it is not evidence of a live holder.
        return None
    if not isinstance(data, dict):
        return None
    try:
        return Ticket(
            name=path.name,
            number=number,
            pid=int(data["pid"]),
            created_ns=int(data["created_ns"]),
            heartbeat_s=float(data["heartbeat_s"]),
            host=str(data.get("host", "")),
            label=str(data.get("label", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _unread_ticket(path: Path, number: int, pid: int) -> Ticket | None:
    """A ticket that exists but cannot be read right now; it keeps its place.

    On Windows a read fails with PermissionError while the owner's heartbeat replaces
    the file. Treating such a ticket as absent let a waiter that read the directory at
    that moment find nobody ahead of it and hold beside the holder. Its order comes
    from its name. Its file's modification time stands in for the heartbeat it hides,
    because every beat replaces the file, so a dead ticket that stays unreadable still
    goes stale. When even that cannot be read, the ticket is taken as just beaten: the
    error is toward "still held", which costs waiting rather than a second run.
    """
    try:
        heartbeat_s = path.stat().st_mtime
    except FileNotFoundError:
        return None
    except OSError:
        heartbeat_s = time.time()
    return Ticket(name=path.name, number=number, pid=pid, created_ns=0, heartbeat_s=heartbeat_s)


def read_tickets(lock_dir: Path) -> list[Ticket]:
    """Every ticket in *lock_dir*, in FIFO order.

    A ticket that cannot be read right now is included (see :func:`_unread_ticket`);
    one that is malformed is not.
    """
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
    proc = subprocess.run(
        ["ps", "-A", "-o", "pid=,ppid="],
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
        proc = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
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


def _unlink_retrying(path: Path) -> OSError | None:
    """Remove *path*, retrying while another process holds it open.

    Returns None once the file is gone (a file that is already missing counts, so a
    second release is harmless), else the last error. Only ``PermissionError`` is
    retried: that is how Windows reports a sharing violation, and a file whose
    deletion is still pending. Any other ``OSError`` is not transient and is returned
    at once.
    """
    last: OSError | None = None
    for pause in (0.0, *UNLINK_BACKOFF_S):
        if pause:
            time.sleep(pause)
        try:
            path.unlink(missing_ok=True)
        except PermissionError as exc:
            last = exc
            continue
        except OSError as exc:
            return exc
        return None
    return last


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

    def _write_ticket(self, path: Path, heartbeat_s: float) -> None:
        _atomic_write_json(
            path,
            {
                "pid": os.getpid(),
                "created_ns": self._created_ns,
                "heartbeat_s": heartbeat_s,
                "host": socket.gethostname(),
                "label": self.label,
            },
        )

    def _take_ticket(self) -> None:
        """Take a number and publish a ticket, under a `choosing` flag (Lamport's bakery).

        The flag goes up BEFORE the number is taken and comes down only once the
        ticket is on disk, so no waiter can decide inside the window where this
        acquirer has a number but no visible ticket. Without it a four-process race
        put two runs inside the lock at once.

        The number is one more than the highest visible, read under the flag. Any
        ticket that was already visible, a holder's included, therefore sorts ahead of
        this one. Two acquirers choosing at once can draw the same number; each sees the
        other's flag, waits, and then breaks the tie by ``(pid, name)``, like everyone
        else who reads it.
        """
        self.dir.mkdir(parents=True, exist_ok=True)
        uid = uuid.uuid4().hex[:8]
        self._choosing_path = self.dir / f"{os.getpid():07d}-{uid}{_CHOOSING_SUFFIX}"
        self._choosing_path.touch()
        try:
            number = next_ticket_number(self.dir)
            # Recorded, not ordering: a stop request is scoped by when this ticket
            # was taken.
            self._created_ns = time.time_ns()
            # A unique name means creation never contends.
            name = f"{number:020d}-{os.getpid():07d}-{uid}{_TICKET_SUFFIX}"
            self.ticket_name = name
            self._ticket_path = self.dir / name
            self._write_ticket(self._ticket_path, time.time())
        finally:
            path, self._choosing_path = self._choosing_path, None
            self._remove_own(
                path,
                consequence=(
                    "every acquirer on this bank, this one included, waits on it until it "
                    f"is {CHOOSING_STALE_AFTER_S:.0f}s old"
                ),
            )

    def _remove_own(self, path: Path, *, consequence: str) -> None:
        """Remove a lock file this process wrote, and report a failure that outlasts the retries.

        Reported as a warning, as the rest of fathom reports what it swallowed. Not
        raised: a release runs in a ``finally``, and an exception there would replace
        the one already in flight.
        """
        err = _unlink_retrying(path)
        if err is not None:
            warnings.warn(
                f"run lock: could not remove {path} after {len(UNLINK_BACKOFF_S) + 1} "
                f"attempts ({type(err).__name__}: {err}); {consequence}",
                stacklevel=3,
            )

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

        The ticket is beaten from the moment it exists, not from the moment it holds.
        Until 0.7.0 only a holder beat, so a wait longer than the horizon made the
        waiter's own ticket stale: it could never hold, and other waiters pruned it.
        """
        try:
            self._take_ticket()
            self._start_heartbeat()
            self._wait_for_turn(timeout_s=timeout_s, poll_s=poll_s, out=out)
        except BaseException:
            # A timeout, a Ctrl-C or any error from the moment the ticket exists drops
            # the ticket and stops its beat, including one raised while the beat thread
            # starts. Otherwise a live process keeps a place in a queue it has left.
            self.release()
            raise

    def _wait_for_turn(self, *, timeout_s: float | None, poll_s: float, out: object | None) -> None:
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
                # No `continue`: the decision already leaves stale tickets out, so
                # pruning them does not change it. Going straight round again spun
                # without a pause whenever a stale ticket stayed: this waiter's own,
                # which it never prunes, or one whose unlink failed.
                self._prune(decision.stale)
            if decision.holds:
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
        """Drop this process's ticket and stop beating. Safe to call twice.

        A ticket that a reader holds open is retried across :data:`UNLINK_BACKOFF_S`.
        One that still cannot be removed is reported with a warning. Until 0.7.0 the
        failure was swallowed, and the ticket then read as a live holder for up to
        :data:`STALE_AFTER_S`.
        """
        self._beat_stop.set()
        thread, self._beat_thread = self._beat_thread, None
        if thread is not None:
            thread.join(timeout=self.heartbeat_interval_s)
        if self._ticket_path is not None:
            self._remove_own(
                self._ticket_path,
                consequence=(
                    f"it reads as a live claim on bank {self.bank!r} until its last "
                    f"heartbeat is {self.stale_after_s:.0f}s old"
                ),
            )
        if self._choosing_path is not None:
            self._remove_own(
                self._choosing_path,
                consequence=(
                    f"acquirers on bank {self.bank!r} wait on it until it is "
                    f"{CHOOSING_STALE_AFTER_S:.0f}s old"
                ),
            )
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
                self._beat_once()

        self._beat_thread = threading.Thread(
            target=_beat, name=f"fathom-runlock-{self.bank}", daemon=True
        )
        self._beat_thread.start()

    def beat(self) -> None:
        """Beat once, synchronously. The thread does this; callers rarely need to."""
        self._beat_once()

    def _beat_once(self) -> None:
        path = self._ticket_path
        if path is None:
            return
        with contextlib.suppress(OSError):
            self._write_ticket(path, time.time())
        # release() joins this thread for one interval only, so a write slower than
        # that can land after release() removed the ticket. It would recreate the
        # ticket with nobody left to beat it, so the write that outlived its release
        # removes itself.
        if self._beat_stop.is_set() or path != self._ticket_path:
            self._remove_own(
                path,
                consequence=(
                    f"it reads as a live claim on bank {self.bank!r} until it is "
                    f"{self.stale_after_s:.0f}s old"
                ),
            )

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
