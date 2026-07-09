# humblepowers 0.4.0 vs superpowers — the re-run that reversed v1

**Date:** 2026-06-15 · **Bank:** `humble-vs-super-v2` · **Trials:** 60 (3 arms × 4 tasks × 5 repeats),
60/60 completed, 0 infra errors · **Cost:** ≈ $30 (token×price estimate) · **Ledger:**
`ledger/humble-vs-super-v2.jsonl` · **Scorecard:** `report/scorecard-humble-vs-super-v2.md`

> **Corrected (2026-06-16):** the n=45 powered confirmatory found this report's quality gap
> (humble 100% > super 80%) was n=10 noise — humble ≈ super on test-discipline, overlapping CIs.
> The cost edge stands. See `2026-06-16-humble-vs-super-powered-confirmatory.md`.

> Companion to the v1 report (`docs/reports/2026-06-14-humblepowers-vs-superpowers.md`), which carries
> the full design, methodology, blindness model, and the regression-test "swap" verifier. This document
> reports only what the re-run with **humblepowers 0.4.0** changed.

## TL;DR

In v1, **humblepowers 0.3.1 lost** the head-to-head: it wrote a regression test only 60% of the time
(stack arm) versus superpowers' 100%, and there was *no* clean efficiency win to offset it. The v1
feedback predicted that *if humblepowers closed that discipline gap it would Pareto-dominate*, because its
cost gap is structural (smaller skill corpus), not test-driven.

**humblepowers 0.4.0 closed the gap — and the verdict flipped.** On `humble-vs-super-v2`, `stack-humble`
(0.4.0 in the common stack) is the **sole Pareto-optimal arm**: it has the *highest* quality **and** the
*lowest* cost, tokens, turns, and wall-clock of the three — it strictly dominates both superpowers
configurations. The quality edge is directional (n=10 on the one criterion that moves; CIs overlap); the
**cost edge is robust** (a systematic ~16–20% across all 20 trials/arm).

## What changed from v1

| | v1 (`humble-vs-super-v1`) | v2 (`humble-vs-super-v2`, this run) |
|---|---|---|
| humblepowers | 0.3.1 | **0.4.0** (adds `planned-execution`; foregrounds red-green TDD + evidence-before-claims verification in dispatch) |
| Arms | bare · humble-only · super-only · stack-humble · stack-super | **stack-humble · super-only · stack-super** |
| Tasks / fixtures / verifier | — | identical (byte-for-byte frozen copy of v1's bank) |

A **separate v2 bank** was used deliberately: `fathom report` aggregates by arm *name* with no
`dataset_version` filter, so running 0.4.0 into v1's ledger would have silently blended it into the same
`stack-humble` column as the 0.3.1 results. v1 is preserved untouched as the 0.3.1 baseline. `bare` was
dropped (its 0% floor is established by v1) and `humble-only` was dropped (humblepowers is designed to run
*within* its stack, so the isolated arm under-represents it). The matched contrast is **stack-humble vs
stack-super**; `super-only` is the un-stacked superpowers reference.

## Results

### Quality — still one discriminating criterion, but it now favors humble

10 of 11 verifier criteria sat at **100% across all three arms** (the bank ceilings on correctness, as in
v1). The whole quality signal is `regression_test_present` — did the agent add a test that fails on the
planted bug and passes on the fix (n=10/arm, the two bug-fix tasks × 5):

| Criterion | stack-humble (0.4.0) | stack-super | super-only |
|---|---|---|---|
| fix_correct, no_regression, tests_present, all feature criteria | 100% | 100% | 100% |
| **regression_test_present** | **100% (10/10)** | **80% (8/10)** | **80% (8/10)** |
| **all-criteria-true pass rate (n=20)** | **100%** | **90%** | **90%** |
| Wilson 95% CI (pass rate) | [83.9%, 100%] | [69.9%, 97.2%] | [69.9%, 97.2%] |

### Economy & efficiency (per trial, n=20/arm)

| Arm | $/trial | Total tok/trial | Turns | Wall (s) | Quality / 100k tok |
|---|---|---|---|---|---|
| **stack-humble (0.4.0)** | **$0.458** | **287.8k** | **10.0** | **64.7** | **0.35** |
| stack-super | $0.545 | 358.2k | 11.9 | 74.7 | 0.25 |
| super-only | $0.517 | 348.3k | 12.4 | 83.4 | 0.26 |

stack-humble is **~16% cheaper** than stack-super and ~11% cheaper than super-only, uses **~17–20% fewer
tokens** and fewer turns, finishes faster, and delivers **~40% more quality per token** — while scoring
*higher* on the only criterion that discriminates. (USD is a token×price estimate; subscription auth bills
the plan, so tokens/turns are the primary economy currency — see v1 report / defect D2.)

### Pareto frontier (hand-computed)

An arm is Pareto-optimal if no other arm has ≥ quality **and** ≤ tokens. stack-humble has the highest
quality **and** the lowest tokens, so it dominates both superpowers arms outright:

**True non-dominated frontier = { stack-humble }.**

> The scorecard's `★` also flags `super-only`; that is the known fathom efficiency-flag bug (it marks any arm
> that dominates *someone* — super-only only dominates stack-super — rather than the truly non-dominated
> set). Trust the hand-computed frontier, not the `★`. (Filed: fathom feedback, efficiency-view Pareto flag.)

