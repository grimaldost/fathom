"""The seat's OAuth credential: how much life it has, and one run's carried copy of it.

Two things live here, both standard library only and both bound by ADR-0004: fathom copies
the credential file, and the only values it ever lifts out of it are the two expiry
timestamps.

* :func:`read_credential_status` reads ``expiresAt`` and ``refreshTokenExpiresAt`` and
  nothing else. ``fathom smoke`` and the pre-flight of ``fathom run`` judge the seat with
  it (``fathom.smoke.assert_credential_live``).
* :class:`CredentialStore` is the copy a run carries from spawn to spawn (FATH-B55). Each
  spawn runs under a throwaway ``CLAUDE_CONFIG_DIR`` holding a copy of the credential, and
  the CLI refreshes an expired access token inside it. The server rotates the refresh
  token on every refresh, so the token the spawn was handed is spent from then on. Without
  a carried copy the refreshed pair was deleted with the spawn's directory and the next
  spawn started again from the seat's file, whose refresh token was already spent: a
  matrix that outlived one access token died on auth part-way. The store keeps whichever
  credential is newest, by those two timestamps, and every spawn starts from it.
* :func:`write_back_to_seat` hands the newest pair back to the seat's own file when a run,
  a smoke or an acceptance subject ends (T53b, ADR-0004's 2026-10-24 amendment). Without it
  the seat kept the refresh token a spawn had spent, and the owner's next ``claude`` asked
  for ``/login``. It writes only when the copy is newer by both timestamps and the seat's
  file is byte-identical to what was copied from it, and it replaces the file atomically.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from types import TracebackType

CREDENTIAL_FILE = ".credentials.json"

# The only two fields fathom reads. Named as constants so a reviewer can see the whole of
# what leaves the credential file in one place (ADR-0004).
_CRED_BLOCK = "claudeAiOauth"
_CRED_EXPIRES_AT = "expiresAt"
_CRED_REFRESH_EXPIRES_AT = "refreshTokenExpiresAt"


@dataclasses.dataclass(frozen=True)
class CredentialStatus:
    """What the credential file says about its own remaining life — and nothing else.

    Exactly two values are lifted out of it (``expiresAt``, ``refreshTokenExpiresAt``,
    both epoch **milliseconds**).  No token, no scope list, no subscription field, and
    nothing from the ``mcpOAuth`` block ever enters this object, so nothing a smoke
    run prints or logs can carry one (ADR-0004).
    """

    found: bool
    readable: bool
    expires_at_ms: int | None = None
    refresh_expires_at_ms: int | None = None
    detail: str = ""


def read_credential_status(path: str | Path | None = None) -> CredentialStatus:
    """Read the two expiry timestamps from *path* (default ``~/.claude/.credentials.json``).

    Zero cost and no spawn.  Every failure to read is reported as a failure to read —
    a missing, locked or shapeless file gives ``found``/``readable``/values that say so,
    never a silent default that would let the gate pass by absence.
    """
    p = Path(path) if path is not None else Path.home() / ".claude" / CREDENTIAL_FILE
    if not p.is_file():
        return CredentialStatus(
            found=False, readable=False, detail=f"no credential file at {p.name}"
        )
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return CredentialStatus(found=True, readable=False, detail=f"{type(exc).__name__}")
    block = data.get(_CRED_BLOCK) if isinstance(data, dict) else None
    if not isinstance(block, dict):
        return CredentialStatus(
            found=True, readable=True, detail=f"no {_CRED_BLOCK} block in the credential file"
        )

    def _ms(key: str) -> int | None:
        value = block.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    return CredentialStatus(
        found=True,
        readable=True,
        expires_at_ms=_ms(_CRED_EXPIRES_AT),
        refresh_expires_at_ms=_ms(_CRED_REFRESH_EXPIRES_AT),
    )


def _life(status: CredentialStatus) -> tuple[int, int] | None:
    """The order credentials are compared in: access expiry, then refresh expiry.

    ``None`` when the file gives neither timestamp, so it can never win a comparison.
    A refresh moves ``expiresAt`` forward, and so does a new login.
    """
    if not status.readable:
        return None
    if status.expires_at_ms is None and status.refresh_expires_at_ms is None:
        return None
    return (
        -1 if status.expires_at_ms is None else status.expires_at_ms,
        -1 if status.refresh_expires_at_ms is None else status.refresh_expires_at_ms,
    )


class CredentialStore:
    """One run's carried copy of the seat's credential file (FATH-B55).

    :meth:`seed_dir` is the directory a spawn copies its credential from, in place of the
    seat's configuration directory; :meth:`absorb` is called with the spawn's own
    directory when the spawn ends, before that directory is deleted. Both keep whichever
    file is newer by :func:`_life`, so the copy follows a refresh made inside a spawn, and
    also a new login or a refresh the operator's own CLI wrote to the seat's file while
    the run went on.

    The store reads the two timestamps and copies bytes; no token enters a Python object
    (ADR-0004). It writes the seat's file only through :meth:`write_back`, which the caller
    runs once when the run ends, before :meth:`close`. To guard that write, the store keeps
    the digest of the seat's bytes it last copied. Nothing is copied until the first
    :meth:`seed_dir`, so a run that plans no spawn reads nothing. :meth:`close` removes the
    copy; use the store as a context manager.
    """

    def __init__(self, real_config: str | os.PathLike[str] | None = None) -> None:
        self._real = Path(real_config) if real_config else Path.home() / ".claude"
        self._dir: Path | None = None
        self._seat_digest: str | None = None
        self._lock = threading.Lock()

    def seed_dir(self) -> str:
        """The directory holding the newest credential, created on first use."""
        with self._lock:
            if self._dir is None:
                self._dir = Path(tempfile.mkdtemp(prefix="fathom_cred_"))
            taken = self._take_if_newer(self._real / CREDENTIAL_FILE)
            if taken is not None:
                self._seat_digest = taken
            return str(self._dir)

    def write_back(self) -> WriteBack:
        """Hand the carried credential back to the seat's file (T53b); see
        :func:`write_back_to_seat` for the guard. Call it before :meth:`close`."""
        with self._lock:
            if self._dir is None:
                return WriteBack("nothing-to-write", "no spawn copied the seat's credential")
            return write_back_to_seat(
                self._dir / CREDENTIAL_FILE, self._real / CREDENTIAL_FILE, self._seat_digest
            )

    def absorb(self, config_dir: str | os.PathLike[str]) -> bool:
        """Keep the credential a spawn left in *config_dir* if it is newer. True if kept."""
        with self._lock:
            if self._dir is None:
                return False
            return self._take_if_newer(Path(config_dir) / CREDENTIAL_FILE) is not None

    def close(self) -> None:
        """Remove the carried copy. Safe to call more than once."""
        with self._lock:
            held, self._dir = self._dir, None
        if held is None:
            return
        for _ in range(4):
            try:
                shutil.rmtree(held)
                return
            except FileNotFoundError:
                return
            except OSError:
                time.sleep(0.5)

    def __enter__(self) -> CredentialStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _take_if_newer(self, source: Path) -> str | None:
        """Replace the carried file with *source* when *source* is newer (lock held).

        The first file taken is taken as it is, readable or not, which is what a spawn got
        before the store existed. After that, only a readable, strictly newer file
        replaces it, by an atomic rename, so a half-written file is never carried. Returns
        the digest of the bytes taken, or ``None`` when nothing was taken.
        """
        if self._dir is None or not source.is_file():
            return None
        held = self._dir / CREDENTIAL_FILE
        if held.is_file():
            incoming = _life(read_credential_status(source))
            current = _life(read_credential_status(held))
            if incoming is None or (current is not None and incoming <= current):
                return None
        return copy_credential(source, held)


def file_digest(path: str | os.PathLike[str]) -> str | None:
    """The SHA-256 of *path*'s bytes, or ``None`` when it cannot be read. Only the digest
    leaves this function; the guard of :func:`write_back_to_seat` compares it."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def copy_credential(source: str | os.PathLike[str], dest: str | os.PathLike[str]) -> str | None:
    """Copy *source* to *dest* by an atomic rename and return the digest of the bytes
    copied, or ``None`` when nothing was copied.

    The bytes are read once, so the digest is of exactly what *dest* received: the
    write-back guard later compares the seat's file against it.
    """
    dest = Path(dest)
    partial = dest.with_name(f"{dest.name}.partial")
    try:
        data = Path(source).read_bytes()
        partial.write_bytes(data)
        os.replace(partial, dest)
    except OSError:
        with contextlib.suppress(OSError):
            partial.unlink()
        return None
    return hashlib.sha256(data).hexdigest()


