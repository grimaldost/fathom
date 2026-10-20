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
"""

from __future__ import annotations

import contextlib
import dataclasses
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
    (ADR-0004). It never writes the seat's file: the seat keeps the credential it had, and
    a refresh made inside the run stays with the run. Nothing is copied until the first
    :meth:`seed_dir`, so a run that plans no spawn reads nothing. :meth:`close` removes the
    copy; use the store as a context manager.
    """

    def __init__(self, real_config: str | os.PathLike[str] | None = None) -> None:
        self._real = Path(real_config) if real_config else Path.home() / ".claude"
        self._dir: Path | None = None
        self._lock = threading.Lock()

    def seed_dir(self) -> str:
        """The directory holding the newest credential, created on first use."""
        with self._lock:
            if self._dir is None:
                self._dir = Path(tempfile.mkdtemp(prefix="fathom_cred_"))
            self._take_if_newer(self._real / CREDENTIAL_FILE)
            return str(self._dir)

    def absorb(self, config_dir: str | os.PathLike[str]) -> bool:
        """Keep the credential a spawn left in *config_dir* if it is newer. True if kept."""
        with self._lock:
            if self._dir is None:
                return False
            return self._take_if_newer(Path(config_dir) / CREDENTIAL_FILE)

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

    def _take_if_newer(self, source: Path) -> bool:
        """Replace the carried file with *source* when *source* is newer (lock held).

        The first file taken is taken as it is, readable or not, which is what a spawn got
        before the store existed. After that, only a readable, strictly newer file
        replaces it, by an atomic rename, so a half-written file is never carried.
        """
        if self._dir is None or not source.is_file():
            return False
        held = self._dir / CREDENTIAL_FILE
        if held.is_file():
            incoming = _life(read_credential_status(source))
            current = _life(read_credential_status(held))
            if incoming is None or (current is not None and incoming <= current):
                return False
        partial = self._dir / f"{CREDENTIAL_FILE}.partial"
        try:
            shutil.copy2(source, partial)
            os.replace(partial, held)
        except OSError:
            with contextlib.suppress(OSError):
                partial.unlink()
            return False
        return True
