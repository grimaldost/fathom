"""Verifier execution: extract the scored result view and run verify.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fathom.adapters.claude_cli import withhold_hidden_dirs

# Root-level names excluded from the scored result view.
# These are engine output paths and stray input assets that fingerprint the scenario.
_EXCLUDED_ROOT_NAMES: frozenset[str] = frozenset(
    [
        "tracker.jsonl",  # engine run tracker
        "outputs",  # engine outputs directory
        "logs",  # engine log directory
        "series.toml",  # stray series config (belongs outside the workspace, spec §6)
        "prompts",  # stray prompt files directory (belongs outside the workspace, spec §6)
    ]
)

# Process-scaffolding dir names excluded from the scored result view.
# An arm's plugins or hooks may write these during execution: working notes rather
# than deliverables, and their presence alone tells which arm ran. Stripping them keeps
# a verifier or judge from inferring the arm (ADR-0003 blindness).
# Applied at EVERY tree level (root and nested, e.g. docs/plans/).
_SCAFFOLDING_DIR_NAMES: frozenset[str] = frozenset(
    [
        ".remember",  # an agent memory / recall store
        "plans",  # planning documents (root and docs/plans/)
        "journal",  # session journal notes
    ]
)

# Marker line that starts the block a series engine may append to the root .gitignore.
# The result view cuts the block and keeps the rest (see _gitignore_for_view).
_AUTO_GITIGNORE_MARKER = "# PR automation"

# System-level env vars forwarded to the verifier subprocess.
# This set is explicit (not wholesale-inherited) so no scenario metadata leaks through.
_SYSTEM_ENV_KEYS: frozenset[str] = frozenset(
    [
        # Cross-platform
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TMPDIR",
        # Windows
        "PATHEXT",
        "SYSTEMROOT",
        "SYSTEMDRIVE",
        "WINDIR",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "TEMP",
        "TMP",
        "COMSPEC",
        "PROGRAMFILES",
        "PROGRAMDATA",
        "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE",
        "OS",
        # Python UTF-8 mode — forwarded so verify.py encodes stdout as UTF-8
        "PYTHONUTF8",
    ]
)


@dataclass
class VerifierResult:
    outcome: str  # "pass" | "fail" | "error"
    criteria: dict[str, Any] | None  # None when outcome is "error"
    stdout: str
    stderr: str
    exit_code: int | None  # None if the subprocess could not be launched


def _scaffolding_ignore(src: str, names: list[str]) -> set[str]:
    """shutil.copytree ignore callback: drop scaffolding dirs at every tree level."""
    return {n for n in names if n in _SCAFFOLDING_DIR_NAMES}


def _gitignore_for_view(raw: bytes) -> bytes | None:
    """The root ``.gitignore`` as the result view holds it, the same in every arm.

    A series engine appends a block that starts at :data:`_AUTO_GITIGNORE_MARKER` to a
    fixture's ``.gitignore``, or creates the file when the fixture has none. Dropping
    the whole file then told a series trial apart by the file's absence, so the block
    is cut instead (from the marker on) and the fixture's lines stay. Engines differ in
    how they join the block on (a blank line before it, a line break added to a last
    line that had none, or none at all), so in every arm the file ends at its last
    non-blank line and with one line break. A file left with no lines is dropped: the
    engine created it. Bytes that are not UTF-8 are copied as they are.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw
    marker_at = text.find(_AUTO_GITIGNORE_MARKER)
    if marker_at >= 0:
        text = text[:marker_at]
    lines = text.splitlines(keepends=True)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None
    if not lines[-1].endswith(("\n", "\r")):
        lines[-1] += "\r\n" if "\r\n" in text else "\n"
    return "".join(lines).encode("utf-8")


def extract_result_view(workspace: Path, dest: Path) -> None:
    """Copy the working tree from *workspace* into *dest*, excluding engine artifacts.

    Only root-level exclusions apply (listed in _EXCLUDED_ROOT_NAMES).  The .git
    directory is always skipped.  The root .gitignore loses the block a series engine
    appends to it, and is left out when nothing else is in it (:func:`_gitignore_for_view`).

    *workspace* is never modified — this is a pure copy operation.
    """
    for item in workspace.iterdir():
        name = item.name
        if name == ".git":
            continue
        if name in _EXCLUDED_ROOT_NAMES:
            continue
        if name in _SCAFFOLDING_DIR_NAMES:
            continue
        dst = dest / name
        if name == ".gitignore" and item.is_file():
            raw = item.read_bytes()
            view = _gitignore_for_view(raw)
            if view is None:
                continue
            if view != raw:
                dst.write_bytes(view)
                continue
        if item.is_dir():
            shutil.copytree(item, dst, ignore=_scaffolding_ignore)
        else:
            shutil.copy2(item, dst)


