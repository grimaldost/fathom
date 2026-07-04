# humble-vs-super — the harder-bank retune and the powered confirmatory

**Date:** 2026-06-16 · **Banks:** `humble-vs-super-v3` (correctness-trap; powered to n=45/arm),
`humble-vs-super-v4` (non-local root-cause; calibration pilot) · **Spend:** ≈ $80 across two
pilots + one 162-trial powered matrix (token×price estimate; subscription-billed) · **Ledgers:**
`ledger/humble-vs-super-{v3,v4}.jsonl` · **Scorecards:** `report/scorecard-humble-vs-super-{v3,v4}.md`

> Sequel to the v2 report (`docs/reports/2026-06-15-humblepowers-0.4.0-vs-superpowers.md`).
> Goal this round (the two STATUS next-steps, fused): build a **harder bank** where correctness
> itself discriminates, and run a **higher-n confirmatory** to turn v2's directional humble≥super
> into a powered verdict. Both questions are answered — one negatively, one conclusively.

## TL;DR

1. **The harder-bank goal failed — and that is a real, replicated finding.** Two independent
   "harder" designs (v3: documented-contract edge cases; v4: non-local root cause) **both
   ceilinged on correctness**: opus-4-8 with *no* plugins (`bare`) wrote correct fixes on
   **100%** of trials, across every correctness criterion, at n=45. On self-contained,
   deterministically-verifiable Python tasks, these process disciplines **do not move opus's raw
   correctness** — they move **test/verification hygiene** (leaving a regression test).
2. **The powered confirmatory corrects v2's quality claim.** At n=45/arm, humble and superpowers
   are **statistically tied** on the discriminating axis (`regression_test_present`):
   stack-humble 100%, super-only 97.8%, stack-super 95.6% — overlapping Wilson CIs. **v2's
   "humble 100% vs super 80%" was small-n (n=10) noise.** Humble is *not* better than superpowers
   on quality; both are at the ceiling.
3. **What survives from v2 is the cost edge — and it is robust.** stack-humble is the most
   efficient disciplined arm on every meaningful axis and **Pareto-dominates both superpowers
   arms**. The v2 bottom line ("humble 0.4.0 is the best choice") holds at high n, but the
   *reason* is **cost, not quality**.

## Part 1 — the harder-bank retunes and the correctness ceiling

v1/v2 ceilinged because their bug reports spoon-fed the fix. v3 and v4 attacked that two ways:

| bank | mechanism (discipline targeted) | result (bare, pilot) |
|------|---------------------------------|----------------------|
| **v3** | documented-but-unhinted edge cases — symptom names one case, the docstring documents the rest (whitespace/keep-first; adjacency+containment; penny-fairness). Rewards reading the whole contract / TDD enumeration. | every correctness criterion **100%** for bare |
| **v4** | **non-local root cause** — an innocent-looking shared helper is the real bug, the symptom surfaces in a consumer, a second consumer + edge cases defeat consumer-local band-aids. Rewards root-cause-tracing. | every correctness criterion **100%** for bare |

In v4, opus-bare **did not take the band-aid the design baited** — it traced symptom → shared
helper and fixed the root cause every time, passing both consumer criteria (the
`TestBandAidFailsSecondConsumer` validation proved a band-aid *would* fail, so this is opus being
thorough, not a lenient verifier). Two clean replications support the finding:

> **On small-to-medium, self-contained, deterministically-verifiable Python tasks, opus-4-8's
> correctness is at the ceiling regardless of these process disciplines.** What the disciplines
> reliably move is test/verification hygiene, captured by `regression_test_present` (bare 0%,
> disciplined ~100% — fully separated).

This is consistent across v2 → v3 → v4 and bounds what the humble/super disciplines can change on a
highly capable base model. The pilot-gate did its job: ~$16 of pilots established this before any
powered spend was committed to a correctness axis that does not move.

## Part 2 — the powered confirmatory (v3, n=45/arm, 180 trials, 0 infra errors)

Powering v3 (3 bug-fix tasks × 15 repeats × 4 arms) gives n=45/arm on the discriminating criterion
and n=45 on each correctness criterion — enough to settle both the v2 quality question and the
correctness ceiling at scale.

### Correctness ceiling — definitive

All eight correctness criteria, **100% across all four arms** (bare included), 0 failures in 180
trials. The ceiling is not a small-n artifact.

### The discriminating axis (`regression_test_present` = all-criteria pass, since correctness is 100%)

| Arm | Pass | Wilson 95% CI |
|-----|------|---------------|
| bare | **0/45 (0.0%)** | [0.0%, 7.9%] |
| stack-humble | **45/45 (100%)** | [92.1%, 100%] |
| super-only | 44/45 (97.8%) | [88.4%, 99.6%] |
| stack-super | 43/45 (95.6%) | [85.2%, 98.8%] |