# What a write-back can come to. Only "written" changes the seat's file.
WRITTEN = "written"
SEAT_CHANGED = "seat-changed"
NOT_NEWER = "not-newer"
NOTHING_TO_WRITE = "nothing-to-write"
FAILED = "failed"


@dataclasses.dataclass(frozen=True)
class WriteBack:
    """What :func:`write_back_to_seat` did, in words that carry no credential value."""

    outcome: str
    detail: str

    @property
    def written(self) -> bool:
        return self.outcome == WRITTEN

    @property
    def notable(self) -> bool:
        """Worth a line to the operator: the seat was written, or a newer credential was
        left unwritten for a reason other than there being nothing newer."""
        return self.outcome in (WRITTEN, SEAT_CHANGED, FAILED)


def _newer_by_both(copy: CredentialStatus, seat: CredentialStatus) -> bool:
    """The copy is strictly newer than the seat by ``expiresAt`` and by
    ``refreshTokenExpiresAt``. A timestamp absent from both files is not compared; one the
    seat has must be in the copy and later; ``expiresAt`` must be in both."""
    if not (copy.readable and seat.readable):
        return False
    if copy.expires_at_ms is None or seat.expires_at_ms is None:
        return False
    if copy.expires_at_ms <= seat.expires_at_ms:
        return False
    if seat.refresh_expires_at_ms is None:
        return True
    return (
        copy.refresh_expires_at_ms is not None
        and copy.refresh_expires_at_ms > seat.refresh_expires_at_ms
    )


