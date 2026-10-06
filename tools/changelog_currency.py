#!/usr/bin/env python
"""Fail a PR that changes the harness while CHANGELOG.md stays untouched.

The rule is "record the change or declare why not", and it is a gate rather than prose
because a rule kept only in prose is the one skipped when a release is assembled in a
hurry: a substantive change that never reaches the changelog is invisible to everyone who
installs the release.

Reads a changed-file list (arguments, else stdin, one path per line) and exits 1 when it
touches a harness path — ``src/``, ``pyproject.toml``, ``.claude-plugin/``, ``commands/``,
``mcp/``, ``skills/``, ``tools/`` — while ``CHANGELOG.md`` is untouched and no commit
message in the range declares the exemption.  The declaration is a line starting
``Changelog: not needed (<reason>)`` (``none`` also reads); pass the range's messages with
``--messages FILE``.

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

# Every top-level entry of this repository is in exactly one class below, or is the record
# itself; tests/test_changelog_currency.py holds the classes to the tree, both ways.
#
# What a change to the harness looks like in a diff. A data root installs this repository
# at a tag, so anything that reaches an installed copy counts: the package (src/, including
# its package data) and its metadata (pyproject.toml), and the plugin surface (.claude-plugin/,
# commands/, mcp/, skills/ — SKILL.md is agent-facing behaviour). The repository's own
# tooling (tools/) counts too, since the gates and hooks run from it.
HARNESS_PREFIXES = ("src/", ".claude-plugin/", "commands/", "mcp/", "skills/", "tools/")
HARNESS_FILES = frozenset({"pyproject.toml"})
RECORD = "CHANGELOG.md"

# Exempt: docs/ and tests/ (fixtures included) are records and checks; assets/ and the
# top-level prose are presentation; .github/ and the hook, ignore and attribute files are
# repository configuration; and uv.lock pins development tools only — the package declares
# no runtime dependencies, so a lock change never reaches a consumer. The gate reads only
# the harness class; this one is named so that the tree has no unclassified entry.
EXEMPT_PREFIXES = ("docs/", "examples/", "tests/", "assets/", ".github/")
EXEMPT_FILES = frozenset(
    {
        "README.md",
        "README-plugin.md",
        "CONTRIBUTING.md",
        "CLAUDE.md",
        "LICENSE",
        "uv.lock",
        ".pre-commit-config.yaml",
        ".gitignore",
        ".gitattributes",
    }
)

# A declaration is a commit-message line, so it survives in history next to the change it
# excuses — a PR description does not.
DECLARATION = re.compile(r"^changelog:\s*(?:none|not needed)\b", re.IGNORECASE | re.MULTILINE)


def is_harness(path: str) -> bool:
    """Whether *path* (forward slashes, relative to the repository root) is a harness path."""
    return path in HARNESS_FILES or path.startswith(HARNESS_PREFIXES)


def unrecorded_harness_paths(changed: Iterable[str]) -> list[str]:
    """The harness paths in *changed* that no CHANGELOG edit accompanies ([] when fine)."""
    paths = [path.strip().replace("\\", "/") for path in changed if path.strip()]
    if RECORD in paths:
        return []
    return [path for path in paths if is_harness(path)]


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
        "with a `Changelog: not needed (<reason>)` line in a commit message."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
