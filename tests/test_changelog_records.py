"""Every top-level entry of the tree has a changelog decision, and none is stale.

The changelog gate is railform's (`railform changelog-gate`, run by CI as the `changelog` job).
Which paths it charges is data: the `[changelog] records` rows of `railform.toml`. This test
holds those rows to the tree. A top-level entry is either charged by a row (what reaches an
installed copy, plus the tooling the gates and hooks run from) or named below as exempt, never
both and never neither: a new top-level directory has to be decided, not left unwatched.

Stdlib only; runs without uv as ``python tests/test_changelog_records.py``.
"""

from __future__ import annotations

import subprocess
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

RECORD = "CHANGELOG.md"

# Exempt: docs/ and tests/ (fixtures included) are records and checks; assets/ and the
# top-level prose are presentation; .github/ and the hook, ignore, attribute and frame files
# are repository configuration; and uv.lock pins development tools only, since the package
# declares no runtime dependencies, so a lock change never reaches a consumer.
EXEMPT = frozenset(
    {
        "docs/",
        "examples/",
        "tests/",
        "assets/",
        ".github/",
        "README.md",
        "README-plugin.md",
        "CONTRIBUTING.md",
        "CLAUDE.md",
        "LICENSE",
        "uv.lock",
        ".pre-commit-config.yaml",
        ".gitignore",
        ".gitattributes",
        "railform.toml",
    }
)


def _charged() -> set[str]:
    """The prefixes of the changelog rows that name the changelog itself."""
    frame = tomllib.loads((REPO / "railform.toml").read_text(encoding="utf-8"))
    rows = frame["changelog"]["records"]
    return {row["prefix"] for row in rows if row["file"] == RECORD}


def _top_level() -> set[str] | None:
    """The top-level names this checkout tracks or would track, present on disk.

    ``None`` outside a git checkout (an unpacked sdist, say), where there is no tree to hold
    the rows to. Paths deleted in the working tree but still in the index are left out, so a
    removal in progress is judged by the tree it produces.
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    paths = [line for line in proc.stdout.splitlines() if line and (REPO / line).exists()]
    return {path.split("/", 1)[0] + ("/" if "/" in path else "") for path in paths}


class ChangelogRecordsTests(unittest.TestCase):
    def setUp(self) -> None:
        top = _top_level()
        if top is None:
            self.skipTest("not a git checkout")
        self.top = top
        self.charged = _charged()

    def test_every_top_level_entry_is_charged_or_exempt_exactly_once(self) -> None:
        for name in sorted(self.top - {RECORD}):
            decided = (name in self.charged) + (name in EXEMPT)
            self.assertEqual(decided, 1, name)

    def test_every_named_entry_exists_in_the_tree(self) -> None:
        named = self.charged | EXEMPT
        self.assertEqual(sorted(named - self.top), [])

    def test_a_directory_entry_ends_in_a_slash_and_a_file_entry_does_not(self) -> None:
        for name in sorted(self.charged | EXEMPT):
            is_dir = (REPO / name.rstrip("/")).is_dir()
            self.assertEqual(name.endswith("/"), is_dir, name)


if __name__ == "__main__":
    unittest.main()
