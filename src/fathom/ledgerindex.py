"""Rendering the ledger index — the committed stamp every verdict is read against.

The logic lives here, under ``src/fathom/``, because :mod:`fathom.reconcile` needs it and an
installed engine carries only the package.  It runs against a data root, found the way every
fathom command finds one (:mod:`fathom.home`)::

    fathom index                            # check: exit 1 when the index is stale
    fathom index --write                    # re-render docs/reports/LEDGER-INDEX.md
    python -m fathom.ledgerindex [--write]  # the same, where the package is importable

Both refuse, with exit 2, when what they would check is neither a data root nor an engine
checkout: checking there would pass for want of ledgers, and writing there would leave a
stray index.  ``--write`` also refuses an engine checkout, which holds no ledgers to stamp.
``tools/ledger_index.py`` in an engine checkout is a thin shim over this module.

How a root is recognised (:func:`root_kind`, :func:`check_root`) lives here too, because
:mod:`fathom.reconcile` imports this module and both entry points must agree on it.

Why it exists: a verdict can be written up and still have been read against a ledger that
has since moved.  When a report quotes counts from a snapshot and a later trial is appended
to the same ledger, documents written at different moments quote different sample sizes
and statistics, none of them the committed state, and nothing flags the disagreement.

This module renders one row per committed ledger: the file's sha256 over canonical bytes,
the per-scenario count of ``status == "completed"`` trials, and the raw row counts.  The
rendered file is committed and the reconciliation regenerates it and compares byte-for-byte,
so any append to any ledger turns the gate red until it is re-rendered — and the re-render
diff names exactly which arms moved, which is the moment to re-read the documents quoting
them.

What this does NOT do, stated plainly: it does not parse prose.  A report that quotes a
wrong number is still a wrong number; what the index buys is that the right number is
committed, dated by hash, and adjacent, so the contradiction is mechanical to find instead
of requiring someone to re-derive it from the JSONL.

Stdlib only.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path

from fathom import home

# Both relative to the data root. As defaults they resolve against the working directory
# at the moment they are used, never against where the package is installed.
LEDGER_DIR = Path("ledger")
INDEX_PATH = Path("docs") / "reports" / "LEDGER-INDEX.md"

# The two markers a root is recognised by, relative to it. How fathom.toml is read is
# defined once, in fathom.home, which the plugin's MCP server loads too.
CONFIG_FILE = home.CONFIG_FILE
PLUGIN_MANIFEST = Path(".claude-plugin") / "plugin.json"
ConfigError = home.ConfigError
read_config = home.read_config

EXIT_OK = 0
EXIT_STALE = 1
EXIT_NOT_A_ROOT = 2

HEADER = """# Ledger index — the stamp every verdict is read against

**Generated. Do not hand-edit.** Re-render with `python -m fathom.ledgerindex --write` from
the data root; `fathom reconcile` fails while this file and `ledger/` disagree.

One row per committed ledger (archived ledgers under `ledger/archive/` are excluded).
`n by arm` counts trial rows with `status == "completed"` only — the same rule the resume
key and every scorecard use, so an errored trial is never a measured failure. A document
that quotes a per-arm n, a pooled control total or a p-value for one of these banks is
quoting *this* row; if it disagrees, the document is stale.

| Bank | ledger sha256 | n by arm (completed) | trial rows | run rows |
|---|---|---|---|---|
"""


def ledger_files(ledger_dir: Path) -> list[Path]:
    """Committed ledgers, top level only — ``ledger/archive/`` is deliberately excluded."""
    if not ledger_dir.is_dir():
        return []
    return sorted(ledger_dir.glob("*.jsonl"))


def rows(path: Path) -> list[dict]:
    """Every JSON object in a ledger, skipping blank and malformed lines."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def canonical_bytes(path: Path) -> bytes:
    """The ledger as git stores it: LF line endings, whatever the checkout has.

    ``ledger.py`` appends with LF line endings on every platform, and a data root's
    ``.gitattributes`` pins ``*.jsonl text eol=lf``, so the committed bytes are LF.  The
    working tree need not be: a checkout with ``core.autocrlf`` or an editor can leave CRLF,
    and git normalises it away again on check-in.  Hashing the raw file once stamped the
    checkout's platform rather than the ledger, and the freshness gate failed on Windows
    against an index stamped on LF — with a message accusing an operator of appending to a
    ledger that had not moved.  Normalising here makes the digest equal to the one over the
    committed blob, on every platform.
    """
    return path.read_bytes().replace(b"\r\n", b"\n")


