#!/usr/bin/env python
"""Fail a PR that changes the harness while CHANGELOG.md stays untouched.

Ported from keel's changelog-currency gate, which is the one place in this repo's estate
where "record the change or declare why not" is mechanical rather than prose.  The 0.4.0
cut is the local demonstration that prose does not hold: two of the day's substantive
commits never reached the changelog, on the very day the release was assembled by hand.

Reads a changed-file list (arguments, else stdin, one path per line) and exits 1 when it
touches a harness path — ``src/``, ``tools/``, ``commands/``, ``mcp/``, ``skills/`` — while
``CHANGELOG.md`` is untouched and no commit message in the range declares the exemption.
The declaration is a line starting ``Changelog: not needed (<reason>)`` (``none`` also
reads); pass the range's messages with ``--messages FILE``.

Version-site agreement is deliberately not this tool's job: that is the ``version-sites``
reconciliation (``fathom reconcile``), which the suite runs on every CI leg.  Repo-local
tooling; stdlib only, runs without uv:

    git diff --name-only "origin/$BASE...HEAD" | python tools/changelog_currency.py
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path

# What a change to the harness looks like in a diff: the engine, the repo tooling, and the
# plugin command/MCP/skill surfaces (SKILL.md is agent-facing behaviour, and historically its
# edits only ever escaped this rule by riding commits that also touched src/ or commands/).
# Docs, ledgers, scenarios and banks are records or data — a ledger append is gated by the
# ledger-index reconciliation, not by prose currency.
HARNESS_PREFIXES = ("src/", "tools/", "commands/", "mcp/", "skills/")
RECORD = "CHANGELOG.md"

# A declaration is a commit-message line, so it survives in history next to the change it
# excuses — a PR description does not.
DECLARATION = re.compile(r"^changelog:\s*(?:none|not needed)\b", re.IGNORECASE | re.MULTILINE)


def unrecorded_harness_paths(changed: Iterable[str]) -> list[str]:
    """The harness paths in *changed* that no CHANGELOG edit accompanies ([] when fine)."""
    paths = [path.strip().replace("\\", "/") for path in changed if path.strip()]
    if RECORD in paths:
        return []
    return [path for path in paths if path.startswith(HARNESS_PREFIXES)]


def declared(messages: str) -> bool:
    """Whether any commit message in the range declares the change changelog-exempt."""
    return bool(DECLARATION.search(messages))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", help="changed paths (else read from stdin)")
    parser.add_argument(
        "--messages",
        type=Path,
        default=None,
        help="file holding the range's commit messages, checked for a declaration line",
    )
    args = parser.parse_args(argv)

    changed = args.paths or sys.stdin.read().splitlines()
    unrecorded = unrecorded_harness_paths(changed)
    if not unrecorded:
        print("OK: no harness change, or the CHANGELOG records it.")
        return 0
    if args.messages is not None and declared(args.messages.read_text(encoding="utf-8")):
        print("OK: a commit in the range declares `Changelog: not needed (<reason>)`.")
        return 0
    print("Harness paths changed with no CHANGELOG.md entry:")
    for path in unrecorded:
        print(f"  {path}")
    print(
        "Record the change under [Unreleased] in CHANGELOG.md, or declare the exemption "
        "with a `Changelog: not needed (<reason>)` line in a commit message. An unrecorded "
        "change is what the 0.4.0 cut shipped twice."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