def _build_minimal_env() -> dict[str, str]:
    """Return an explicit env containing only system-level vars.

    Constructed from the calling process's environment but limited to the
    whitelist in _SYSTEM_ENV_KEYS, so no application-specific or
    scenario-identifying variables are forwarded. Nor does any of them name a withheld
    directory (:func:`~fathom.adapters.claude_cli.withhold_hidden_dirs`): run from a
    virtual environment inside the data root, fathom has that environment's scripts
    directory on PATH, and the verifier, with any agent code it shells out to, inherits
    PATH. PATH keeps its other entries.
    """
    return withhold_hidden_dirs({k: v for k, v in os.environ.items() if k in _SYSTEM_ENV_KEYS})


def extract_criteria(stdout: str) -> dict[str, Any] | None:
    """The criteria dict from a verifier's *stdout*, or None if there is none.

    Tolerant of noise AROUND the JSON, strict about the JSON itself.

    A verifier that checks behaviour-preservation has to import the agent's
    modified package, so whatever that package prints at import time lands on the
    verifier's stdout ahead of its answer.  Requiring the whole of stdout to parse
    therefore threw away trials whose criteria had been computed correctly — and
    threw them away in an ARM-CORRELATED way, since whether the agent adds a print
    is a property of the arm being measured.  That is a silent bias, not just a
    lost trial.

    The rule: scan lines back-to-front and take the LAST line that parses as a JSON
    object.  The criteria line is the last thing a verifier emits, so a debug dict
    printed earlier never wins.  A stdout containing no JSON object is still None —
    the tolerance must not degrade into "find something, anything", or a crashed
    verifier would start scoring.
    """
    if not stdout:
        return None
    # Whole-stdout parse first: the overwhelmingly common case, and it also handles
    # a pretty-printed multi-line object that a line scan would miss.
    try:
        whole = json.loads(stdout.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    else:
        return whole if isinstance(whole, dict) else None

    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict):
            return obj
    return None


def run_verifier(verify_entry: Path, workspace: Path, timeout_s: int = 60) -> VerifierResult:
    """Extract the result view from *workspace*, invoke *verify_entry*, return the outcome.

    The result view is a temporary copy of the workspace with engine artifacts
    excluded.  It is removed after the verifier exits.

    *verify_entry* receives the result view path as its sole argument.  The
    subprocess environment is built minimal-explicit: no scenario identity in
    argv or env (ADR-0003).  Nor in its working directory: fathom works from the
    data root, whose ``.fathom/streams/`` holds files named after the arms, so the
    verifier starts in a fresh, empty directory of its own, removed afterwards with
    the result view.  That removes the accidental route to the streams, a verifier
    that reads or searches its working directory, and not every route: the
    verifier's own path, which its argv carries, lies inside the data root, and a
    verifier that climbs from it can still reach them.

    *timeout_s* bounds the verifier subprocess (default 60). A bank may raise it
    per task via ``[verify] timeout_s`` for verifiers that shell out to a heavier
    harness — e.g. one that runs a third-party venv's pytest whose import+collect
    alone exceeds the default 60s.

    Outcome rules:
    - exit 0  + valid JSON dict  → "pass"
    - exit ≠0 + valid JSON dict  → "fail"
    - crash, or no JSON object anywhere on stdout → "error"
      (noise around the object is tolerated — see :func:`extract_criteria`)
    """
    tmp = tempfile.mkdtemp(prefix="fathom-result-view-")
    cwd = tempfile.mkdtemp(prefix="fathom-verifier-cwd-")
    try:
        result_view = Path(tmp)
        try:
            extract_result_view(workspace, result_view)
        except Exception as exc:
            return VerifierResult(
                outcome="error",
                criteria=None,
                stdout="",
                stderr=str(exc),
                exit_code=None,
            )

        env = _build_minimal_env()
        try:
            proc = subprocess.run(
                [sys.executable, str(verify_entry), str(result_view)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                cwd=cwd,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return VerifierResult(
                outcome="error",
                criteria=None,
                stdout="",
                stderr="verifier timed out",
                exit_code=None,
            )
        except Exception as exc:
            return VerifierResult(
                outcome="error",
                criteria=None,
                stdout="",
                stderr=str(exc),
                exit_code=None,
            )

        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode

        criteria = extract_criteria(stdout)
        if criteria is None:
            return VerifierResult(
                outcome="error",
                criteria=None,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
            )

        outcome = "pass" if exit_code == 0 else "fail"
        return VerifierResult(
            outcome=outcome,
            criteria=criteria,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(cwd, ignore_errors=True)
