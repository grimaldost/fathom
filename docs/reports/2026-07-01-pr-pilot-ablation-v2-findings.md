# The series engine value ablation v2 (brownfield) -- findings and evolution case

- **Date:** 2026-07-01/02 (matrix + M2 replication complete; blind-panel verdicts folded)
- **Bank:** `tasks/ablation-v2/exprlang` -- brownfield, multi-file (lexer / parser /
  evaluator / errors) feature-add: comparison + boolean operators with short-circuit,
  bool-vs-int type rules, precedence, multi-char lexing.
- **Grading:** blind harness-side oracle (`verify.py`, 15 criteria incl. a 60-case
  property test vs an independent reference evaluator). The repo's visible suite (the
  gate) is a mutation-proven proper subset of the oracle (mutants validated in a
  scratch workspace; regenerable from the recipe in the design spec -- not persisted,
  a reproducibility gap the panel flagged).
- **Cost:** real spend ~$0 (subscription auth); $ figures are list-equivalent
  estimates from token counts. n per cell 6-10; 95% Wilson CIs.
- **Process:** written from the series-engine advocate position under an anti-self-deception
  contract: concessions first, every defense tied to a falsifiable measurement, and the
  draft submitted to a BLIND two-reviewer panel (a both-directions methodology auditor
  and a steelman adversary, no session context, ledger recomputed independently).
  Panel verdict: **publishable with edits** -- every point estimate reproduced from the
  ledger ("honest to the cent"), with attribution/framing/disclosure corrections. This
  version folds them; §9 summarizes what changed.

## 1. TL;DR (panel-corrected)

1. **Strong tier: null across the board (conceded).** Bare Sonnet 5 self-verifies and
   lands 100% on this task class; every in-session series-engine feature (gate, review,
   authoring brief, extra attempt) measured +0 quality at ~equal interleaved cost.
   Caveat the panel enforced: at a 100% base rate the instrument cannot detect value --
   "adds +0 here" is measured; "adds nothing anywhere at strong tier" is not. The
   headless engine was NOT run: its strong-tier quality question is *expected* null by
   the self-gating argument but remains **unmeasured** (the only engine datum on file
   is 2026-06-10: ~4.6x tokens for +0 quality).
2. **Weak tier: failures collapse onto a machine-checkable defect class the repo suite
   provably misses, and the suite-only gate catches none of it** (8/8 gates green,
   5/8 oracle escapes, 38% = 38% vs bare). A 10-case deterministic type-contract probe
   added to the gate **coincided with 38% -> 90%** -- but the panel's decomposition
   caps what the mechanism *demonstrably* earned: the probe fired in 2/10 trials
   (both rescued: red -> fix -> green -> oracle-pass), while 7/10 passed on first
   attempt in a batch whose first-attempt quality was anomalously high vs earlier
   batches (type-correct 8/10 vs ~11/26, Fisher p~0.05-0.08) and which ran as a
   contiguous block, last, in a ledger with no timestamps. **Attributable lift:
   between +20pp (verified rescues) and +52pp (headline); mechanism demonstrated,
   magnitude unconfirmed pending an interleaved replication.**
3. **The transferable finding (survived both reviewers):** self-authored tests inherit
   the implementer's blind spots -- Haiku wrote gate-passing tests sharing its own
   bool-is-int misconception, and in the review arm approved its own defective code
   5/5 times. Gate value therefore tracks the **independence and coverage of the
   deterministic oracle**, not the presence of a gate. What the series engine should do about
   that is an agenda (§5), not yet a result.

## 2. Why this instrument (recap)

v1 (greenfield, single-file) was aced by bare Sonnet 5/5 -- a quality-null that could
not discriminate any arm. The operator's method rule stands: **do not conclude from a
blunt instrument; build one that can see.** v2 is brownfield (regression surface) +
multi-file (coupling) with mutation-proven gate-escape classes. Bank validation:
fixture baseline green / fixture gate + oracle red / solution gate + oracle all-green
(re-verified independently by the audit). A fresh-eyes pre-mortem (2 BLOCKER, 4 MAJOR)
was folded before spend; its key fixes -- headroom-tier primary measurement (FM-1),
iteration-matched `reprompt` control (FM-6), mutation validation (FM-4) -- all
mattered downstream. Deviations the audit surfaced, acknowledged: the Haiku cross ran
n=8 (design pinned n=10) except the review/authoring/sg arms; per-criterion vectors
are summarized in prose rather than tabled; minimum detectable effect at n=8 vs 3/8
baseline is near-total rescue only.

