# model-tier-v1 — difficulty-ladder bank for model-tier calibration

A difficulty-ladder bank for a model-tier calibration study: eight bug-fix / small-feature
tasks spread across three difficulty bands, each scored by the author for the *cheapest*
model tier expected to clear it. The arms in this study are **model tiers** (weak / mid /
strong); the ladder lets the matrix show where each tier's capability ceiling falls.

Each task ships a buggy package plus a shipped test suite that passes on the buggy source
(it does **not** cover the planted bug). The verifier (`verify.py`) emits a flat
`{criterion: bool}` JSON object: an easy **anchor** criterion, one or more **hard**
(capability-gated) criteria listed in `[verify].hard_criteria`, plus `no_regression` and
`regression_test_present`. The hard criteria are the discriminating signal — read them in
the scorecard's Per-Criterion Pass Rates table, not just the headline pass-rate.

Tier mapping used for `author_score`: **0-25 → weak / Haiku**, **26-55 → mid / Sonnet**,
**56-100 → strong / Opus**.

## Predicted-signal

| task | author_score | predicted tier | band |
|------|-------------:|----------------|------|
| `fix-clamp` | 10 | weak / Haiku | low |
| `fix-titlecase` | 22 | weak / Haiku | low |
| `feature-csv-coalesce` | 40 | mid / Sonnet | mid |
| `fix-interval-merge` | 45 | mid / Sonnet | mid |
| `fix-dedup-records` | 50 | mid / Sonnet | mid (holdout) |
| `fix-money-split` | 55 | mid / Sonnet | mid |
| `fix-nonlocal-parse` | 70 | strong / Opus | high |
| `fix-nonlocal-urlkey` | 74 | strong / Opus | high |

Baseline expectation per band:

- **low** ⇒ all three models pass (the Haiku ceiling reaching these confirms the weak tier
  suffices for trivial single-function fixes).
- **mid** ⇒ Haiku is mixed (clears the anchor, trips at least one hard criterion on the
  harder rungs), Sonnet passes.
- **high** ⇒ Haiku fails the hard criteria (it patches the symptom site and leaves the
  second consumer / call site broken), Opus passes by fixing the shared root cause.

## Spread gate

- **≥ 2 tasks in each band:** `[0-25]` = fix-clamp (10), fix-titlecase (22) → **2**;
  `[26-55]` = feature-csv-coalesce (40), fix-interval-merge (45), fix-dedup-records (50),
  fix-money-split (55) → **4**; `[56-100]` = fix-nonlocal-parse (70),
  fix-nonlocal-urlkey (74) → **2**. All three bands satisfy the ≥ 2 minimum.
- **Boundary rungs within ±5 of the band edges:** the 25 weak/mid edge is probed by
  `fix-titlecase` = 22 (Δ3); the 55 mid/strong edge is probed by `fix-money-split` = 55
  (Δ0, sitting exactly on the edge). These two rungs sharpen the tier boundaries the study
  is trying to locate.

> Caveat: the ≥2-per-band claim above holds under the **author** scores. Under the
> reconciled rubric scores (next section) the weak band is thinner and the 55 boundary is
> only bracketed — see "Independent re-rating & reconciliation".

## Independent re-rating & reconciliation (§2)

A second, **blind** rater (no access to the author scores) re-scored each task with the same
pinned `series-engine:pr-prompt-scorer` rubric (the series engine 0.8.1 @ `1c2748f`). Final score = the
average of the two; `scores.toml` is the machine-readable source the report consumes.

| task | author | blind rater | final | predicted tier |
|---|--:|--:|--:|---|
| `fix-clamp` | 10 | 25 | 18 | weak |
| `fix-titlecase` | 22 | 30 | 26 | mid |
| `feature-csv-coalesce` | 40 | 43 | 41 | mid |
| `fix-interval-merge` | 45 | 33 | 39 | mid |
| `fix-dedup-records` | 50 | 30 | 40 | mid (holdout) |
| `fix-money-split` | 55 | 33 | 44 | mid |
| `fix-nonlocal-parse` | 70 | 61 | 65 | strong |
| `fix-nonlocal-urlkey` | 74 | 61 | 67 | strong |

**Tier agreement: 7/8.** Only `fix-titlecase` differs (author weak 22 vs rater mid 30) —
exactly one band, at the 25 boundary, within the §2 "≤ one band" tolerance (no recut).

