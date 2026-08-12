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

**Existence was not enough** (the second defect, 2026-08-11). The gate proved a
verdict existed; it could not prove the verdict had been read against the ledger
*as committed*. A re-validation report was published against a 10-trial snapshot,
an eleventh trial was appended to the same ledger later in the same wave, and
three documents ended up carrying three different control-pool sizes and three
different p-values — none of them the committed state — with this suite green
throughout. So the ratchet gained a second tooth: ``docs/reports/LEDGER-INDEX.md``
is generated from the ledgers (sha256 + per-arm completed counts) and compared
byte-for-byte here. Any append turns this red until the index is re-rendered, and
the re-render diff names the arms that moved.

The honest limit: the index does not read prose. It cannot tell that a paragraph
says ``0/7`` where the ledger says 0/8. What it removes is the excuse — the
correct number is committed, hash-dated and adjacent, so the contradiction is
mechanical to find rather than something a reader must re-derive from JSONL.

Stdlib-only: ``python tests/test_ledger_coverage.py`` runs without uv.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
LEDGER_DIR = REPO / "ledger"
REPORTS_DIR = REPO / "docs" / "reports"
STATUS = REPO / "docs" / "STATUS.md"

sys.path.insert(0, str(REPO / "tools"))

import ledger_index  # noqa: E402

# The generated index names every bank, so it would satisfy the coverage scan for
# all of them. It is a stamp, not a verdict — exclude it or the first gate goes vacuous.
GENERATED_REPORTS = {"LEDGER-INDEX.md"}


def committed_banks() -> list[str]:
    """Bank names with a committed ledger (archived ledgers are excluded)."""
    if not LEDGER_DIR.is_dir():
        return []
    return sorted(p.stem for p in LEDGER_DIR.glob("*.jsonl"))


def uncovered_banks() -> list[str]:
    """Banks whose conclusion is findable in neither a report nor STATUS."""
    reports = list(REPORTS_DIR.glob("*.md")) if REPORTS_DIR.is_dir() else []
    bodies = [
        (r.name, r.read_text(encoding="utf-8", errors="replace"))
        for r in reports
        if r.name not in GENERATED_REPORTS
    ]
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

    def test_the_ledger_index_is_current(self) -> None:
        """No verdict may be read against a ledger that has moved since it was stamped."""
        rendered = ledger_index.render(LEDGER_DIR)
        committed = (
            ledger_index.INDEX_PATH.read_text(encoding="utf-8")
            if ledger_index.INDEX_PATH.is_file()
            else ""
        )
        self.assertEqual(
            committed,
            rendered,
            "docs/reports/LEDGER-INDEX.md disagrees with ledger/. A ledger was appended to "
            "without re-stamping. Re-render with `python tools/ledger_index.py --write`, read "
            "the diff — it names the arms whose n moved — and update every document that quotes "
            "those counts, pooled control totals or p-values before committing.",
        )

    def test_the_index_check_can_actually_fail(self) -> None:
        """A byte appended to a ledger must change the rendered index.

        Without this, a renderer that silently dropped rows would keep the freshness
        gate green forever — the vacuous-gate class this repo keeps catching.
        """
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            mirror = Path(tmp) / "ledger"
            shutil.copytree(LEDGER_DIR, mirror, ignore=shutil.ignore_patterns("archive"))
            before = ledger_index.render(mirror)
            victim = sorted(mirror.glob("*.jsonl"))[0]
            with victim.open("a", encoding="utf-8") as fh:
                fh.write('{"kind": "trial", "scenario": "seeded", "status": "completed"}\n')
            after = ledger_index.render(mirror)
            self.assertNotEqual(before, after, "the index does not move when a ledger does")
            self.assertIn("seeded:1", after)

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