def summarise(path: Path) -> dict:
    """One index row's facts for a single ledger."""
    parsed = rows(path)
    from fathom.ledger import apply_voids as _apply_voids

    parsed = _apply_voids(parsed)
    trials = [r for r in parsed if r.get("kind") == "trial"]
    runs = [r for r in parsed if r.get("kind") == "run"]
    completed: collections.Counter[str] = collections.Counter(
        str(r.get("scenario") or "(unnamed)") for r in trials if r.get("status") == "completed"
    )
    return {
        "bank": path.stem,
        "sha256": hashlib.sha256(canonical_bytes(path)).hexdigest(),
        "completed": dict(sorted(completed.items())),
        "trial_rows": len(trials),
        "run_rows": len(runs),
    }


def render(ledger_dir: Path = LEDGER_DIR) -> str:
    """The whole index document, as it should be committed."""
    lines = [HEADER.rstrip("\n")]
    for path in ledger_files(ledger_dir):
        s = summarise(path)
        by_arm = (
            ", ".join(f"{arm}:{n}" for arm, n in s["completed"].items()) or "— (none completed)"
        )
        lines.append(
            f"| `{s['bank']}` | `{s['sha256']}` | {by_arm} | {s['trial_rows']} | {s['run_rows']} |"
        )
    lines.append("")
    return "\n".join(lines)


# A table row as render() writes it: bank and digest are the first two cells, in backticks.
_STAMP_ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|")

_RERENDER = "`fathom index --write` (or `python -m fathom.ledgerindex --write`) from the data root"


