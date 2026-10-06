"""The changelog-currency gate, and its red proof.

The rule is that every harness change is recorded in CHANGELOG.md or declared exempt.
The load-bearing tests are the red ones: a harness change with no record must exit 1,
or the gate asserts nothing.

Stdlib-only; runs without uv as ``python tests/test_changelog_currency.py``.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import changelog_currency  # noqa: E402


class UnrecordedPathsTests(unittest.TestCase):
    def test_a_harness_change_without_a_record_is_named(self) -> None:
        changed = ["src/fathom/cli.py", "docs/README.md"]
        self.assertEqual(
            changelog_currency.unrecorded_harness_paths(changed), ["src/fathom/cli.py"]
        )

    def test_every_harness_path_is_covered(self) -> None:
        """The package, its metadata, the plugin surface and the repository tooling."""
        for path in (
            "src/fathom/reconcile.py",
            "pyproject.toml",
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            "commands/run.md",
            "mcp/fathom_server.py",
            "skills/fathom-eval/SKILL.md",
            "tools/ledger_index.py",
            "tools/git-hooks/pre-commit",
        ):
            self.assertEqual(changelog_currency.unrecorded_harness_paths([path]), [path])

    def test_a_changelog_edit_in_the_same_diff_clears_the_gate(self) -> None:
        changed = ["src/fathom/cli.py", "CHANGELOG.md"]
        self.assertEqual(changelog_currency.unrecorded_harness_paths(changed), [])

    def test_docs_tests_and_repository_config_do_not_trip_the_gate(self) -> None:
        """Nothing here reaches an installed copy of the engine."""
        changed = [
            "docs/adr/0002-trial-run-append-only-ledger.md",
            "docs/specs/2026-06-10-fathom-v1-design.md",
            "tests/test_cli.py",
            "examples/data-root/fathom.toml",
            "examples/data-root/ledger/example.jsonl",
            ".github/workflows/ci.yml",
            ".pre-commit-config.yaml",
            ".gitignore",
            ".gitattributes",
            "uv.lock",
            "README.md",
            "README-plugin.md",
            "CONTRIBUTING.md",
            "CLAUDE.md",
            "LICENSE",
            "assets/fathom-mark-light.svg",
        ]
        self.assertEqual(changelog_currency.unrecorded_harness_paths(changed), [])

    def test_a_harness_name_is_matched_whole(self) -> None:
        """A prefix match on a directory name or a root file must not catch look-alikes."""
        changed = ["srcs/notes.md", "docs/src/example.py", "tests/fixtures/pyproject.toml"]
        self.assertEqual(changelog_currency.unrecorded_harness_paths(changed), [])

    def test_backslash_paths_are_normalized(self) -> None:
        """A Windows-rendered diff must not slip past a forward-slash prefix match."""
        self.assertEqual(
            changelog_currency.unrecorded_harness_paths(["src\\fathom\\cli.py"]),
            ["src/fathom/cli.py"],
        )


def _engine_tree_top_level() -> set[str] | None:
    """The top-level names this checkout tracks or would track, present on disk.

    ``None`` outside a git checkout (an unpacked sdist, say), where there is no tree to
    hold the classes to. Paths deleted in the working tree but still in the index are
    left out, so a removal in progress is judged by the tree it produces.
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


class EngineTreeTests(unittest.TestCase):
    """The classes describe this repository's tree: every entry in exactly one, none stale.

    A class entry naming something the tree no longer has is how a gate keeps describing
    a repository that has moved on; an entry the classes do not name is a path whose
    changes nobody decided about.
    """

    def setUp(self) -> None:
        top = _engine_tree_top_level()
        if top is None:
            self.skipTest("not a git checkout")
        self.top = top

    def test_every_top_level_entry_is_classified_exactly_once(self) -> None:
        for name in sorted(self.top):
            harness = name in changelog_currency.HARNESS_FILES or (
                name in changelog_currency.HARNESS_PREFIXES
            )
            exempt = name in changelog_currency.EXEMPT_FILES or (
                name in changelog_currency.EXEMPT_PREFIXES
            )
            record = name == changelog_currency.RECORD
            self.assertEqual(harness + exempt + record, 1, name)

    def test_every_class_entry_exists_in_the_tree(self) -> None:
        named = {
            *changelog_currency.HARNESS_PREFIXES,
            *changelog_currency.HARNESS_FILES,
            *changelog_currency.EXEMPT_PREFIXES,
            *changelog_currency.EXEMPT_FILES,
        }
        self.assertEqual(sorted(named - self.top), [])

    def test_a_directory_entry_ends_in_a_slash_and_a_file_entry_does_not(self) -> None:
        for prefix in (*changelog_currency.HARNESS_PREFIXES, *changelog_currency.EXEMPT_PREFIXES):
            self.assertTrue(prefix.endswith("/") and prefix.count("/") == 1, prefix)
        for name in (*changelog_currency.HARNESS_FILES, *changelog_currency.EXEMPT_FILES):
            self.assertNotIn("/", name)

    def test_exempt_paths_never_trip_the_gate(self) -> None:
        changed = [
            *(f"{prefix}example" for prefix in changelog_currency.EXEMPT_PREFIXES),
            *changelog_currency.EXEMPT_FILES,
        ]
        self.assertEqual(changelog_currency.unrecorded_harness_paths(changed), [])


class DeclarationTests(unittest.TestCase):
    def test_a_declaration_line_reads(self) -> None:
        for line in (
            "Changelog: not needed (comment-only refactor)",
            "changelog: none (typo in a docstring)",
        ):
            message = f"fix(cli): something small\n\n{line}\n"
            self.assertTrue(changelog_currency.declared(message), line)

    def test_prose_mentioning_the_changelog_is_not_a_declaration(self) -> None:
        message = "docs: explain that the changelog: not needed escape exists\n"
        self.assertFalse(changelog_currency.declared(message))


class MainTests(unittest.TestCase):
    def test_an_unrecorded_harness_change_exits_nonzero(self) -> None:
        """The red proof: the gate can actually fail."""
        self.assertEqual(changelog_currency.main(["src/fathom/cli.py"]), 1)

    def test_an_unrecorded_metadata_change_exits_nonzero(self) -> None:
        """pyproject.toml is what a data root installs; a change there is a harness change."""
        self.assertEqual(changelog_currency.main(["pyproject.toml"]), 1)

    def test_a_recorded_change_exits_zero(self) -> None:
        self.assertEqual(changelog_currency.main(["src/fathom/cli.py", "CHANGELOG.md"]), 0)

    def test_a_declared_exemption_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            messages = Path(tmp) / "messages.txt"
            messages.write_text(
                "chore(tools): rename an internal\n\nChangelog: not needed (no behaviour)\n",
                encoding="utf-8",
                newline="\n",
            )
            self.assertEqual(
                changelog_currency.main(["src/fathom/cli.py", "--messages", str(messages)]), 0
            )

    def test_the_declaration_does_not_excuse_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            messages = Path(tmp) / "messages.txt"
            messages.write_text("fix(cli): a real change\n", encoding="utf-8", newline="\n")
            self.assertEqual(
                changelog_currency.main(["src/fathom/cli.py", "--messages", str(messages)]), 1
            )


if __name__ == "__main__":
    unittest.main()
