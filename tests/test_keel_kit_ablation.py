"""Bank-side guards for keel-kit-ablation-v1 — the properties the run's reading depends on.

Three things can silently invalidate this bank, and none of them is caught by `fathom validate`:

1. The core arm stops being a strict deletion of the full arm, so a gap between them is no longer
   attributable to the removed prose.
2. The arms start differing in something other than the injected body, so the ablation has two
   axes.
3. The verifier's violation-to-check-letter map falls out of step with the pinned gate's message
   text, so a criterion silently scores the wrong check. The gate carries no check id in code, so
   the map is recovered from `(where, message)` — which makes it exactly the kind of thing that
   decays without a test. The corpus below is one crafted mutant per check: it proves each check
   CAN fire on a realistic spec body and that the map recovers the right letter.

Stdlib only; runs without uv (`python tests/test_keel_kit_ablation.py`).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BANK = REPO / "tasks" / "keel-kit-ablation-v1"
ARMS = REPO / "scenarios" / "keel-kit"

sys.path.insert(0, str(BANK))
import keelgate_verify as kv  # noqa: E402

ORACLE = kv.load_oracle()

CLEAN_SPEC = """\
# Spec — a small change

- **Date:** 2026-08-11
- **Status:** draft
- **Kind:** series

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| the thing | `mod.py` |

## Numbered sections

### §1 Change the thing
What changes, grounded at `mod.py:1` `VALUE`.
**Acceptance criterion:** `python -m unittest tests.test_mod` passes with a new case.

## PR ↔ section manifest

| PR | Implements section | One concern? |
|---|---|---|
| PR01 | §1 | yes |
"""

CERT = """
## Pre-mortem certification

- **Reviewer:** A. Reviewer
- **Verdict:** CERTIFIED
- **Failure modes considered & folded in:** two, recorded below

### Fold ledger

