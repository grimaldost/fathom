"""The backlog says "Unreleased" only while the changelog has an [Unreleased] entry to back it.

A release cut moves every [Unreleased] entry under its version heading. Backlog rows closed
by that release said "Unreleased" too, and nothing moved them: after 0.9.0 shipped, seven
Closed-ids rows and one open row still said "Unreleased". Once the cut has emptied
[Unreleased], any backlog line that still says it names a release that already happened.

Stdlib-only; runs without uv as ``python tests/test_backlog_versions.py``.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def unreleased_entries(changelog: str) -> str:
    """The text of the changelog's ``[Unreleased]`` section, stripped ("" when empty)."""
    match = re.search(r"^## \[Unreleased\][^\n]*\n(.*?)(?=^## \[|\Z)", changelog, re.M | re.S)
    return match.group(1).strip() if match else ""


def unreleased_mentions(backlog: str) -> list[str]:
    """The backlog lines that say a change is in "Unreleased"."""
    return [line.strip() for line in backlog.splitlines() if "Unreleased" in line]


def stale_mentions(changelog: str, backlog: str) -> list[str]:
    """Backlog lines saying "Unreleased" after a cut emptied the changelog's section."""
    return [] if unreleased_entries(changelog) else unreleased_mentions(backlog)


class BacklogVersionTests(unittest.TestCase):
    def test_the_repository_backlog_names_no_release_that_already_happened(self) -> None:
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        backlog = (REPO / "docs" / "backlog.md").read_text(encoding="utf-8")
        self.assertEqual(
            stale_mentions(changelog, backlog),
            [],
            "CHANGELOG [Unreleased] is empty, so these backlog lines name a release that "
            "already shipped: set each to the version that closed it",
        )

    def test_a_row_left_at_unreleased_after_the_cut_is_named(self) -> None:
        cut = "# Changelog\n\n## [Unreleased]\n\n## [0.9.0] - 2026-10-07\n\n- Shipped.\n"
        backlog = "| FATH-B01 | Built. | 0.8.0 |\n| FATH-B02 | Built. | Unreleased |\n"
        self.assertEqual(stale_mentions(cut, backlog), ["| FATH-B02 | Built. | Unreleased |"])

    def test_unreleased_rows_stand_while_the_changelog_has_unreleased_entries(self) -> None:
        pending = "# Changelog\n\n## [Unreleased]\n\n- Pending.\n\n## [0.9.0] - 2026-10-07\n"
        backlog = "| FATH-B02 | Built. | Unreleased |\n"
        self.assertEqual(stale_mentions(pending, backlog), [])


if __name__ == "__main__":
    unittest.main()