## 3. The full matrix (15 arms; `lazy-gate` stub excluded as a withdrawn arm)

| arm | model / effort | harness | pass | 95% CI | $/trial | $/success | turns |
|---|---|---|---|---|---|---|---|
| bare | Sonnet 5 hi | none (self-judged) | 6/6 = 100% | 61-100% | 1.24* | -- | 24 |
| bare-reprompt | Sonnet 5 hi | +1 generic re-verify spawn | 8/8 = 100% | 68-100% | 1.54 | -- | 51 |
| bare-gate | Sonnet 5 hi | + suite gate + fix loop | 8/8 = 100% | 68-100% | 0.80* | -- | 25 |
| bare-gate-review | Sonnet 5 hi | + review pass | 5/5 = 100% | 57-100% | 2.09 | -- | 38 |
| bare-authoring | Sonnet 5 hi | + structured brief | 8/8 = 100% | 68-100% | 1.41 | -- | 25 |
| orchestrated | Sonnet 5 hi | gate + "rely on the gate" brief | 8/8 = 100% | 68-100% | 0.78* | -- | 24 |
| sonnet-lo | Sonnet 5 **low** | none | 8/8 = 100% | 68-100% | **0.53** | 0.53 | 20 |
| sonnet-lo-gate | Sonnet 5 low | + suite gate | 7/8 = 88% | 53-98% | 0.56 | 0.64 | 22 |
| opus | Opus 4.8 hi | none | 8/8 = 100% | 68-100% | 1.04 | 1.04 | 22 |
| haiku | Haiku 4.5 hi | none | 3/8 = 38% | 14-69% | 0.27 | 0.72 | 33 |
| haiku-reprompt | Haiku 4.5 hi | +1 generic re-verify | 4/8 = 50% | 22-78% | 0.39 | 0.78 | 46 |
| haiku-authoring | Haiku 4.5 hi | + structured brief | 4/10 = 40% | 17-69% | 0.29 | 0.72 | 34 |
| haiku-gate | Haiku 4.5 hi | + suite gate (blind to the defect) | 3/8 = 38% | 14-69% | 0.30 | 0.80 | 34 |
| haiku-gate-review | Haiku 4.5 hi | + review | 5/10 = 50% | 24-76% | 0.34 | 0.68 | 40 |
| **haiku-gate-sg** | Haiku 4.5 hi | + **strengthened** gate (suite + type probe) | **9/10 = 90%** | 60-98% | 0.33 | **0.36-0.37** | 40 |

\* batch-1 (arm-blocked) figures; §6 shows the interleaved replication -- bare's true
adjacent-run cost is ~$0.75-0.83, and the Sonnet-arm cost differences vanish.
(Disclosure fixes from the audit: the `haiku-authoring` row was missing from the
earlier draft; `bare` shows the n=6 primary cell -- all 17 completed bare trials
across batches passed; `sonnet-lo-gate`'s one red trial has null oracle grades in the
ledger and is counted failed via gate-subset logic; the `haiku-gate-review` trials
predate the gate-`detail` ledger patch, so their per-trial gate/review telemetry is
unrecoverable.)

Defect-escape (gate green but oracle red): `haiku-gate` **5/8**; `haiku-gate-sg` 1/10
(the `not_op` residual -- gate-green, i.e. **undetected**); Sonnet gated arms 0.

## 4. Findings (panel-corrected)

### F1 -- strong tier: in-session features measured +0 on this instrument

Bare Sonnet runs the tests itself (~24 turns) and lands 100%; gate / review /
authoring / reprompt change nothing but cost. Review specifically: 2x spawns, 0/5
changes -- but the panel restored the design's own FM-8 flag: at a 100% base rate a
review-null is **instrument-ambiguous** (CI on 0/5 reaches 43%), evidence of
redundancy-here, not worthlessness. Same ceiling logic bounds "Opus = Sonnet".

### F2 -- weak tier: the blind gate detects nothing; iteration alone adds ~+12pp noise-level

Haiku 38%, failures concentrated on `type_bool_in_arith`. The suite gate neither
detects (5/8 escapes) nor lifts (38% = 38%). The iteration-matched control
(`reprompt`, 50%) and the review arm (50%) sit within noise of bare (p~0.66); the
review arm's verdicts approved defective code 5/5 times it graded it. Survived both
reviewers untouched.

### F3 -- strengthened gate: mechanism demonstrated, magnitude unconfirmed

Same task, same model, same fix loop; the harness gate gains a 10-case deterministic
type-contract probe. Result 9/10 (90%) vs 3/8+3/8 pooled baseline (Fisher two-sided
p=0.014; vs `haiku-gate` alone p=0.043; vs the `reprompt` control p=0.118).
Panel-enforced decomposition:

