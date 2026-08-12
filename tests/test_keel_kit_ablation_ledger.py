"""Guards binding the ablation's published reading to the ledger it was read from.

The 2026-08-11 proof report states claims 6 and 7 at a specific N, and every interval and
p-value in its SS1.7 is a function of that N. Two things would make the published reading
false without anyone editing the report:

1. **The ledger grows.** Stage 2 (the `--repeats 2` pass) is licensed and unbought. If it
   lands, every "n = 1 per (arm, task) cell" statement in SS1.6 and SS1.7 becomes wrong, and
   the note-only discordance the verdicts turn on is recomputed from a different base. These
   tests fail loudly in that case, which is the intended behaviour: new trials oblige a new
   revision, they do not silently improve the old one.
2. **The holdout is opened.** The sealed tasks are pre-registered as unspent for this
   contrast. A holdout trial appearing in this ledger invalidates SS1.4's seal.

They also pin the two counts the cut decision rests on -- the realised discordant pairs on
the deciding class, and the fact that the class was exercised at all -- so a later reading
cannot restate either from memory.

These are guards on a *published claim*, not on behaviour. They are expected to fail the day
more data arrives; the fix is to re-read the ledger and revise the report, never to relax the
numbers here.

Stdlib only; runs without uv (`python tests/test_keel_kit_ablation_ledger.py`).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "ledger" / "keel-kit-ablation-v1.jsonl"

ARMS = ("a-full-014", "b-vnext-full", "c-vnext-core", "d-bare")
DEV_TASKS = (
    "author-cli-flag",
    "author-schema-evolve",
    "author-single-change",
    "author-two-consumer",
    "repair-bijection",
    "repair-ledger-drift",
)
# The class the cut decision is read from (report SS1.6 rule 3). `enforcement_overclaims_absent`
# is a member but exists only on the sealed repair task, so it scores on no dev trial.
NOTE_ONLY = (
    "enforcement_claims_clean",
    "enforcement_overclaims_absent",
    "reuse_refs_resolve",
    "range_anchors_balanced",
)

# As published in revision 3. Every one is recomputable from the ledger by
# `kk_verdict.py`; they are restated here so a drifting ledger fails a test.
PUBLISHED_TRIALS = 24
PUBLISHED_REPEATS = (0,)
PUBLISHED_SPEND_USD = 9.7572
PUBLISHED_NOTE_ONLY = {
    "a-full-014": (11, 18),
    "b-vnext-full": (13, 18),
    "c-vnext-core": (10, 18),
    "d-bare": (7, 18),
}
PUBLISHED_BC_DISCORDANT = (4, 1)  # B_only, C_only -- exact McNemar p = 0.375


def load() -> tuple[list[dict], list[dict]]:
    runs, trials = [], []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        (runs if rec.get("kind") == "run" else trials).append(rec)
    return runs, trials


class LedgerShape(unittest.TestCase):
    def setUp(self):
        self.runs, self.trials = load()

    def test_trial_count_matches_the_published_reading(self):
        self.assertEqual(
            len(self.trials),
            PUBLISHED_TRIALS,
            "the ledger no longer holds the 24 trials the report reads; re-read it and "
            "revise the report rather than editing this number",
        )

    def test_every_cell_is_n_equals_one(self):
        self.assertEqual(sorted({t["repeat"] for t in self.trials}), list(PUBLISHED_REPEATS))
        seen = {(t["scenario"], t["task_id"], t["repeat"]) for t in self.trials}
        self.assertEqual(len(seen), len(self.trials), "duplicate (arm, task, repeat) cell")
        self.assertEqual(len(seen), len(ARMS) * len(DEV_TASKS), "the matrix is not balanced")

    def test_the_holdout_was_not_spent(self):
        self.assertEqual([t for t in self.trials if t.get("holdout")], [])
        self.assertEqual(sorted({t["task_id"] for t in self.trials}), sorted(DEV_TASKS))

    def test_every_trial_is_completed_and_valid(self):
        self.assertEqual({t["status"] for t in self.trials}, {"completed"})
        self.assertEqual({t["valid"] for t in self.trials}, {True})
        self.assertEqual({r["exit_code"] for r in self.runs}, {0})

    def test_arms_resolve_to_four_distinct_config_hashes(self):
        by_hash = {t["config_hash"]: t["scenario"] for t in self.trials}
        self.assertEqual(len(by_hash), len(ARMS), "resume-key collision between arms")
        self.assertEqual(sorted(by_hash.values()), sorted(ARMS))

    def test_published_spend_matches_the_run_records(self):
        total = sum(r["cost_usd_est"] for r in self.runs)
        self.assertAlmostEqual(total, PUBLISHED_SPEND_USD, places=4)


class TheCutDecision(unittest.TestCase):
    """The two facts SS1.7's verdict on claim 6 turns on."""

    def setUp(self):
        _, self.trials = load()
        self.by = {(t["scenario"], t["task_id"]): t["verifier_results"] for t in self.trials}

    def test_note_only_totals_are_as_published(self):
        for arm, expected in PUBLISHED_NOTE_ONLY.items():
            k = n = 0
            for crit in NOTE_ONLY:
                for task in DEV_TASKS:
                    v = self.by[(arm, task)].get(crit)
                    if v is None:
                        continue
                    n += 1
                    k += bool(v)
            self.assertEqual((k, n), expected, f"note-only total moved for {arm}")

    def test_the_note_only_class_was_exercised(self):
        """The cut rule's second row -- 'no arm ever fails, so no power' -- must not fire."""
        failures = [
            (t["scenario"], t["task_id"], c)
            for t in self.trials
            for c, v in t["verifier_results"].items()
            if c in NOTE_ONLY and not v
        ]
        self.assertTrue(
            failures, "the deciding class was pre-satisfied; the report says it was not"
        )

    def test_b_to_c_discordance_is_as_published(self):
        """Only discordant pairs carry information; 5 of them cap the read at p = 0.0625."""
        b_only = c_only = 0
        for crit in NOTE_ONLY:
            for task in DEV_TASKS:
                vb = self.by[("b-vnext-full", task)].get(crit)
                vc = self.by[("c-vnext-core", task)].get(crit)
                if vb is None or vc is None:
                    continue
                b_only += bool(vb) and not bool(vc)
                c_only += bool(vc) and not bool(vb)
        self.assertEqual((b_only, c_only), PUBLISHED_BC_DISCORDANT)
        self.assertLess(
            b_only + c_only,
            6,
            "6 discordant pairs is the minimum for an exact p <= .05; if the ledger now "
            "carries at least that many, the cut contrast is newly readable and the report "
            "owes a revision",
        )

    def test_the_a10_half_of_the_class_is_unscored_on_every_dev_task(self):
        """SS1.4: `enforcement_overclaims_absent` exists only on the sealed repair task."""
        scored = [
            t for t in self.trials if "enforcement_overclaims_absent" in t["verifier_results"]
        ]
        self.assertEqual(scored, [])

    def test_the_integrity_tripwire_did_not_fire_and_no_trial_was_excluded(self):
        integrity = (
            "no_self_certification",
            "anchors_point_at_staged_files",
            "defect_not_masked",
            "staged_tree_untouched",
        )
        for t in self.trials:
            vr = t["verifier_results"]
            self.assertTrue(vr.get("spec_written"), f"{t['scenario']}/{t['task_id']} wrote no spec")
            for c in integrity:
                if c in vr:
                    self.assertTrue(vr[c], f"integrity trip: {t['scenario']}/{t['task_id']}/{c}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
