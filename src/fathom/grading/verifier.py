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

# Root-level names excluded from the scored result view.
# These are engine output paths and stray input assets that fingerprint the scenario.
_EXCLUDED_ROOT_NAMES: frozenset[str] = frozenset(
    [
        "tracker.jsonl",  # engine run tracker
        "outputs",  # engine outputs directory
        "logs",  # engine log directory
        "series.toml",  # stray series config (should be outside workspace per §6)
        "prompts",  # stray prompt files directory (should be outside workspace per §6)
    ]
)

# Process-scaffolding dir names excluded from the scored result view.
# Plugins like humblepowers write these during execution; stripping them prevents
# a judge from inferring which arm ran (ADR-0003 blindness hardening, §10).
# Applied at EVERY tree level (root and nested, e.g. docs/plans/).
_SCAFFOLDING_DIR_NAMES: frozenset[str] = frozenset(
    [
        ".remember",  # humblepowers memory / recall system
        "plans",  # humblepowers planned-execution (root and docs/plans/)
        "journal",  # session journaling dirs
        ".envmem",  # an arm's env-memory store (per-arm ENVMEMORY__DIR) — fingerprints the arm
        ".seeded-store",  # seeded env-memory store (a warm-store arm) — fingerprints the arm
        ".empty-store",  # empty env-memory store (control arms)
    ]
)

# Marker string a series engine may append to .gitignore.
# A .gitignore containing this string is an automation artifact and is excluded.
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


def _is_gitignore_automation_artifact(path: Path) -> bool:
    """Return True if this .gitignore was modified by a series engine."""
    try:
        return _AUTO_GITIGNORE_MARKER in path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return False


def extract_result_view(workspace: Path, dest: Path) -> None:
    """Copy the working tree from *workspace* into *dest*, excluding engine artifacts.

    Only root-level exclusions apply (listed in _EXCLUDED_ROOT_NAMES).  The .git
    directory is always skipped.  The .gitignore is excluded when it contains the
    automation marker written by a series engine.

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
        if name == ".gitignore" and item.is_file() and _is_gitignore_automation_artifact(item):
            continue
        dst = dest / name
        if item.is_dir():
            shutil.copytree(item, dst, ignore=_scaffolding_ignore)
        else:
            shutil.copy2(item, dst)


def _build_minimal_env() -> dict[str, str]:
    """Return an explicit env containing only system-level vars.

    Constructed from the calling process's environment but limited to the
    whitelist in _SYSTEM_ENV_KEYS, so no application-specific or
    scenario-identifying variables are forwarded.
    """
    return {k: v for k, v in os.environ.items() if k in _SYSTEM_ENV_KEYS}


def run_verifier(verify_entry: Path, workspace: Path, timeout_s: int = 60) -> VerifierResult:
    """Extract the result view from *workspace*, invoke *verify_entry*, return the outcome.

    The result view is a temporary copy of the workspace with engine artifacts
    excluded.  It is removed after the verifier exits.

    *verify_entry* receives the result view path as its sole argument.  The
    subprocess environment is built minimal-explicit: no scenario identity in
    argv or env (ADR-0003).

    *timeout_s* bounds the verifier subprocess (default 60). A bank may raise it
    per task via ``[verify] timeout_s`` for verifiers that shell out to a heavier
    harness — e.g. one that runs a third-party venv's pytest whose import+collect
    alone exceeds the default 60s.

    Outcome rules:
    - exit 0  + valid JSON dict  → "pass"
    - exit ≠0 + valid JSON dict  → "fail"
    - crash or non-JSON stdout   → "error"
    """
    tmp = tempfile.mkdtemp(prefix="fathom-result-view-")
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

        try:
            criteria = json.loads(stdout.strip())
        except (json.JSONDecodeError, ValueError):
            return VerifierResult(
                outcome="error",
                criteria=None,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
            )

        if not isinstance(criteria, dict):
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