- **2 trials**: probe fired (gate red), fix loop rescued, oracle passed -- the
  catch-and-rescue mechanism, directly evidenced, 2/2.
- **7 trials**: passed on first attempt -- the probe (harness-side, invisible unless
  red) played no role. First-attempt type-correctness in this batch: 8/10 vs ~42%
  in earlier weak-tier batches (p~0.05-0.08) -- a batch anomaly the ledger cannot
  adjudicate (no timestamps; arm ran as a contiguous last block).
- **1 trial**: `not_op` escape, gate-green -- the residual surface survived (the probe
  did not become the oracle), and it was **undetected**, which matters for E-d.

Honest statement: **the mechanism is real (2/2 rescues at ~$0.03 amortized/trial,
~0 LLM tokens when green); the 52pp magnitude is confounded with batch position/luck;
attributable lift is bounded +20pp..+52pp.** Promotion requires an interleaved
replication with a concurrent `haiku-gate` control and a pre-registered probe.
Cost-per-success, corrected comparators: $0.36-0.37 vs interleaved bare Sonnet
$0.75-0.83 -> **~2.0-2.3x cheaper** (not the 3.4x the cold-cache figure implied), and
vs blind-gate Haiku $0.80 -> ~2.2x.

### F4 -- effort routing (hypothesis) and the gate-catch anecdote (withdrawn)

`sonnet-lo` = 100% at $0.53 -- ~30-36% cheaper than interleaved high-effort bare, same
quality, on ONE task that even Haiku solves 38% of the time. A pricing observation
that motivates an effort-routing hypothesis; falsifier: a task where low effort
measurably degrades Sonnet, then routed-vs-always-max. The earlier draft's "first
live gate catch" claim is **withdrawn**: in that trial the two fix attempts were
0-turn/$0 spawns that never executed and the oracle never scored the workspace --
consistent with a merge-blocking safety property, but n=1 and infrastructure-tainted.

### F5 -- what review is for (narrowed)

After the strengthened gate, the surviving failure is semantic (`not_op`) and
gate-invisible. Deterministic checks have a floor; catching what lives above it
requires an oracle *independent of the implementer* -- and the weak tier cannot
review itself (5/5 self-approvals of defective code). Review's niche is conditional
AND requires independence (a stronger model or a human), not more passes by the same
model.

## 5. The evolution agenda -- panel-adjudicated status

- **E-a. Deterministic oracle strengthening.** SURVIVES NARROWED. What is demonstrated:
  an independent deterministic check with an instructive failure message rescues a
  weak model from its own blind spot, at ~zero cost when green. What is NOT
  demonstrated: that the series engine can *supply* such checks generically -- this probe
  encodes task-specific semantics (5/10 cases overlap the acceptance oracle
  verbatim), i.e. bespoke test authoring, which the series engine's own philosophy assigns to
  the repo. The defensible product kernel: **compose and measure oracle independence
  and coverage** (run repo suite + typecheck + property/mutation smokes as separate
  gate lanes; report per-lane catch rates), rather than "own the oracle."
- **E-b. Escape telemetry.** THE LOAD-BEARING UNTESTED HYPOTHESIS (both reviewers).
  Without it, E-a's probe-authoring knowledge has no production source (here it came
  from observing the failures -- the study's central circularity caveat). Chicken-and-
  egg acknowledged: gate-green-but-defect-found telemetry needs a later defect signal,
  which a walk-away flow must source from CI/review/issues. Test before any preset
  ships: does a telemetry-suggested check close the measured escape class on the next
  series?
- **E-c. Routing v2 (model x effort x conditional review).** SURVIVES AS HYPOTHESIS
  with defined falsifiers; the effort half rests on one easy cell (F4). The
  conditional-review half follows from F1 (cost) + F5 (independence), with the FM-8
  ceiling caveat on the strong-tier evidence.
- **E-d. Escalation ladder.** DOES NOT SURVIVE AS STATED. Its trigger
  (gate-red-after-fixes) fired 0/10 in the keystone arm; the one real failure was
  gate-GREEN -- the ladder would have merged it silently, the worst outcome for a
  walk-away product. Inside this matrix the ladder is dominated by `sonnet-lo`
  ($0.53 at 100% vs ~$0.45-0.55 at 90% with an undetected-escape tail). Revival
  requires E-a-level detection of the residual classes plus explicit pricing of a
  shipped escape.