**Spread-gate outcome (honest, not a clean pass).** The blind rater independently
*confirmed the pre-mortem's FM-3*: the rubric clusters the single-file bugfixes in the
low-mid 30s–40s and jumps to ~61 for the two cross-module root-cause tasks, structurally
avoiding the 55 boundary (the rubric's own worked examples are 5 / 48 / 91). Under the
reconciled scores:

- The three **tiers** are populated — weak = {clamp 18} (+ titlecase 26 as the weak/mid
  boundary rung); mid = {titlecase 26, interval 39, dedup 40 [holdout], csv 41, money 44};
  strong = {nonlocal-parse 65, nonlocal-urlkey 67} — so tier-level calibration (do weak/mid/
  strong tasks get the right model?) is testable.
- The **25 boundary** is probed (titlecase ≈ 26). The **55 boundary** is only *bracketed*
  (money 44 mid ↔ nonlocal 65 strong) — no task lands in 50–60, because the rubric does not
  produce boundary-scored tasks. The boundary-*placement* analysis is therefore coarse, and
  the **weak band is thin** (one solidly-weak task + one boundary task). Reported as a
  limitation (and itself a finding about the rubric), rather than forcing rubric-55 tasks the
  rubric avoids by construction.

## Holdout

`fix-dedup-records` is held out (`bank.toml` `holdout = ["fix-dedup-records"]`) — a mid-band
task reserved out of the tuning set.

## Pilot gate outcome (§9)

Pilot = `--repeats 2` over all 7 working tasks × 3 model arms = **42 trials** (all
completed, no errors, ~**$6**). Same-bank, so these count toward the full `--repeats 5`
matrix (resume, zero waste).

**GO predicate** (≥1 high-band hard criterion with Haiku ≤60% AND Opus ≥80%, n≥5):
`fix-nonlocal-parse` separates the tiers on BOTH hard criteria — `messages_quoted` and
`codes_quoted_tagged`: **Haiku 50% / Sonnet 50% / Opus 100%** (weak models patch the
symptom site; Opus fixes the shared root cause). At n=2 this is below the ≥5-trial bar and
the confusion matrix marks it *indeterminate* (CIs overlap), so the full n=5 matrix is run
to confirm.

**Discrimination summary (n=2):** 6 of 7 tasks CEILING — Haiku aces every hard criterion
on clamp, titlecase, interval-merge, csv-coalesce, money-split, and nonlocal-urlkey. This
is **not** the prior null-result ceiling: a weak model acing a mid/strong-scored task IS
the calibration signal — it means the mapping **over-provisions** (routes to a dearer tier
than needed). The confusion matrix is non-degenerate (1 on-diagonal, 5 over-provisioned,
1 indeterminate); the corrected Pareto shows **sonnet dominated by haiku** (equal quality,
higher cost).

**Decision: GO** to the full `--repeats 5` matrix — the bank delivers a real verdict
(over-provisioning + one genuine model-capability gradient at nonlocal-parse); n=5 confirms
it and resolves nonlocal-parse. **Caveat for the report:** the reused tasks turned out
easier-for-Haiku than their rubric scores implied (prompt-complexity ≠ model-difficulty,
the FM-N3 / v3-ceiling precedent), so the headline is "for this distribution the mapping
over-provisions," stated with the bank-easiness caveat.

**Effort layer:** the pilot shows headroom for effort to matter ONLY on nonlocal-parse
(every other task is at 100%). A targeted effort test (haiku-xhigh / sonnet-xhigh on the
high tasks) is run after the full matrix to probe the substitution question there; a full
effort cross is skipped (no headroom elsewhere).

## Authoring reference

These tasks follow the standard bug-fix anatomy:
`fixtures/` (the buggy package + a shipped suite that passes on the bug) is staged into the
candidate workspace; `original/` (the same buggy source, stashed, + the shipped tests) is
harness-side for the `regression_test_present` swap; `verify.py` reads only `argv[1]` and
shares the `bugfix_verify.py` helper in this bank dir. The two low tasks (`fix-clamp`,
`fix-titlecase`) were authored fresh for this bank; the other six were reused from the
`humble-vs-super-v1/v3/v4` banks with a `hard_criteria` array added to each `[verify]`.
