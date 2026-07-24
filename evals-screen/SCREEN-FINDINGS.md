# Stage-1 behavioral screen -- findings (2026-07-24)

168 trials, repeats=1, $20.26 ($0.121/trial). Pre-registered gates:
footprint-lift vs bare >= +2/6 per tier AND FP-lift (over_scope on null) <= +2/6.
**n=6 per cell -- this is an underpowered SCREEN by design; every number is a
noisy point estimate, a +1/+2 is one or two tasks. Read as signal, not proof.**

## Results (footprint = discipline applied; over_scope = false-positive)

### B-present (e1-*, Lane 2 prompt-time arms)
| arm | haiku | sonnet |
|---|---|---|
| bare | 2/6 | 3/6 |
| oracle (ceiling) | 4/6 (+2) | 5/6 (+2) |
| classifier-hint | 3/6 (+1) | **6/6 (+3)** |
| static-registry | 3/6 (+1) | -- |
| framing-4d | 3/6 (+1) | -- |
| gate-4a | 2/6 (+0) | -- |
| gate-placebo | 2/6 (+0) | -- |

### C-present (c-*, Lane 3 action-stream arms)
| arm | haiku | sonnet |
|---|---|---|
| bare | 3/6 | 3/6 |
| oracle (ceiling) | 3/6 (+0) | 3/6 (+0) |
| detector-nudge | 3/6 (+0) | -- |
| retrospective-gate | 4/6 (+1) | -- |

### null (over_scope, false-positive; lower is better, bare = 0/6 everywhere)
detector-nudge 1/6 (+1), retrospective-gate 1/6 (+1); every other arm 0/6.

### Pre-registered gate verdict
**Only `classifier-hint` [sonnet] promotes** (foot-lift +3, FP-lift +0). Every
other arm/tier: no.

## The findings, honestly

1. **The prior lead did NOT replicate.** In RG-2x2, the forced-applicability gate
   (4a) lifted footprint +5/12 per tier (75% vs 37.5%). Here, on the same e1 banks
   with the same forced-eval.md, `gate-4a` = 2/6, identical to bare 2/6 -- **zero
   lift** -- and its token-matched placebo is also 2/6. So the confound question is
   moot: the gate simply did not move footprint this time. Combined with the
   never-closed RG-2x2 confound, the evidence for "forced deliberation lifts
   discipline" is now WEAK. This is the rigor push paying off -- a plausible prior
   result failing under a cleaner, pre-registered, placebo-controlled run.

2. **One survivor, capability-gated:** `classifier-hint` on the STRONG tier
   (sonnet 6/6, +3, matching the oracle ceiling) -- but haiku +1 only. Consistent
   with E1's strong-tier classifier gradient. A strong-tier-only effect.

3. **Oracle lifts Band-B (+2) but NOT Band-C (+0), both tiers.** Clean band-model
   result: naming the right skill helps when the need is stated in the prompt
   (Band B), and does nothing when the need emerges mid-execution (Band C). The
   Band-C footprint looks capability-bound -- no prompt/hook intervention (oracle,
   nudge, gate) moved it.

4. **The action-stream (Lane 3) thesis did not pan out at the screen level.**
   detector-nudge +0 and retrospective-gate +1 on C-footprint, and each added +1
   over_scope on the null banks (a small false-positive cost). Net: no help, slight
   harm.

5. **Everything else is +0/+1** -- below the screen threshold. static-registry,
   framing-4d, gate: no robust lift.

## Caveats / threats

- **n=6 is tiny.** The gate non-replication could be regression to the mean
  (RG-2x2 overestimate) OR this run underestimating; the truth needs a POWERED
  re-run. But even the point estimate flipping from +5/12 to +0/6 is a real signal
  that the effect is not robust.
- Runs are on different days/possibly CLI versions; same model family (haiku-4.5 /
  sonnet-5).

## Disposition

- **No clean build.** The only gate-clearing arm is classifier-hint on the strong
  tier -- capability-gated, and (per E1) selection-injection whose behavioral value
  is tier-bound.
- **Stage 2 (powered, if the program continues):** (a) a properly powered re-test
  of the gate (4a) with its placebo -- more TASKS, both tiers -- to settle
  replication vs noise (this is the single most important follow-up: the whole
  "forced deliberation" thesis rides on it); (b) classifier-hint on the strong
  tier, confirmatory; (c) enriched-description (Lane 1's 0.94 selection recall) on
  an INDEPENDENTLY authored holdout to kill the author-circularity, then a
  behavioral arm.
- **Honest terminal read (if no Stage 2):** at this screen's threshold, no
  mechanism robustly beats bare except capability-gated classifier-hint on the
  strong tier; the prior "gate" lead is unreplicated. Bands A (router) + D (model
  floor) still carry dispatch; the search for a robust Band-B/C lift comes up
  mostly empty here.

## Provenance
ledger-screen/*.jsonl (168 trials) x scripts-screen/analyze.py. Banks/arms/scenarios
committed at c30fd18 (feat/dispatch-screen). Pre-registration:
craft docs/design/2026-07-24-dispatch-screen-program-design.md.
