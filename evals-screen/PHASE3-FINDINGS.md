# Phase-3 findings — does the gate generalize? (2026-07-25)

165 completed trials, $36.82, haiku-4.5 + sonnet-5. Blind analysis against
`docs/design/2026-07-25-phase3-gate-generalization-prereg.md`, applied verbatim.

## Verdicts

| hypothesis | verdict |
|---|---|
| **H1** — discipline-worded gate lifts footprint on debugging and data | **INCONCLUSIVE** (1 of 4 cells ≥ +0.15; 2 cells ≤ +0.05) |
| **H2** — the prescriptive-over-triggers gap replicates on new disciplines | **REFUTED** (gap +0.00 on all four cells) |

### Footprint

| discipline / tier | bare-sub | disc-sub | presc-sub |
|---|---|---|---|
| debug / haiku | 0.78 | 0.89 (+0.11) | 1.00 |
| debug / sonnet | 0.78 | 1.00 (+0.22) | 1.00 |
| data / haiku | 0.56 | 0.56 (+0.00) | 0.44 |
| data / sonnet | 1.00 | 1.00 (+0.00) | 0.89 |

### Over-scope on trivial edits

**0.00 in every cell** — every arm, both disciplines, both tiers. (The `bare-sub`
null-debug baseline is the one banked in Phase 2: same arm, bank, tasks and tiers,
deliberately not re-run; the analyzer ingests it explicitly.)

## What this means — the Phase-2 headline is now narrower

Phase 2 found, on verification-before-completion, that a prescriptive gate ("add a
regression check now") bought footprint at a 0.58 over-scope cost while a
discipline-worded gate ("are you confident, or assuming?") cost nothing. I proposed
promoting that into craft's `skill-authoring` doctrine as a general
**discipline-vs-artifact register rule**, and pre-registered that H2 must confirm
before promoting it.

**H2 refuted it.** The prescriptive gates for debugging and data over-triggered
exactly zero times. Prescriptive wording is therefore **not** generally harmful, and
the rule must not be written into doctrine as stated. Per the pre-registration, the
Phase-2 result is downgraded to **verification-specific**.

### The better explanation (hypothesis, not yet tested)

Compare what each prescriptive gate actually demanded:

- verification: *"add a regression check now"* — an artifact that is **producible
  regardless of applicability**. You can always write a test for a docstring bump.
- debugging: *"trace the fault to the shared helper, patch it there, update every
  caller"* — on a trivial edit there is no fault and no shared helper. The
  instruction has **no referent**, so it cannot be over-performed.
- data: *"run the pipeline, print the totals, reconcile line by line"* — running and
  printing creates **no new defs or files**, so `over_scope` cannot see this work
  even if it happened.

So the risk is not the prescriptive *register*; it is prescribing an artifact that is
**always producible** — and, for the data arm, the refutation is partly
**metric-bound**: `over_scope` measures extra defs/files and is blind to wasted
runtime effort. A cleaner test would prescribe an always-producible artifact for a
non-verification discipline, and add a metric that can see wasted work.

## Second-order observation (flagged, not claimed)

`presc-sub` **reduced** data footprint (0.44 vs 0.56 haiku; 0.89 vs 1.00 sonnet).
Prescribing a specific procedure may crowd out the actual correctness work. n=9 per
cell — this is a hypothesis worth a targeted test, not a finding.

## Where the subagent gate now stands

The mechanism is real but its value is **discipline-dependent**:

| discipline | discipline-worded gate lift |
|---|---|
| verification-before-completion | **+0.56 / +0.56** (Phase 2) |
| systematic-debugging | +0.11 / +0.22 |
| data / observable verification | +0.00 / +0.00 |

Verification is where an always-on subagent gate pays. That is also the discipline
whose whole content is "check before declaring done" — the one thing a subagent, cut
off from the parent's judgment, most reliably skips (Phase 2: delegation drops
footprint from 0.48/0.59 to 0.44). Data shows no headroom on sonnet (bare already
1.00) and no effect on haiku.

## Disposition

1. **Do not promote the register rule** into `skill-authoring`. Craft feedback
   finding #1 is revised accordingly (see the corrected report).
2. **Ship the gate for verification only**, not as a general discipline-delivery
   mechanism. Scope the convoy stage design (track E) the same way: mandate
   verification, and do not generalize the claim to other disciplines.
3. **Open question worth one cheap test:** is over-triggering driven by
   "always-producible artifact" rather than by register? A prescriptive gate demanding
   an always-producible artifact for debugging would settle it.

## Provenance
`ledger-phase3/*.jsonl` (165 completed) + `ledger-phase2/null-*.jsonl` (borrowed
`bare-sub` FP baseline) × `scripts-phase2/analyze_phase3.py`. Gate plugin:
`scenarios/phase3-hooks/subagent-gate-multi/` (one plugin, `GATE_DISCIPLINE` ×
`GATE_REGISTER`). Cost $36.82.
