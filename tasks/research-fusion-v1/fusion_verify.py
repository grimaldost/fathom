"""Shared verifier for the multi-substrate research bank (harness-side, blind).

Reads the candidate's work ONLY from the result-view path in ``argv[1]``. Every arm
gets the same question and the same instruction; only the mount differs, and this
module never sees which (ADR-0003).

What this bank measures, and the weaker claim it makes on purpose
-----------------------------------------------------------------
MANT-B36 asks two things: how often a surfaced divergence **changed a decision**, and
cost per decision changed against a single-provider run. Neither is observable by a
verifier. "Changed a decision" is a counterfactual, and scoring decision *correctness*
needs questions whose answers are known post-hoc and were not obvious at the time — a
set that does not exist and is the real long pole
(``docs/specs/2026-08-11-cross-project-gate-banks.md`` Gate B).

So this bank measures the **precondition** of the moat claim instead, which is
deterministic, blind, and — the part that matters — able to REJECT the claim on its own
terms. The tool's advertised output is a machine-readable epistemic sidecar carrying
cross-substrate divergences whose ``substrates`` join back to ``sources[].label``. If a
real fan-out over contested questions returns no divergences, or divergences with one
side, or substrate labels that join to nothing, then the surface the moat rests on is
not being produced, and no decision-value study is worth buying yet.

A structurally perfect sidecar is NOT evidence that fusion beats one good model. It is
evidence that the thing fusion is supposed to produce exists. State it that way.

Criterion classes, which the report must keep apart:

``availability``
    Only an arm with the tool mounted can produce a cross-substrate divergence at all.
    The bare arm scores 0 on these BY CONSTRUCTION — that is a floor, not a result.
``well-formedness``
    Given a sidecar, is it internally consistent? This is where the claim can fail on
    its own terms, and it is the load-bearing class.

Stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BRIEF_FILE = "brief.md"
SIDECAR_FILE = "sidecar.json"
QUESTION_FILE = "question.txt"
MIN_SUBSTRATES = 2
MIN_SIDES = 2
QUESTION_OVERLAP = 0.6

CRITERIA = (
    "brief_written",
    "sidecar_written",
    "sidecar_parses",
    "sidecar_required_fields",
    "sidecar_question_matches",
    "claims_present",
    "multi_substrate",
    "divergences_present",
    "divergences_well_formed",
    "substrate_source_join",
    "verification_queue_present",
)

# Required on write by the tool's own contract (core/sidecar.py REQUIRED_ON_WRITE).
REQUIRED_ON_WRITE = ("question", "generated_at", "sources")

_STOP = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "should",
    "that",
    "the",
    "to",
    "vs",
    "with",
    "which",
}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 2}


def _labels(sidecar: dict) -> set[str]:
    out: set[str] = set()
    for src in sidecar.get("sources") or []:
        if isinstance(src, dict) and isinstance(src.get("label"), str):
            out.add(src["label"])
    return out


def _cited_substrates(sidecar: dict) -> list[str]:
    """Every substrate token that must join back to a ``sources[].label``."""
    out: list[str] = []
    for div in sidecar.get("divergences") or []:
        if isinstance(div, dict):
            out.extend(s for s in (div.get("substrates") or []) if isinstance(s, str))
    for cite in sidecar.get("source_citations") or []:
        if isinstance(cite, dict) and isinstance(cite.get("substrate"), str):
            out.append(cite["substrate"])
    return out


def grade(root: Path) -> dict[str, bool]:
    results = dict.fromkeys(CRITERIA, False)

    brief = root / BRIEF_FILE
    results["brief_written"] = brief.is_file() and bool(
        brief.read_text(encoding="utf-8", errors="replace").strip()
    )

    sidecar_path = root / SIDECAR_FILE
    if not sidecar_path.is_file():
        return results
    results["sidecar_written"] = True

    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, ValueError):
        return results
    if not isinstance(sidecar, dict):
        return results
    results["sidecar_parses"] = True

    results["sidecar_required_fields"] = all(bool(sidecar.get(f)) for f in REQUIRED_ON_WRITE)

    # A sidecar that answers a different question is the failure its own schema
    # comment names; the question is staged beside the fixture so this is checkable.
    asked_path = root / QUESTION_FILE
    if asked_path.is_file() and isinstance(sidecar.get("question"), str):
        asked = _words(asked_path.read_text(encoding="utf-8", errors="replace"))
        answered = _words(sidecar["question"])
        results["sidecar_question_matches"] = bool(asked) and (
            len(asked & answered) / len(asked) >= QUESTION_OVERLAP
        )

    results["claims_present"] = bool(sidecar.get("claims"))
    results["verification_queue_present"] = bool(sidecar.get("verification_queue"))

    labels = _labels(sidecar)
    results["multi_substrate"] = len(labels) >= MIN_SUBSTRATES

    divergences = [d for d in (sidecar.get("divergences") or []) if isinstance(d, dict)]
    results["divergences_present"] = bool(divergences)
    results["divergences_well_formed"] = bool(divergences) and all(
        len([s for s in (d.get("sides") or []) if str(s).strip()]) >= MIN_SIDES
        and bool([s for s in (d.get("substrates") or []) if str(s).strip()])
        for d in divergences
    )

    cited = _cited_substrates(sidecar)
    results["substrate_source_join"] = bool(cited) and all(s in labels for s in cited)

    return results


# The gate: the arm produced the two artifacts and the sidecar is machine-readable.
# Everything past that is per-criterion signal.
GATE = ("brief_written", "sidecar_written", "sidecar_parses")


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve()
    criteria = grade(root)
    print(json.dumps(criteria, sort_keys=True))
    return 0 if all(criteria[k] for k in GATE) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