## v1 → v2: the reversal on the discriminating criterion

| `regression_test_present` | v1 (0.3.1) | v2 (0.4.0) |
|---|---|---|
| stack-humble | **60%** | **100%** |
| stack-super | 100% | 80% |
| super-only | 90% | 80% |

humblepowers moved **+40 points** within-tool (60% → 100%). A 40-point gap in *superpowers'* favor (v1:
100 vs 60) became a 20-point gap in *humblepowers'* favor (v2: 100 vs 80). The super arms drifting to 80%
this run is within n=10 noise (their true rate is ~80–100%); the durable, defensible shift is the
**humblepowers within-tool jump** — its v1 weakness is gone.

## Interpretation — mechanism

v1's loss was humblepowers' calibration doctrine working *too* aggressively: on a small, well-specified
bug it judged the TDD/verification skill "not worth loading" and shipped the fix without a regression
test ~half the time. 0.4.0's changes (a dedicated `planned-execution` skill; TDD and
evidence-before-claims verification surfaced more strongly in dispatch) appear to have re-tuned exactly
that decision — the agent now leaves the regression test behind the fix while *keeping* the smaller corpus
that gives humblepowers its structural token/cost advantage. That combination is precisely what flips a
quality-vs-cost trade into Pareto dominance. **This run validates the v1 craft-collection feedback's
central prediction.**

## Threats to validity (unchanged structure from v1; read these before acting)

1. **The quality edge is directional, not conclusive.** Everything rests on `regression_test_present` at
   **n=10/arm**; 100% vs 80% gives overlapping Wilson CIs ([72%, 100%] vs [49%, 94%]). What is *robust* is
   the within-tool jump (60→100) and the cost advantage; what is *not yet proven* is a statistically clean
   quality win over superpowers. A confirmatory run would need ~30–50 bug-fix trials/arm.
2. **Same ceiling.** 10/11 criteria at 100% — the bank does not stress correctness. The verdict is narrow
   ("does the agent leave a regression test, at what cost"), not a broad quality measurement. The harder-bank
   follow-up (STATUS next-step 1) still stands.
3. **Cost is a token×price estimate** on subscription auth (total_cost_usd = 0); the ~16–20% gap is real in
   tokens/turns regardless of the dollar conversion.
4. **Single model, single host, one run** (opus-4-8, Windows). No holdout was run (sealed
   `fix-cache-eviction-bug` excluded by design).

## Conclusion

On `humble-vs-super-v2`, **humblepowers 0.4.0 (in its stack) is the better choice on every axis measured**:
it writes the regression test at least as reliably as superpowers (100% vs 80% here) while costing ~16–20%
less in tokens and dollars and finishing faster — the sole Pareto-optimal arm. The v1 verdict ("superpowers
more effective, at a cost premium, no clean efficiency win for humblepowers") is **reversed** by the 0.4.0
release. Caveat the quality half as directional (n=10); bank the cost half as robust. The strongest
follow-up remains a harder bank, plus a higher-n confirmatory pass on the bug-fix tasks if a
statistically-clean quality claim is wanted.

## Appendix — reproducibility

```sh
uv run fathom smoke                                                                  # 8/8
uv run fathom run humble-vs-super-v2 --scenarios-dir scenarios/humble-vs-super-v2 --repeats 5
uv run fathom report humble-vs-super-v2
```

- Bank/instrument: `tasks/humble-vs-super-v2/` (frozen copy of v1's tasks; own vendored plugins —
  humblepowers 0.4.0, superpowers v5.1.0 @ `6fd4507`, engineering-discipline 0.1.2, session-workflow
  0.2.2). Provenance + hypothesis: `tasks/humble-vs-super-v2/V2_NOTES.md`.
- superpowers + the held-constant stack are byte-identical to v1's, so their `config_hash` matches v1 — the
  only intended treatment change is the humblepowers version.
- Ledger `ledger/humble-vs-super-v2.jsonl` (append-only); regenerate the scorecard any time with
  `fathom report`.
