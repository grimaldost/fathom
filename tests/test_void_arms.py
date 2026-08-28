"""A void arm's number may not appear in a document without saying it is void.

Some arms are not merely *wrong*, they are **unattributable**: the configuration that
produced their trials is unknown and unrecoverable, so no correction can restate the
number and no re-analysis can rescue it. ``haiku-gate-sg`` is the case that motivated
this file. Its gate probe shipped as a literal placeholder path, handed to the shell
verbatim, so the probe never executed and the arm silently ran as its own control. Its
ledger ``config_hash`` has no preimage across ~170k candidate command forms while all
fourteen sibling arms reconstruct exactly.

The defect was found and disclosed. **The disclosure did not travel.** It was written in
one report while the number stayed unqualified in the two reports that used it, in the
project's own status index, and — worst — under a *negative product verdict* (retire the
escalation ladder) whose evidence was a trigger that "fired 0/10", which is exactly what
an inert probe produces. It was also staged as the bar a future *paid* engine arm would
be priced against. Six weeks passed with the correction one file away from every reader
who needed it.

That is the gap this closes. A prose correction in one document is not a mechanism; it
decays the moment someone reads a different document. Here the registry is the mechanism:
naming an arm void makes the suite red until every point of use says so.

Stdlib-only; runs without uv as ``python tests/test_void_arms.py``.
"""

from __future__ import annotations

import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

# Any of these, case-insensitively, marks a mention as qualified at its point of use.
QUALIFIERS = (
    "void",
    "unattributable",
    "historical only",
    "not reproducible",
    "correction",
    "withdrawn",
)

VOID_ARMS = {
    "haiku-gate-sg": {
        "why": (
            "the gate probe shipped as a literal placeholder path, so it never executed and "
            "the arm ran as its own control; its config_hash has no preimage"
        ),
        # The report that carries the full disclosure. It is the source, so it is exempt:
        # requiring markers there would demand a report annotate its own findings section.
        "disclosure": "docs/reports/2026-08-11-ablation-v2-series-arm-authoring.md",
        # Generated artifacts that may name the arm without a marker, and why.
        # LEDGER-INDEX.md is machine-rendered and marked "Do not hand-edit"; it reports a raw
        # count of completed trial rows, which stays arithmetically true, and no pass rate.
        "generated_exempt": ("docs/reports/LEDGER-INDEX.md",),
    },
}


def _mentions(arm: str) -> list[tuple[pathlib.Path, int, str]]:
    """Every line under docs/ naming ``arm``, excluding names it is a prefix of.

    The negative lookahead matters: ``haiku-gate-sg2`` is the *forked replacement* arm and
    naming it is never a defect, but it contains the void arm's name as a substring.
    """
    pattern = re.compile(re.escape(arm) + r"(?!\d)")
    hits = []
    for path in sorted(DOCS.rglob("*.md")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                hits.append((path, lineno, line))
    return hits


class VoidArmDisclosureTests(unittest.TestCase):
    def test_every_mention_of_a_void_arm_is_qualified_where_it_is_used(self) -> None:
        for arm, spec in VOID_ARMS.items():
            exempt = {spec["disclosure"], *spec["generated_exempt"]}
            unqualified = []
            for path, lineno, line in _mentions(arm):
                rel = path.relative_to(REPO).as_posix()
                if rel in exempt:
                    continue
                if not any(q in line.lower() for q in QUALIFIERS):
                    unqualified.append(f"{rel}:{lineno}: {line.strip()[:110]}")

            self.assertEqual(
                unqualified,
                [],
                f"`{arm}` is a void arm ({spec['why']}), but these lines name it with no "
                f"qualification a reader would see at that point:\n  "
                + "\n  ".join(unqualified)
                + f"\n\nAdd one of {QUALIFIERS} on the line itself. A correction living only in "
                f"{spec['disclosure']} is what already failed: it did not reach the reader of "
                "any other document.",
            )

    def test_the_disclosure_and_exempt_files_exist(self) -> None:
        """An exemption pointing at a moved file would silently widen itself."""
        for arm, spec in VOID_ARMS.items():
            for rel in (spec["disclosure"], *spec["generated_exempt"]):
                self.assertTrue(
                    (REPO / rel).is_file(),
                    f"{arm}: exempt path {rel} does not exist, so the exemption is unbounded",
                )

    def test_the_check_can_actually_fail(self) -> None:
        """The gate is not satisfied by absence — the vacuous shape this repo keeps catching.

        A registry naming an arm that appears nowhere, or a qualifier list matching every
        line, would both pass forever while checking nothing.
        """
        self.assertTrue(VOID_ARMS, "no void arms registered — the check would pass vacuously")
        for arm in VOID_ARMS:
            mentions = _mentions(arm)
            self.assertTrue(
                mentions,
                f"`{arm}` is registered void but named in no document under docs/ — "
                "either the registry is stale or the scan is broken",
            )
            self.assertTrue(
                any(not any(q in line.lower() for q in QUALIFIERS) for _, _, line in mentions),
                f"every line naming `{arm}` contains a qualifier, including in the disclosure "
                "report's own prose — the qualifier list is too broad to detect anything",
            )


if __name__ == "__main__":
    unittest.main()
