# Is the series engine useful? — what's known, and the v2 study that would settle it

- **Date:** 2026-07-01. Companion to the recalibration run-state + report.

## Two efficiency questions — where each actually stands

**Q1 — Is the ENGINE (decompose → gate → review) worth it vs plain Claude?** (the usefulness question)
- **Measured once** (2026-06-10, the series-engine bank, engine vs bare, n=6/arm): on tasks below the coordination
  threshold, **pure overhead** — the series engine spent ~4.6× tokens, ~4× wall-clock, 8 sessions/trial, for **+0.00
  quality** (bare passed 100%). Consistent with the series engine's own doctrine ("below the blast-radius/coordination
  threshold, orchestration is overhead"). Verdict: *don't use the series engine for tasks this small* — NOT *the series engine
  is worthless*.
- The value-side (does it PAY OFF on hard work?) is **untested and hard to measure cleanly**. Two confounds
  (ADR-0009 D1/D6): the arms must be capability-equalized, and fathom grades self-contained **staged subtrees**
  while part of the engine's real gate value lives in the **whole repo**. And the v1 bank has a **ceiling
  effect** (bare aces everything) so quality can't discriminate.

**Q2 — Does tier-ROUTING save cost (within-engine, `pp-native-tier` vs `pp-fixed-opus`)?**
- **Designed, never run** (ADR-0009): blocked on tier heterogeneity in the anchors, and the `tier_routing=native`
  executor code is **unbuilt**. With **Sonnet 5** it's degenerate anyway — routing collapses to "default mid
  (Sonnet 5), escalate rarely," so the win is simply *not pinning Opus*, not per-PR routing. The calibration
  run already showed this direction.

## Consolidated practical guidance for TODAY (actionable without more runs)
- **Routing is low-value with Sonnet 5.** Lean **mid-default (Sonnet 5), Opus as escalation.** The strong band
  trends escalation-only (calibration: Sonnet 5 hit 80% on the one task that needed capacity, Opus 100%).
- **The engine earns its keep only on genuinely governed / hard / multi-task work** — its doctrine holds; on
  easy work it is measured overhead.
- These are already reflected in the shipped mid→Sonnet 5 bump + the `model-tiers` calibration note.

## The v2 study that would settle Q1 (the only thing that adds real signal)
Requires two things the v1 bank lacks:
1. **A bank where `bare` FAILS sometimes** (bare pass rate strictly inside (0,1)). With Sonnet 5 near-Opus,
   difficulty must be high: long-horizon, cross-module invariants, subtle correctness, larger fixtures.
2. **A defect-escape metric, not just final pass.** The engine's claimed value is catching defects a plain
   session SHIPS. Measure: fraction of `bare` runs that self-report "done" but fail hidden acceptance —
   the escapes the gate+review would have caught.

**Proposed shape**
- **Bank** (the series-usefulness bank): 3 hard multi-PR tasks, difficulty **probe-tuned** so bare Sonnet 5 fails
  ~30-60%. Property/parity/invariant checks in `verify.py`.
- **Arms:** `bare-sonnet5`, `bare-opus`, `pp-series-sonnet5` (engine, mid-default), `pp-series-opus`. (Skip
  `pp-native-tier`: low-value with Sonnet 5 and needs unbuilt fathom code — chosen arms use only the existing
  `single-session` / `series` strategies with a model pin.)
- **Metrics:** final acceptance pass rate per arm; **defect-escape** rate; economy (tokens / sessions / $ est).
- **Confound mitigations:** equalize tool access (bare gets the same `Bash(python:*)` self-check the engine
  has — the v1 `bare` arm already did); keep the graded diff self-contained so both arms grade identically;
  state explicitly that this measures the decompose+gate+review **discipline on self-contained tasks** (a fair
  subset of the engine's value), NOT its whole-repo gate value.
- **Verdict it yields:** "on hard governed work, the series engine buys **+X% correctness** / prevents **Y% defect-escape**
  at **Z× cost**" — quantifies where the engine crosses from overhead to value. Three clean outcomes (pays off /
  pays off but a tier under-provisions / both arms floor → task too hard), all actionable.

## Cost & build
- **Build:** author the hard bank (fixtures + `verify.py` + `series.toml` + prompts + `review.md` per task) —
  the bulk of the effort. No new fathom code for the chosen arms.
- **Difficulty probe:** `bare-sonnet5` on candidate tasks, n=5 ≈ $2-4/task; ~2-3 authoring iterations → **~$25**.
- **Full matrix:** 4 arms × 3 tasks × n=5 = 60 trials; the `pp-series` arms (~8 sessions, long) dominate →
  **~$60-150** est list-price (≈$0 real under subscription auth). Both `--max-budget-usd` capped.
- **Recommended staged budget:** ~$25 authoring+probe (prove we can make bare fail with Sonnet 5), then a
  ~$150 ceiling for the matrix once the bank discriminates.

## Honest bottom line
The runs alone will NOT hand you a clean "the series engine is/ isn't useful" — the honest measurement is confounded and
the informative half needs a purpose-built hard bank. What IS settled: **overhead on easy work; routing is
low-value with Sonnet 5; use the engine on hard governed work, mid-default + Opus-escalation.** The v2 study is
a real (bounded) investment that converts the value-side from doctrine into a number.
