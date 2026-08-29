"""The changelog-currency gate, and its red proof.

The gate exists because the 0.4.0 cut shipped with two of the day's commits unrecorded —
the rule was prose, and prose was violated the day it mattered.  The load-bearing tests
are the red ones: a harness change with no record must exit 1, or the gate asserts
nothing.

Stdlib-only; runs without uv as ``python tests/test_changelog_currency.py``.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import changelog_currency  # noqa: E402


class UnrecordedPathsTests(unittest.TestCase):
    def test_a_harness_change_without_a_record_is_named(self) -> None:
        changed = ["src/fathom/cli.py", "docs/STATUS.md"]
        self.assertEqual(
            changelog_currency.unrecorded_harness_paths(changed), ["src/fathom/cli.py"]
        )

    def test_every_harness_prefix_is_covered(self) -> None:
        for path in (
            "src/fathom/reconcile.py",
            "tools/ledger_index.py",
            "commands/run.md",
            "mcp/fathom_server.py",
        ):
            self.assertEqual(changelog_currency.unrecorded_harness_paths([path]), [path])

    def test_a_changelog_edit_in_the_same_diff_clears_the_gate(self) -> None:
        changed = ["src/fathom/cli.py", "CHANGELOG.md"]
        self.assertEqual(changelog_currency.unrecorded_harness_paths(changed), [])

    def test_records_and_data_do_not_trip_the_gate(self) -> None:
        """Ledgers, scenarios, banks and docs are gated elsewhere (or are the record)."""
        changed = [
            "ledger/e2-data-semantics.jsonl",
            "scenarios/ablation-v2/bare.toml",
            "tasks/model-tier-v1/task.toml",
            "docs/reports/LEDGER-INDEX.md",
            "tests/test_cli.py",
        ]
        self.assertEqual(changelog_currency.unrecorded_harness_paths(changed), [])

    def test_backslash_paths_are_normalized(self) -> None:
        """A Windows-rendered diff must not slip past a forward-slash prefix match."""
        self.assertEqual(
            changelog_currency.unrecorded_harness_paths(["src\\fathom\\cli.py"]),
            ["src/fathom/cli.py"],
        )


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