- **E-e. Engine as governance product.** REFRAMED: a *positioning hypothesis*, not a
  finding -- the engine never ran here. Its strong-tier quality contribution is
  expected-null by the self-gating argument but unmeasured; its known datum is ~8x
  cost for +0 quality on below-threshold work (2026-06-10). The panel's challenge
  stands: name the falsifiable governance metric and its realistic n before
  positioning on it (P10/variance discrimination at engine cost is expensive; a
  variance study needs n>=30/config).

## 6. Efficiency cross-check (M2) -- the cost gap was a confound; the gate is cost-neutral

The raw matrix showed gated Sonnet arms ~37% cheaper than bare -- but the arms had run
in per-arm blocks (bare first, cache cold). The interleaved replication (one new trial
per arm per round, time-adjacent; healthy completed trials only) kills the gap:

| arm | batch 1 (arm-blocked) mean $/t | batch 2 (interleaved, n=8/arm) mean / median $/t | pass |
|---|---|---|---|
| bare | 1.10 | 0.83 / **0.75** | 8/8 |
| bare-gate | 0.80 | 0.86 / **0.76** | 8/8 |
| orchestrated | 0.81 | 0.81 / **0.74** | 8/8 |

(Means audit-corrected to healthy-spend-only; the earlier draft's 0.96/0.84 had
poisoned-window spend in the numerator -- the error direction was anti-gate.) Verdict:
**cost-neutral at the strong tier** (medians within $0.02); the "rely on the gate"
brief does not deliver measurable token savings. The batch-1 gap was an order/cache
artifact; the replication existed to catch it and did. Standing method rule, now
extended per the audit: **interleaving is required for any cross-arm claim -- cost or
quality** (the F3 keystone cell itself violated it and pays with an unresolvable
batch confound).

## 7. Scope and limitations

One task family (interpreter feature-add, self-checkable, tests present); weak-tier
economics on Haiku 4.5 only; the probe was authored knowing the dominant failure
class (E-b is the honest production substitute); n small (6-10/cell; MDE at n=8 vs
3/8 baseline is near-total rescue); no ledger timestamps / cli_version / model_id on
these records (batch effects unauditable post hoc -- filed as fathom feedback);
mutation-validation artifacts not persisted (recipe in the design spec). Conclusions
bind to this class; the lineage-wide claim is the *mechanism* (oracle independence
and coverage gate the gate's value), not the point numbers.

## 8. Verdict (panel-corrected)

On this task class: **at the strong tier, use a bare strong model -- low effort if
available** (`sonnet-lo` was the cheapest 100% cell); every in-session series-engine
feature measured +0 quality there, at cost that is neutral once interleaved. At the
weak tier, failures collapsed onto one machine-checkable contract class the repo
suite provably misses; the suite-only gate detected nothing; a hand-authored probe
for that known class coincided with 38%->90%, of which +20pp is verified
catch-and-rescue and the remainder is batch-confounded. The transferable finding is
that **self-authored tests inherit the implementer's blind spots, so gate value
tracks the independence and coverage of the deterministic oracle** -- whether
the series engine can supply that coverage generically (E-a-narrowed) or learn it from escapes
(E-b) is the actual keystone, and it is untested. The engine was not measured here;
its quality-vs-bare question at strong tier remains expected-null-but-open. Before
any promotion of the keystone: an interleaved sg replication with concurrent control
and a pre-registered probe on a class not chosen from observed failures.

## 9. Blind panel -- what the reviewers changed

Two blind reviewers (no session context; ledger recomputed independently):

- **Methodology auditor (both-directions):** verdict *publishable with edits*; all 14+
  matrix rows and CIs reproduced exactly. PRO-tool bias found: F3 over-attribution
  (2/10 probe-fires), stale 3.4x/"half the cost" multipliers, E-d arithmetic assuming
  detection it doesn't have, F4's n=1 safety story. ANTI-tool bias found: engine
  "settled (null)" without running it; review/Opus nulls stated without the 100%-
  ceiling caveat (FM-8). Method: haiku-authoring row omitted; batch-2 means included
  poisoned spend; n deviations from the design unacknowledged; provenance gaps.
- **Steelman adversary:** E-d does not survive (trigger 0/10, escape was gate-green,
  dominated by sonnet-lo); E-a narrowed to oracle-independence kernel (probe~oracle
  overlap); E-e is positioning-before-measurement; F1/F2/M2 and the blind-spot
  mechanism survive fully; proposed the §8 rewrite adopted above (adapted).

All four load-bearing edits and the disclosure fixes are folded in this version.
Panel cost: ~275k subagent tokens (~$4-6 est.).