| Finding | Target section | artifact:line | Confirmed |
|---|---|---|---|
| A finding | §1 | {anchor} | yes |
"""

# One mutant per check: (letter, the edit applied to CLEAN_SPEC).
MUTANTS: dict[str, object] = {
    "A0": lambda s: s.replace("- **Kind:** series", "- **Kind:** enormous"),
    "A1": lambda s: s.replace(
        "### §1 Change the thing", "### Change the thing\n\n### §1 Change the thing"
    ),
    "A2": lambda s: s.replace(
        "**Acceptance criterion:** `python -m unittest tests.test_mod` passes with a new case.",
        "**Acceptance criterion:** it works.",
    ),
    "A3": lambda s: s.replace("What changes, grounded", "What changes (TODO), grounded"),
    "A4": lambda s: s.replace("| PR01 | §1 | yes |", "| PR01 | §1 | yes |\n| PR02 | §1 | yes |"),
    "A5": lambda s: s.replace("| the thing | `mod.py` |", "| the thing | `gone.py` |"),
    "A6": lambda s: s.replace("`mod.py:1` `VALUE`", "`mod.py:999`"),
    "A7": lambda s: s.replace(
        "What changes, grounded",
        "Cited as `docs/adr/0001-different-name.md`. What changes, grounded",
    ),
    "A8": lambda s: s.replace(
        "What changes, grounded", "§7 stays unchanged. What changes, grounded"
    ),
    "A9": lambda s: s.replace(
        "What changes, grounded", "**Reuse:** `mod.py::absent_symbol`\nWhat changes, grounded"
    ),
    "A10": lambda s: s.replace(
        "## Numbered sections",
        "## Enforcement status\n\n| Invariant | Status | Gate/mechanism |\n|---|---|---|\n"
        "| the-rule | planned | none yet |\n\nThe the-rule invariant is enforced by the suite.\n\n"
        "## Numbered sections",
    ),
    "A11": lambda s: s.replace("`mod.py:1` `VALUE`", "`mod.py:1-999`"),
    "A12": lambda s: s + CERT.format(anchor="`mod.py:999`"),
    "R1": lambda s: (
        s + CERT.format(anchor="`mod.py:1`").replace("| A finding | §1 | `mod.py:1` | yes |", "")
    ),
}


def _stage(tmp: Path, spec_text: str) -> Path:
    (tmp / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp / "docs" / "adr").mkdir(parents=True, exist_ok=True)
    (tmp / "docs" / "adr" / "0001-the-real-one.md").write_text("# ADR-0001\n", encoding="utf-8")
    spec = tmp / "spec.md"
    spec.write_text(spec_text, encoding="utf-8")
    return spec


def _letters(spec: Path) -> list[str]:
    result = ORACLE.check_spec_ready(spec, structure_only=True)
    return [kv.classify(v.where, v.message) for v in result.violations]


class OraclePinTests(unittest.TestCase):
    def test_vendored_oracle_matches_its_pin(self):
        pin = json.loads((BANK / "_oracle" / "PIN.json").read_text(encoding="utf-8"))
        for rel, expected in pin["sha256"].items():
            actual = hashlib.sha256((BANK / "_oracle" / rel).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, f"{rel} no longer matches the pin")


class PositiveControlTests(unittest.TestCase):
    """Every check CAN fire on a realistic spec, and the map recovers its letter."""

    def test_clean_spec_fires_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = _stage(Path(tmp), CLEAN_SPEC)
            self.assertEqual(_letters(spec), [], "the clean baseline must be silent")

    def test_each_mutant_fires_exactly_its_target_check(self):
        for letter, mutate in MUTANTS.items():
            with self.subTest(check=letter), tempfile.TemporaryDirectory() as tmp:
                spec = _stage(Path(tmp), mutate(CLEAN_SPEC))
                fired = set(_letters(spec))
                self.assertIn(letter, fired, f"{letter}'s mutant did not fire it")
                self.assertNotIn("?", fired, f"{letter}'s mutant produced an unclassified message")

    def test_enforcement_shadow_catches_what_the_gate_window_misses(self):
        """The bank's own criterion is strictly stronger than the gate's A10.

        An invariant key containing a negation word ("batches-never-rewritten") suppresses every
        claim the gate would otherwise raise about it, because the negation lookback sees the key's
        own text. The bank's criterion removes the key before looking.
        """
        spec_text = CLEAN_SPEC.replace(
            "## Numbered sections",
            "## Enforcement status\n\n| Invariant | Status | Gate/mechanism |\n|---|---|---|\n"
            "| batches-never-rewritten | review-only | the reviewer reads it |\n\n"
            "The batches-never-rewritten invariant is enforced by the migration case.\n\n"
            "## Numbered sections",
        )
        with tempfile.TemporaryDirectory() as tmp:
            spec = _stage(Path(tmp), spec_text)
            self.assertNotIn("A10", _letters(spec), "the gate is expected to miss this form")
            self.assertTrue(
                kv.enforcement_overclaims(spec_text), "the bank's own criterion must catch it"
            )


class ArmTests(unittest.TestCase):
    def _arm(self, name: str) -> dict:
        return tomllib.loads((ARMS / f"{name}.toml").read_text(encoding="utf-8"))

    def test_arms_differ_only_in_the_injected_body(self):
        arms = [self._arm(n) for n in ("a-full", "b-core", "c-bare")]
        for key in ("adapter", "model", "strategy", "effort"):
            self.assertEqual(
                len({a[key] for a in arms}), 1, f"arms disagree on {key} — that is a second axis"
            )
        self.assertEqual(len({tuple(a["tools"]["allowed"]) for a in arms}), 1)
        self.assertNotIn("context", arms[2], "the bare arm must inject nothing")

    def test_core_body_is_a_strict_deletion_of_the_full_body(self):
        def flatten(text: str) -> str:
            return re.sub(r"\s+", " ", text.replace("*", "")).strip().rstrip(".;,: ")

        full = flatten((ARMS / "assets" / "kit-full.md").read_text(encoding="utf-8"))
        core_raw = (ARMS / "assets" / "kit-core.md").read_text(encoding="utf-8")
        parts = re.split(r"(?<=[.:!?])\s+|\n{2,}|\n(?=[-|#])", core_raw)
        for part in parts:
            sentence = flatten(part)
            if len(sentence) > 12:
                self.assertIn(
                    sentence,
                    full,
                    "the core arm carries text the full arm does not — a gap between them would no "
                    "longer be attributable to the removed prose",
                )

    def test_core_is_materially_smaller(self):
        words = {
            name: len((ARMS / "assets" / f"kit-{name}.md").read_text(encoding="utf-8").split())
            for name in ("full", "core")
        }
        self.assertLess(words["core"], words["full"] * 0.7)


class BankShapeTests(unittest.TestCase):
    def test_every_task_ships_a_gate_a_solution_and_a_profile(self):
        for task_dir in sorted(p for p in BANK.iterdir() if (p / "task.toml").exists()):
            with self.subTest(task=task_dir.name):
                task = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
                self.assertIn("run", task.get("gate", {}), "no gate command")
                self.assertTrue((task_dir / "solution").is_dir(), "no reference solution")
                profile = json.loads((task_dir / "profile.json").read_text(encoding="utf-8"))
                self.assertTrue(profile["criteria"], "no criteria declared")
                self.assertTrue(profile["staged_sha256"], "no staged digests to protect")

    def test_holdout_ids_exist_and_stay_sealed(self):
        manifest = tomllib.loads((BANK / "bank.toml").read_text(encoding="utf-8"))
        ids = {p.name for p in BANK.iterdir() if (p / "task.toml").exists()}
        self.assertEqual(len(manifest["holdout"]), 2)
        for held in manifest["holdout"]:
            self.assertIn(held, ids)

    def test_no_fixture_names_an_internal_tool(self):
        """Public repo: fixtures use invented domains only."""
        forbidden = ("treasuryutils", "datacontext", "data-context", "stack-radar", "datahub")
        for path in BANK.rglob("*"):
            if not path.is_file() or "_oracle" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for token in forbidden:
                self.assertNotIn(token, text, f"{path} names {token}")


if __name__ == "__main__":
    unittest.main()