def stamps(document: str) -> dict[str, str]:
    """``{bank: ledger sha256}`` as an index document states them, one per table row."""
    found: dict[str, str] = {}
    for line in document.splitlines():
        match = _STAMP_ROW.match(line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


@dataclasses.dataclass(frozen=True)
class Staleness:
    """Why a root's committed index is not a fresh render of its ledgers.

    ``kind`` is one of:

    - ``"unrendered"``: ledgers exist and no index does;
    - ``"ledgers"``: a ledger's sha256 differs from its row, or a ledger has no row, or a
      row has no ledger — ``changes`` names each one;
    - ``"rendering"``: every row's sha256 matches its ledger, so no ledger moved.  The
      document differs only in how this engine version renders it: the header text, or the
      row format or counting.  An engine release that rewords the header lands here.
    """

    kind: str
    changes: tuple[str, ...] = ()

    @property
    def detail(self) -> str:
        if self.kind == "unrendered":
            return (
                f"ledger/ holds ledgers but no index has been rendered. Render it with "
                f"{_RERENDER} and commit it with the ledgers."
            )
        if self.kind == "ledgers":
            return (
                f"the committed index disagrees with a fresh render of ledger/: "
                f"{'; '.join(self.changes)}. Re-render with {_RERENDER}, read the diff — it "
                "names the arms whose n moved — and update every document quoting those "
                "counts, pooled control totals or p-values before committing."
            )
        return (
            "every ledger's sha256 matches its row in the committed index, so no ledger "
            "moved; the index differs only in how this engine version renders it (the header "
            f"text, or the row format or counting). Re-render with {_RERENDER} and commit the "
            "result. If the re-render moves any n by arm, the engine's counting changed: "
            "re-read the documents quoting those counts."
        )


def staleness(root: Path) -> Staleness | None:
    """Why *root*'s committed index is stale, or ``None`` when it equals a fresh render.

    A root with no ledgers and no index is current: there is nothing to stamp, which is the
    state of an engine checkout or of a data root before its first paid trial.

    The comparison is of the whole document, byte for byte; the per-ledger digests are read
    back only to say which kind of difference it is.  Without that, a header reworded by an
    engine release was reported as an append to a ledger that had not moved.
    """
    ledger_dir = root / LEDGER_DIR
    index = root / INDEX_PATH
    if not index.is_file():
        return Staleness("unrendered") if ledger_files(ledger_dir) else None
    committed = index.read_text(encoding="utf-8")
    fresh = render(ledger_dir)
    if committed == fresh:
        return None
    before, after = stamps(committed), stamps(fresh)
    changes: list[str] = []
    for bank in sorted(before.keys() | after.keys()):
        if bank not in before:
            changes.append(f"`{bank}` has no row in the index")
        elif bank not in after:
            changes.append(f"`{bank}` has a row but no ledger")
        elif before[bank] != after[bank]:
            changes.append(f"`{bank}` changed since the index was stamped")
    if changes:
        return Staleness("ledgers", tuple(changes))
    return Staleness("rendering")


def is_current(root: Path) -> bool:
    """Whether *root*'s committed index equals a fresh render of its ledgers."""
    return staleness(root) is None


def write(root: Path) -> Path:
    """Render *root*'s ledgers into its index file, LF line endings; returns the path."""
    index = root / INDEX_PATH
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(render(root / LEDGER_DIR), encoding="utf-8", newline="\n")
    return index


# ---------------------------------------------------------------------------
# Roots
# ---------------------------------------------------------------------------


def is_data_root(root: Path) -> bool:
    """Whether *root* carries the data-root marker: a ``fathom.toml`` with ``[data_root]``
    of a schema this fathom reads.

    A ``fathom.toml`` that cannot be read, or that declares another schema, is not a
    marker here; :func:`fathom.home.has_marker` says why.
    """
    try:
        return home.has_marker(root)
    except ConfigError:
        return False


def is_engine_checkout(root: Path) -> bool:
    """Whether *root* is a fathom engine checkout that carries its plugin manifest.

    The engine is recognised as :func:`fathom.home.looks_like_engine_checkout` recognises
    it (``src/fathom/`` beside a ``pyproject.toml`` naming the ``fathom`` project), so that
    every command agrees on what one is; the manifest is required too, because it is one
    of the version sites ``fathom reconcile`` checks there. Another plugin's repository has
    a manifest and is not an engine checkout.
    """
    return home.looks_like_engine_checkout(root) and (Path(root) / PLUGIN_MANIFEST).is_file()


def root_kind(root: Path) -> str | None:
    """``"data root"``, ``"engine checkout"``, or ``None`` when *root* is neither.

    A directory that is neither has no ledgers to check, so every check of it would pass.
    The command-line entry points refuse such a directory rather than report that vacuous
    pass — it is what running from the wrong directory looks like.
    """
    if is_data_root(root):
        return "data root"
    if is_engine_checkout(root):
        return "engine checkout"
    return None


def not_a_root_message(root: Path, command: str, *, pointer: str = "--home DIR") -> str:
    """The refusal both entry points print for a directory that is neither kind of root."""
    return (
        f"{root} is neither a fathom data root (a {CONFIG_FILE} with a [data_root] table) "
        "nor a fathom engine checkout, so there is nothing here to check. Run "
        f"`{command}` inside a data root, or point at one with {pointer} or the FATHOM_HOME "
        "environment variable; `fathom init DIR` creates one"
    )


class RootError(ValueError):
    """What a check would run against is neither a data root nor an engine checkout."""


@dataclasses.dataclass(frozen=True)
class CheckRoot:
    """The root a check runs against, its kind, and an optional note for stderr."""

    path: Path
    kind: str
    note: str | None = None


def check_root(
    explicit: str | os.PathLike[str] | None = None,
    *,
    command: str,
    pointer: str = "--home DIR",
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
) -> CheckRoot:
    """The root ``fathom reconcile`` and the index check run against.

    A data root is found as every command finds one (:func:`fathom.home.resolve`), with
    *explicit* in the place of ``--home``, except that it must carry the marker: an
    unmarked directory has no ``[[reconcile.known]]`` to read and no claim to be checked.
    An engine checkout is a root too, for its version sites; it is used when it is named
    explicitly, or when it is the working directory and no data root was named or found.

    Raises :class:`RootError` with the message to print.
    """
    here = Path(os.path.abspath(Path.cwd() if cwd is None else cwd))
    if explicit is not None:
        named = str(explicit).strip()
        if not named:
            option = pointer.split()[0]
            raise RootError(
                f"{option} was given an empty value. Name the root with {pointer}, or leave "
                f"{option} out to use FATHOM_HOME or the data root around the working directory"
            )
        root = Path(os.path.abspath(here / Path(named).expanduser()))
        try:
            # Raises for an unreadable fathom.toml, and for a marker of another schema.
            home.has_marker(root)
        except ConfigError as exc:
            raise RootError(str(exc)) from exc
        kind = root_kind(root)
        if kind is None:
            raise RootError(not_a_root_message(root, command, pointer=pointer))
        return CheckRoot(root, kind)
    try:
        found = home.resolve(None, env=env, cwd=here)
    except home.DataRootError as exc:
        if exc.found_nothing and root_kind(here) == "engine checkout":
            return CheckRoot(here, "engine checkout")
        if exc.found_nothing:
            raise RootError(not_a_root_message(here, command, pointer=pointer)) from exc
        raise RootError(str(exc)) from exc
    if not found.marked:
        raise RootError(
            f"{not_a_root_message(found.path, command, pointer=pointer)}. "
            f"{home.unmarked_reason(found.path)} {home.how_to_mark(found.path)}"
        )
    note = None
    if found.origin == home.ENV_VAR and root_kind(here) == "engine checkout":
        note = (
            f"note: the working directory is a fathom engine checkout, and FATHOM_HOME "
            f"selects the data root at {found.path}; unset FATHOM_HOME to check the engine's "
            "own version sites."
        )
    return CheckRoot(found.path, "data root", note)


def run_index(
    explicit: str | os.PathLike[str] | None = None,
    *,
    write_index: bool = False,
    command: str,
    pointer: str = "--home DIR",
) -> int:
    """Check (default) or re-render the index of the root :func:`check_root` finds."""
    try:
        target = check_root(explicit, command=command, pointer=pointer)
    except RootError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_NOT_A_ROOT
    if target.note:
        print(target.note, file=sys.stderr)
    if write_index:
        if target.kind != "data root":
            print(
                f"error: {target.path} is a fathom engine checkout, which holds no ledgers, so "
                f"there is no index to write there. Run `{command} --write` inside a data root, "
                f"or point at one with {pointer} or the FATHOM_HOME environment variable",
                file=sys.stderr,
            )
            return EXIT_NOT_A_ROOT
        print(f"wrote {write(target.path)}")
        return EXIT_OK
    stale = staleness(target.path)
    if stale is None:
        print(f"ledger index is current ({target.kind} at {target.path})")
        return EXIT_OK
    print(f"ledger index is STALE: {stale.detail}", file=sys.stderr)
    return EXIT_STALE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m fathom.ledgerindex",
        description=(
            "Check (default) or re-render (--write) the ledger index of a data root. "
            "Exit 1 when the committed index is stale, 2 when there is neither a data root "
            "nor an engine checkout to check."
        ),
    )
    parser.add_argument("--write", action="store_true", help="rewrite the committed index")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "the data root (default: found as every fathom command finds it — FATHOM_HOME, "
            "else the nearest marked directory at or above the working directory)"
        ),
    )
    args = parser.parse_args(argv)
    return run_index(args.root, write_index=args.write, command=parser.prog, pointer="--root DIR")


if __name__ == "__main__":
    raise SystemExit(main())