- **bare is conclusively separated** from every disciplined arm (CI tops out at 7.9%, disjoint
  from the disciplined arms' floors ≥ 85%). The discipline floor — 0% → ~100% — is rock-solid.
- **The three disciplined arms are statistically tied** (CIs overlap on [92.1%, 98.8%]).
  stack-humble's clean 45/45 vs super's 1–2 misses out of 45 is within noise. **v2's humble>super
  quality gap does not replicate.**

### Economy & efficiency (per trial, n=45)

| Arm | Quality | Total tok (incl. cache) | Turns | Wall (s) | Est. USD |
|-----|---------|-------------------------|-------|----------|----------|
| bare | 0% | 177k | 7.3 | 35.2 | $0.217 |
| **stack-humble** | **100%** | **288k** | **9.2** | **48.3** | **$0.390** |
| super-only | 97.8% | 329k | 11.8 | 56.7 | $0.428 |
| stack-super | 95.6% | 356k | 11.6 | 56.4 | $0.482 |

stack-humble is **~9–19% cheaper (USD)**, uses **~21% fewer turns**, **~12–19% fewer total
tokens**, and finishes faster than the superpowers arms — at tied-best quality.

### Pareto frontier (hand-computed; the scorecard `★` is the known fathom "dominates-someone" bug)

On quality vs **total tokens** and quality vs **USD**, stack-humble has the highest quality **and**
the lowest cost of the disciplined arms, so it dominates both superpowers arms:

**True non-dominated frontier = { bare, stack-humble }.** stack-super is dominated by both other
disciplined arms; super-only is dominated by stack-humble.

> Transparency: on the **in+out-only** token subtotal (excluding cache), super-only is leanest
> (8.9k vs humble's 11.0k) because its smaller plugin corpus means a shorter system prompt — so on
> that one metric super-only joins the frontier. On **total** tokens (cache is the dominant
> volume), turns, wall-clock, and USD, stack-humble dominates. The verdict holds on every metric
> except that single cache-excluded subtotal.

## The refined verdict (vs v2)

| Axis | v2 (n=10) | v3 powered (n=45) |
|------|-----------|-------------------|
| Quality (`regression_test_present`) | humble 100% > super 80% — "humble better" (directional) | humble 100% ≈ super 95.6–97.8% — **tied at ceiling**; v2 gap was noise |
| Correctness | ceilinged (1 criterion of 11 moved) | **ceilinged, definitively** (0/180 failures); replicated in v3 + v4 |
| Cost | humble ~16–20% cheaper (directional) | humble ~9–19% cheaper, ~21% fewer turns — **robust** |
| Pareto | stack-humble sole-optimal | **stack-humble dominates both super arms** (via cost) |

**v2 said humble 0.4.0 reversed the verdict and was Pareto-dominant. The powered run upholds the
bottom line — stack-humble is the best disciplined choice — but corrects the mechanism: it wins on
cost, not quality. Humble and superpowers are equally good (near-perfect) at leaving a regression
test; humble just gets there with a smaller corpus, fewer turns, and lower cost.** The v2 "quality
edge" was the kind of small-n artifact higher n exists to catch.

## Threats to validity

1. **Single discriminating axis.** Correctness ceilings, so the entire quality signal is
   `regression_test_present`. The verdict is narrow ("does the arm leave a regression test, at what
   cost"), not a broad quality measurement. This is now a *demonstrated property* of opus on this
   task class, not a bank-authoring shortfall — but a genuinely broad quality axis would need
   either a much harder task class (large multi-file navigation, where one-shot context fails) or
   the dark pairwise judge (architecture/readability beyond mechanical checks).
2. **Cost is a token×price estimate** on subscription auth (`total_cost_usd = 0`); the ~9–19% gap
   is real in tokens/turns/wall regardless of the dollar conversion.
3. **Single model, single host.** opus-4-8 on Windows. A weaker base model might *not* ceiling on
   correctness — the discipline plugins could move correctness there. This finding is specific to a
   highly capable base model.
4. **n=45 ties are "indistinguishable", not "proven equal".** A 2–5 point true difference between
   humble and super could exist below this resolution; what is ruled out is the v2-sized (20-point)
   gap.

## Conclusion

The harder-bank goal produced a clean negative finding — opus correctness can't be discriminated by
these disciplines on self-contained tasks — replicated twice. The powered confirmatory then settled
the v2 question: **humble 0.4.0 and superpowers are tied at the quality ceiling; humble's durable
advantage is cost (Pareto-dominant on total tokens, turns, wall-clock, and USD).** Keep v2's
bottom-line recommendation (humble 0.4.0 is the better choice), but state the reason precisely: not
because it writes better code or better tests than superpowers, but because it matches superpowers'
near-perfect test-discipline with a leaner corpus at materially lower cost.

## Appendix — reproducibility

```sh
uv run fathom smoke                                                                       # 8/8
# v3 powered confirmatory (pilot trials resume in):
uv run fathom run humble-vs-super-v3 --scenarios-dir scenarios/humble-vs-super-v3 --repeats 15
uv run fathom report humble-vs-super-v3
# v4 non-local pilot (calibration):
uv run fathom run humble-vs-super-v4 --scenarios-dir scenarios/humble-vs-super-v4-pilot --repeats 4
uv run fathom report humble-vs-super-v4
```

- Instruments: `tasks/humble-vs-super-v3/` (3 correctness-trap tasks; `V3_NOTES.md`),
  `tasks/humble-vs-super-v4/` (2 non-local root-cause tasks; `V4_NOTES.md`). Both reuse
  `bugfix_verify.py` byte-identical and mount the same vendored plugins as v2 (identical
  `config_hash` for the shared arms).
- Validation: `tests/test_verify_humble_super_v3.py`, `tests/test_verify_humble_super_v4.py` prove
  each task's naive/band-aid fix fails its targeted criterion and the buggy fixture fails the hidden
  criteria — so the verifiers discriminate by construction (399 tests pass).
- Ledgers append-only; regenerate scorecards any time with `fathom report`.