def write_back_to_seat(
    copy: str | os.PathLike[str],
    seat: str | os.PathLike[str],
    copied_digest: str | None,
) -> WriteBack:
    """Write the credential in *copy* back to the seat's file *seat* (T53b).

    It writes only when all of these hold, and otherwise leaves the seat's file as it is:

    * something was copied from the seat (*copied_digest* is the digest
      :func:`copy_credential` returned for it);
    * the seat's file is still byte-identical to what was copied, so no other session
      refreshed it or logged in meanwhile;
    * the copy is newer than the seat by both expiry timestamps (:func:`_newer_by_both`).

    The write replaces the seat's ``claudeAiOauth`` block with the copy's and keeps every
    other key of the seat's file as the seat has it. The new file is written in full to a
    temporary file in the seat's directory and moved over the seat's file in one
    :func:`os.replace`, so the seat's file is either the old one or the new one, never a
    part of either. The two files are parsed for the merge and nothing parsed leaves this
    function: the result names an outcome, never a value (ADR-0004, 2026-10-24 amendment).
    """
    copy, seat = Path(copy), Path(seat)
    if copied_digest is None or not copy.is_file():
        return WriteBack(NOTHING_TO_WRITE, "no spawn copied the seat's credential")
    if file_digest(seat) != copied_digest:
        return WriteBack(
            SEAT_CHANGED,
            "the seat's credential file changed while the run went on (another claude "
            "session refreshed it or logged in again), so the run's credential was not "
            "written back; the seat's file was left as it is",
        )
    if not _newer_by_both(read_credential_status(copy), read_credential_status(seat)):
        return WriteBack(
            NOT_NEWER,
            f"the run's credential is not newer than the seat's by both {_CRED_EXPIRES_AT} "
            f"and {_CRED_REFRESH_EXPIRES_AT}; the seat's file was left as it is",
        )
    try:
        seat_data = json.loads(seat.read_text(encoding="utf-8"))
        copy_data = json.loads(copy.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return WriteBack(FAILED, f"could not read the credential files ({type(exc).__name__})")
    block = copy_data.get(_CRED_BLOCK) if isinstance(copy_data, dict) else None
    if not isinstance(seat_data, dict) or not isinstance(block, dict):
        return WriteBack(FAILED, f"a credential file has no {_CRED_BLOCK} block to write")
    merged = {**seat_data, _CRED_BLOCK: block}
    fd, partial = tempfile.mkstemp(prefix=f"{CREDENTIAL_FILE}.", suffix=".tmp", dir=seat.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(merged, handle)
            handle.flush()
            os.fsync(handle.fileno())
        with contextlib.suppress(OSError):
            shutil.copymode(seat, partial)
        # The narrowest window the guard can leave: the seat's file is compared once more
        # just before the rename.
        if file_digest(seat) != copied_digest:
            Path(partial).unlink()
            return WriteBack(
                SEAT_CHANGED,
                "the seat's credential file changed while the write-back was being prepared; "
                "the seat's file was left as it is",
            )
        os.replace(partial, seat)
    except OSError as exc:
        with contextlib.suppress(OSError):
            Path(partial).unlink()
        return WriteBack(
            FAILED,
            f"could not replace the seat's credential file ({type(exc).__name__}); "
            "the seat's file was left as it is",
        )
    return WriteBack(
        WRITTEN,
        "the run's newer credential was written back to the seat's credential file",
    )
