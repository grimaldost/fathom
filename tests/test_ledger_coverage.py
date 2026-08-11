"""Every committed ledger must have a rendered verdict somewhere (FATH-B06).

14 reports stood against 19 committed ledgers, and five analyses' conclusions
survived only in commit messages and another repo's design docs — while a sibling
backlog cited one of them to justify retiring a shipped surface. The failure was
structural, not personal: the expensive step (running the matrix) is instrumented,
resumable and gated, while the cheap decisive step (writing the verdict where a
consumer can find it) was unenforced prose. The prose form shipped in CONTRIBUTING
and recurred.

This is the ratchet. A new ledger may not be committed without either a
``docs/reports/`` entry naming its bank or a row in ``docs/STATUS.md``. Running
the matrix is the part that costs money; publishing the verdict costs nothing,
so the gate binds on the free step.

Stdlib-only: ``python tests/test_ledger_coverage.py`` runs without uv.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
LEDGER_DIR = REPO / "ledger"
REPORTS_DIR = REPO / "docs" / "reports"
STATUS = REPO / "docs" / "STATUS.md"


def committed_banks() -> list[str]:
    """Bank names with a committed ledger (archived ledgers are excluded)."""
    if not LEDGER_DIR.is_dir():
        return []
    return sorted(p.stem for p in LEDGER_DIR.glob("*.jsonl"))


def uncovered_banks() -> list[str]:
    """Banks whose conclusion is findable in neither a report nor STATUS."""
    reports = list(REPORTS_DIR.glob("*.md")) if REPORTS_DIR.is_dir() else []
    bodies = [(r.name, r.read_text(encoding="utf-8", errors="replace")) for r in reports]
    status = STATUS.read_text(encoding="utf-8", errors="replace") if STATUS.is_file() else ""

    missing = []
    for bank in committed_banks():
        in_report = any(bank in name or bank in body for name, body in bodies)
        if not in_report and bank not in status:
            missing.append(bank)
    return missing


class LedgerCoverageTests(unittest.TestCase):
    def test_every_committed_ledger_has_a_findable_verdict(self) -> None:
        missing = uncovered_banks()
        self.assertEqual(
            missing,
            [],
            "these banks were run and paid for but their conclusion is published "
            f"nowhere a consumer can find it: {missing}. Write the findings report "
            "under docs/reports/ (the ledger already exists — `fathom report <bank>` "
            "renders the scorecard, and the verdict is a paragraph on top of it), or "
            "add the analysis row to docs/STATUS.md.",
        )

    def test_the_check_can_actually_fail(self) -> None:
        """The gate is not satisfied by absence.

        A coverage check that passes because it found no ledgers would be exactly
        the vacuous gate this repo keeps catching elsewhere.
        """
        self.assertTrue(
            committed_banks(),
            "no committed ledgers found — the coverage check would pass vacuously",
        )


if __name__ == "__main__":
    unittest.main()
