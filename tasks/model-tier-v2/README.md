# model-tier-v2 — the routing-mechanism substrate

Fourteen buyable rungs plus a sealed holdout and a positive control, built to answer one
question: **what is the least a session can spend without losing quality, and does
choosing the model with a rubric calculation cost more than it saves?**

**Authored, not run.** No ledger exists for this bank. Every number below is either
offline evidence the verifiers produce at zero spend, arithmetic a test recomputes, or a
`--dry-run` ceiling. Nothing here is an observation about a model.

> **Blocked at the smoke gate, $0 spent.** `uv run fathom smoke` returns **5/8** with
> `Failed to authenticate: OAuth session expired and could not be refreshed` on both
> checks that make a real model call, reproduced twice. That is neither ALL PASS nor the
> engine-boundary-only 7/8 the discipline permits, so no paid trial has been bought and
> no ledger line written. **The unblock is a host re-authentication, which is a human
> step.** Everything below is pre-registered and unchanged by the block.

---

## The decision this bank exists to settle

Not "is the complexity rubric accurate". The owner's question is narrower and harder:

> the lowest possible spend per session without losing quality — and if we are spending
> MORE by choosing the tier with a rubric calculation, then change it.

So a routing **mechanism** `m` is judged on its total cost:

```
C(m) = decision_cost(m) + execution_cost(tier m picks) + retry_cost(m)

minimise C(m)  subject to  quality(m) >= best quality - non_inferiority_margin
```

Quality is a **constraint**, not the objective. A mechanism that saves money by shipping
worse work has not won; a mechanism that matches the best quality for less has.

**`quality` here means post-repair quality** — what the session ultimately delivers, after
a gate-detected failure has been repaired. Not the first-attempt pass rate. See
[the estimand section](#the-quality-estimand-is-post-repair-and-this-bank-does-not-compute-it)
for why, and for the bounds this bank exports instead of computing it.

**This bank owns the middle two terms and the constraint.** It measures, per task and per
tier: what the tier costs, how often it succeeds, and how its failures split. It does
**not** measure `decision_cost(m)` — what it costs to *run* a mechanism, to score a task
on a rubric before dispatching it — because that is measured by running the mechanism,
which needs its own arms. A separate programme owns that and consumes this bank's output.
Every `C(m)` this bank prints is therefore a **lower bound**, and it says so in the
scorecard rather than printing a zero.

### The candidate mechanisms

Two are properties of the **task** and are computed here from authored, frozen metadata:

| mechanism | how it routes |
|---|---|
| `points` | the scored rubric as it ships: score the task 0–100, map through the 25/55 thresholds |
| `reduced` | a floor plus a few shape shortcuts: the cross-shape floor fires → mid; else a shortcut from the rubric's **own published "Likely strong" list** → strong; else weak |

Three more are fixed rules needing no metadata at all — `always-weak`, `always-mid`,
`always-strong` — and one is not a candidate but the floor: `oracle`, which routes every
task to its measured cheapest adequate tier and is unbeatable by construction.

Mechanisms whose choice depends on the run — escalate-on-red-gate, a model that reads the
repo before dispatching — are **not** computed here. They need arms, and they belong to
the mechanism-comparison programme.

`reduced`'s shortcut list is taken verbatim from the rubric's own "Likely strong"
heuristics rather than invented here. That is deliberate: a reduced mechanism assembled to
lose would settle nothing. It is the rubric's advice with the arithmetic removed.

---

## What the audit found, and what changed

The bank as previously staged could not settle this, for four reasons. Each is arithmetic,
each is now recomputed by a test rather than quoted.

### 1. The screen dropped rungs on the outcome under test

The admission screen dropped a rung as `SATURATED` when the weak arm passed every repeat.
But a rung the weak tier aces **while the rubric routed it to mid or strong** is the single
most informative observation available — it is a mechanism paying for capacity it did not
need, which is exactly the over-spend the question is about. The screen deleted that
evidence before the analysis could see it, and did so probabilistically in the flattering
direction: a rung whose weak arm truly passes 90% of the time was dropped 59% of the time
at repeats=5.

**Changed.** Saturation is now a **reading** — cheapest adequate tier = weak — not a drop.
The only remaining drop is `FLOORED` (no tier clears the bar), and even that is recorded
rather than deleted. The economy the screen was reaching for survives inverted: tranche 3
spends *more* repeats where the reading is uncertain, never fewer where it is inconvenient.
`screen-plan.toml` is superseded by [`tranche-plan.toml`](tranche-plan.toml).

### 2. The rung statistic was mostly a machine for printing `indeterminate`

`empirical_right_tier` asks a *relative* question — which tier is statistically
indistinguishable from the best arm — and answers it so conservatively that at buyable
repeat counts it rarely answers at all. Over six realistic rung shapes, by exact
enumeration:

| repeats | relative statistic reads the right tier | absolute bar τ=0.7 |
|--:|--:|--:|
| 5 | **33%** | **88%** |
| 8 | 42% | 93% |
| 10 | 63% | 96% |
| 12 | 65% | 95% |

It is also **not monotone in n** — the CI-overlap leg tightens in steps, so 12 repeats can
read worse than 10. Buying more repeats did not reliably help.

**Changed.** The primary rung statistic is now `needed_tier(τ)`: **the cheapest tier whose
per-trial pass rate reaches τ**. That is the routing question stated directly — is this
tier good enough to send the work to — and it is the quantity `C(m)` needs. τ = 0.70 is
pre-registered; at repeats=5 it means "4 of 5 or better". The relative statistic is kept
and still rendered, so no committed reading moves; it is simply no longer the primary.

### 3. Score and shape were collinear, so the two mechanisms barely disagreed

Every rung was a bug fix. Across the nine, the point-biserial correlation between "the
cross-shape floor fires" and the rubric score was **r = 0.743**: non-cross-shape rungs
scored {20, 40}, cross-shape rungs {38, 50, 54, 60, 62, 67, 71} — very nearly separable at
39. A bank where the score is a proxy for the shape cannot distinguish "the points predict"
from "the shape predicts", which is the whole contest.

Worse, it left only **three** buyable rungs where `points` and `reduced` route
differently. On concordant rungs both mechanisms buy the same tier and pay the same bill,
so they carry no contrast at all. An exact one-sided sign test over `K` discordant rungs
has a smallest attainable p of `2^-K`:

| K discordant | smallest attainable one-sided p | can reach α=0.05? |
|--:|--:|---|
| 3 | 0.125 | **no** |
| 4 | 0.0625 | **no** |
| 5 | 0.031 | yes, tolerating zero misses |
| 8 | 0.0039 | yes, tolerating one miss (7/8 → p=0.035) |
| 12 | 0.0002 | yes, tolerating two misses |

At K=3 **no result was reachable however the trials fell.** The bank could not have
produced a verdict at any repeat count or any budget.

**Changed.** Five rungs were authored into cells the bank had none in, each in a genre it
had none of, and the buyable discordant set is now **8**. A test asserts the count and
fails below it.

### 4. Every rung was one shape

Routing decisions span authoring, refactoring, unlocalised debugging, data work, review
and planning, and the rubric scores those very differently. A ladder made only of bug
fixes cannot say whether the mapping transfers off that one distribution.

**Changed.** The bank now carries six genres. A test asserts at least five.

---

## The roster

Scores are the pinned model-complexity rubric (`choosing-models/references/scoring-rubric.md`),
one rater — see [Open: the second blind rating](#open-the-second-blind-rating).
`points` = `tier_for_score`; `reduced` is declared per task in
[`scores.toml`](scores.toml)'s `[reduced]` table and frozen before any spend.

| task | genre | score | points | reduced | disagree |
|---|---|--:|---|---|:--:|
| `fix-clamp2` | bugfix | 20 | weak | weak | |
| `plan-migration-order` | **planning** | 37 | mid | weak | ⚠ |
| `feature-ndjson-merge` | bugfix | 38 | mid | mid | |
| `fix-strip-unicode` | bugfix | 40 | mid | weak | ⚠ |
| `refactor-dedupe-validators` | **refactor** | 45 | mid | weak | ⚠ |
| `review-locate-defects` | **review** | 46 | mid | weak | ⚠ |
| `fix-tz-window` | bugfix | 50 | mid | mid | |
| `fix-decimal-round` | bugfix | 54 | mid | strong | ⚠ |
| `fix-quota-rollup` | bugfix | 60 | strong | mid | *(sealed holdout)* |
| `debug-cache-staleness` | **debugging** | 60 | strong | mid | ⚠ |
| `fix-graph-cycle` | bugfix | 62 | strong | mid | ⚠ |
| `data-reconcile-telemetry` | **data** | 66 | strong | weak | ⚠ |
| `fix-merge-3way` | bugfix | 67 | strong | strong | |
| `fix-ledger-replay` | bugfix | 71 | strong | strong | |
| `control-nonlocal-parse` | positive control | 65 | — | — | |

**8 buyable discordant rungs, 5 concordant, 1 sealed, 1 control.**

### The score distribution, honestly

Scores span **20–71** of the 0–100 range. Two deciles-wide stretches are empty and one is
thin:

- **0–19 is empty.** The rubric's trivial-task override (base 15) is unreachable by a
  fathom task: a task with a verifiable, violable acceptance bar necessarily contains some
  logic, which puts the base at 30. This is a structural limit of the instrument, not a
  gap someone forgot to fill.
- **72–100 is empty.** Reaching above ~70 on the additive axes requires either
  reasoning +20–25 ("novel algorithm or proof-like work") or structure +15+
  ("multi-system coordination"), and both are themselves entries on the rubric's "Likely
  strong" shortcut list. **The rubric cannot place a task above ~70 without firing one of
  its own shortcuts**, which means the additive points and the shortcuts are confounded at
  the top of the range by construction. That is a finding about the rubric, discovered
  while trying to author the cell, and it is why `data-reconcile-telemetry` at 66 is the
  ceiling of the no-shortcut range rather than the 78 first targeted.
- **The weak band holds one rung** (`fix-clamp2`, 20). This is a real shortfall, unchanged
  from the previous cycle and for the same structural reason: once a task is substantial
  enough to plant a defect in, the rubric's floor lifts it to at least 26. Any claim of the
  form "the weak tier suffices for trivial work" rests on K=1, and repeats cannot fix K.

### Deliberate enrichment, and what it costs the estimand

The five new rungs were chosen to land where the two mechanisms disagree. Each was
**scored by the rubric as written** and the disagreement read off afterwards — the scores
were not tuned — but the *selection* of which tasks to author was not random.

The consequence is precise and must not be forgotten when reading a result: this bank can
say **which mechanism wins where they differ**, and **what that difference costs per
disagreeing task**. It cannot say **how often they differ on a real workload**, so it
cannot convert a per-disagreement saving into an expected saving per session. That
conversion needs a workload sample, which is a different instrument.

---

## The evidence: satisfiable, violable, determinate

Every rung ships three harness-side overlays beside `fixtures/`, never inside it, so
`stage_task` cannot copy them into a workspace:

- `solution/` — the reference fix. Every criterion true, exit 0.
- `counter/` — the plausible patch at the reported symptom: every **thin** criterion true,
  every **hard** criterion false, exit non-zero.
- `counter-strong/` — a fix that satisfies the **whole standard oracle** and still misses:
  it fails at least one strong-level criterion.

`tests/test_bank_model_tier_v2.py` runs all four positions through the real verifiers on
every task, and pins the per-trial draw the estimator actually scores cells with:

| overlay | per-trial draw | what it proves |
|---|:--:|---|
| `fixtures/` alone | **0** | nothing is banked before the arm does anything |
| `counter/` | **0** | the symptom patch cannot reach the bar |
| `solution/` | **1** | the bar is reachable |
| `counter-strong/` | **0** | the strong oracle has headroom over standard |

`fathom validate model-tier-v2 --strict`: **45 pass, 0 fail, 0 warn, 0 unverifiable.**

What this does **not** establish: that a real weak model writes the `counter/` patch. The
overlays are authored, chosen to be the plausible shortcut. They prove the instrument can
separate; only a paid run can say whether the tiers do.

### The document-producing rungs, and their one exemption

`review-locate-defects` and `plan-migration-order` forbid a code change, so
`regression_test_present` — "did the arm add a test covering what it fixed" — has no
referent. They emit **`code_unchanged`** instead: the module must come back byte-identical
to the harness-side stash. Both are hygiene criteria and neither is ever admissible as a
hard criterion. The swap is asserted in `TestArtifactTasks`, including a test that
*mutates the module and checks the criterion trips* — a preservation check nobody can trip
proves nothing.

---

## Failure mode is a cost term, not a footnote

A failure's **mode** is what prices the retry term, so the bank measures it per trial:

| outcome | meaning | what a session pays |
|---|---|---|
| `pass` | every hard criterion true | the tier's cost |
| `gate_caught` | a hard criterion false **and** the shipped suite went red | the tier's cost **and** the escalation it triggers |
| `silent` | a hard criterion false **and** the shipped suite stayed green | the tier's cost, plus an escape into the work |

The gate signal is `no_regression`, which runs a **harness-side copy** of the shipped
suite that a candidate cannot weaken by editing the workspace — the conservative reading of
"would the gate have caught this".

The two are counted separately and **never summed**. Summing them would let a mechanism
that fails invisibly look cheaper than one that fails loudly, which is backwards: the
invisible failure is the worse outcome. `retry_cost` uses the gate-caught share alone;
silent failures land in `escape_rate`.

### The quality estimand is post-repair, and this bank does not compute it

A cross-implementation check against the routing programme found this bank reporting
**0.55** where that programme reported **0.70** on the same fixture. Both were right, and
they were **different quantities**: the first-attempt pass rate at the chosen tier, and the
probability the work is ultimately correct after a gate-detected repair.

**The estimand is post-repair quality.** `C(m)` already charges the retry cost, so
charging for an escalation while crediting none of its benefit penalises every cheap-start
mechanism twice — once in cost, and again in an unearned quality penalty. It is also what
the objective means: quality is what the session ultimately *delivers*, and a failure the
gate catches and a repair fixes is delivered correct, at a price the cost model has
already paid.

**This bank exports the facts; the consuming analysis owns the estimand.** Per tier it
publishes `passing`, `failures`, `gate_caught_failures` and `silent_failures`, which bound
post-repair quality from both sides:

```
first_attempt_pass_rate  <=  post-repair quality  <=  1 - escape_rate
```

Repair only ever adds (the lower bound), and a silent failure is never repaired because
nothing knows to try (the upper bound). The repair-success assumption between them is the
analysis's to make, not this bank's — the arms here are open-loop and never observe a
repair.

The field formerly called `quality` is now **`first_attempt_pass_rate`**, and the artifact
schema is bumped to **2** so a consumer pinned to schema 1 fails on the version rather than
reading a missing key as absent data. A test asserts no mechanism row carries a field named
`quality` at all. The name had meant two things in one week, which is exactly a number
crossing a boundary with its meaning stripped off.

### A pattern worth naming: two elements, one direction

This is the **second** element of the design found to bias the same way.

| element | how it leaned |
|---|---|
| the admission screen dropping `SATURATED` rungs | deleted the evidence of over-provisioning before the analysis saw it |
| charging retry cost while crediting no repair benefit | penalised cheap-start mechanisms in cost *and* again in quality |

Both were defensible in isolation and both were found by someone else. Two independent
elements leaning toward the dearer mechanism is a pattern, not a coincidence — the plausible
cause is that this bank was built to test a rubric that routes *up*, so every modelling
choice inherited that frame's defaults.

**The standing check this leaves behind, for any element added later:** *does this element
charge a cheap-start mechanism for something without crediting it?* If the answer is not
obviously no, the element needs an explicit argument before it ships. Asymmetry that
survives review twice is unlikely to be the last of it, and a third instance should be
looked for rather than waited for.

This is the retry-economics interaction the skill already names — a red gate the cheaper
model cannot diagnose buys a repair loop rather than a saving — made measurable. Note the
bank's own displaced-cause shape produces *silent* failures by construction: every
`counter/` overlay keeps the shipped suite green. That is the expensive failure mode, and
it is the one a gate-based mechanism cannot rescue.

---

## The substrate artifact — the coordination surface

`fathom report model-tier-v2` writes **`report/routing-substrate-model-tier-v2.json`**
beside the scorecard. It is the input to the mechanism-comparison programme, which
consumes it rather than parsing markdown or reading the ledger a second way: one producer,
one schema, one place the numbers come from.

```jsonc
{
  "schema_version": "2",               // 2 renamed mechanisms[].quality -> first_attempt_pass_rate
  "bank": "model-tier-v2",
  "tau": 0.7,                          // the adequacy bar the ground truth is read at
  "non_inferiority_margin": 0.05,
  "arm_config_hashes": {"haiku": ["…"], "sonnet5": ["…"], "opus5": ["…"]},
  "tasks": [{
    "task_id": "refactor-dedupe-validators",
    "rubric_score": 45.0,
    "genre": "refactor",
    "tier_points": "mid",              // what the scored rubric routes it to
    "tier_reduced": "weak",            // what floor+shortcuts routes it to
    "discordant": true,
    "cheapest_adequate_tier": "mid",   // GROUND TRUTH
    "cheapest_adequate_robust": false, // false = a point estimate, not a robust reading
    "relative_right_tier": "indeterminate",   // the old statistic, kept for continuity
    // The RAW facts per tier. `failures` is stated as well as its two components, so a
    // consumer never has to derive a count (and never derives it differently).
    "per_tier": {
      "weak":   {"arm": "haiku", "trials": 5, "passing": 1, "failures": 4,
                 "pass_rate": 0.2, "ci": [0.036, 0.624],
                 "gate_caught_failures": 2,   // a repair loop is available for these
                 "silent_failures": 2,        // these escape; no gate sees them
                 "mean_cost_usd": 0.02},
      "mid":    {…}, "strong": {…}
    }
  }],
  "mechanisms": [{
    "mechanism": "points", "n_tasks": 13,
    "decision_cost_usd": null,         // NOT measured here — never written as 0
    "execution_cost_usd": 0.213, "retry_cost_usd": 0.020, "total_cost_usd": 0.233,
    "first_attempt_pass_rate": 0.92,   // NOT the estimand — it is the estimand's LOWER bound
    "escape_rate": 0.00                // 1 - this is the estimand's UPPER bound
  }]
}
```

Three contracts worth stating explicitly, because the whole comparison rests on them:

- **`decision_cost_usd` is `null`, never `0`.** Unmeasured is not zero, and writing zero
  would make every total look final when each is a lower bound. A test pins it through a
  JSON round-trip, so it cannot become `0` by serialisation either.
- **Every count is stated, never left derivable.** `failures` is published alongside
  `passing`, `gate_caught_failures` and `silent_failures` even though it is their sum,
  because this table crosses a programme boundary and *a consumer that has to derive a
  count is a consumer that can derive it differently*. The same rule is why
  `schema_version` bumps on a rename: a consumer pinned to the old version fails on the
  version rather than reading a missing key as absent data.
- **`first_attempt_pass_rate` is not the quality estimand** — the estimand is post-repair
  quality, and this artifact deliberately does not compute it. It exports the facts that
  bound it; the consuming analysis picks the repair-success assumption. The old name
  `quality` is gone and a test asserts it stays gone.
- **Cost is aggregated per arm for readability, but identity is the `config_hash`.**
  `arm_config_hashes` records every hash each arm name was seen under, and
  `build_calibration` **warns** when an arm maps to more than one — that is two different
  configurations being averaged under one label, which is exactly the silent-wrong the
  aggregation rule exists to prevent.

---

## The tranches: what each costs and what each decides

Ceilings are real `--dry-run` output at `--max-budget-usd 2`. Read them correctly:
**`--max-budget-usd` is a PER-SPAWN cap, not a run total** — fathom has no total-run cap at
all, so a ceiling is `planned trials × the cap in force`. The binding guard is cumulative:
read summed `cost_usd_est` out of `ledger/model-tier-v2.jsonl` between tranches.

| tranche | command shape | trials | ceiling @ $2/spawn | what it decides |
|---|---|--:|--:|---|
| **T0 instrument** | `--tasks control-nonlocal-parse --repeats 10` on the two-arm dir | 20 | **$40.00** | whether the ladder separates **at all**, on a task with a recorded v1 gradient. **Stop rule: if the control does not separate, no mechanism comparison is interpretable — a flat ladder makes every mechanism look equal — and nothing further is bought.** |
| **T1 discordant core** | the 8 disagreeing rungs × 3 arms × 5 | 120 | **$240.00** | **`points` vs `reduced`**, on both readings: which routes to the cheaper adequate tier, and what the difference costs per task. These are the only rungs where the two can differ. |
| **T2 census complement** | the 5 agreeing rungs × 3 arms × 5 | 75 | **$150.00** | **`always-weak` / `always-mid` / `always-strong` / the `oracle` floor** — mechanisms that differ from everything on *every* rung and so need the whole census. Also completes the ground-truth table and makes the genre-transfer question answerable. |
| **T3 robustness** | the unrobust rungs, repeats 5 → 10 | ≤120 new | ≤**$240.00** | whether each ground-truth reading is a point estimate or **robust**. Required for any threshold move; not required for a mechanism verdict. |
| **program total** | | **335** | **$670.00** | |

**At the v1 observed rate ($0.236/trial mean, $0.576 max across 1059 committed spawns, of
which only 8 exceed $2 and none on a model-tier bank) the full programme lands near
$79, worst observed case ~$193.** Stopping after T1 is 140 trials, ceiling $280, expected
**~$33**.

The ordering is deliberate: T0 is the cheapest thing that can stop the whole programme, and
T1 answers the owner's actual question before a dollar goes to rungs whose answer is a
foregone tie.

### T3's price is arithmetic, not caution

At **repeats=5 no reading can be robust.** A perfect 5/5 has a Wilson lower bound of
**0.566**, below τ=0.70. Ten repeats with a perfect record bounds at **0.722** and clears
it. That is the entire justification for a deepening tranche, and
`test_no_reading_is_robust_at_the_census_repeat_count` recomputes both numbers rather than
quoting them.

### Designed for interruption

The host's OAuth access token lives about eight hours, so no tranche is a single long
invocation. Every tranche is bought in **chunks of 4 rungs** (`chunk_tasks` in
`tranche-plan.toml`): 4 × 3 arms × 5 repeats = 60 trials, about 4 hours at the v1 observed
~4 min/trial — half a token's life, so a chunk that starts on a fresh token finishes on it.
A test asserts the chunk fits.

Resumption needs no state of its own: the resume key is
`(bank, dataset_version, task_id, config_hash, repeat)`, a completed trial is never
re-bought, and an interrupted chunk resumes by **running the same command again**.

```sh
uv run fathom smoke                                    # must be ALL PASS before any spend
uv run fathom validate model-tier-v2 --strict
uv run fathom verify-arming --scenarios-dir scenarios/model-tier-v2

# T0 — the instrument check. Nothing else is bought if this fails.
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2-screen \
  --tasks control-nonlocal-parse --repeats 10 --max-budget-usd 2

# T1 — the discordant core, in two chunks of four rungs.
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2 \
  --tasks plan-migration-order,fix-strip-unicode,refactor-dedupe-validators,review-locate-defects \
  --repeats 5 --max-budget-usd 2
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2 \
  --tasks fix-decimal-round,debug-cache-staleness,fix-graph-cycle,data-reconcile-telemetry \
  --repeats 5 --max-budget-usd 2

uv run fathom report model-tier-v2       # scorecard + routing-substrate JSON
```

**`--scenarios-dir` is load-bearing and this bank has a trap.** The default `scenarios/`
glob also resolves to exactly **three** arms (`bare`, `series`, `single-long-session`), so
omitting the flag prints an identical count line and silently runs the wrong experiment.
The plan prints an `arms:` line naming them — read it before letting a matrix run on.

---

## Pre-registered decision rules

Fixed before any spend. Every one is stated so that a result can only license the action
written against it.

### R1 — the instrument gate (blocks everything)

The control separates iff a **one-sided Fisher exact test** of `haiku` against `opus5` on
per-trial pass counts gives **p ≤ 0.05 at ≥ 10 repeats per arm**. At the control's own
recorded v1 rates (haiku 0.4, opus5 1.0) that rule fires with probability **0.945** at
repeats=10, by exact enumeration a test recomputes.

- **If the control does not separate:** the scorecard prints `underpowered` when fewer than
  10 repeats are on the ledger and `does not separate` otherwise — never the same words for
  the two. In either case **no mechanism conclusion is available from any part of this
  bank**, and nothing beyond T0 is bought. A null here is not evidence against the rubric;
  it is evidence the instrument or the lineup moved.

### R2 — the mechanism verdict (the owner's question)

Read on the discordant set only, and only when it is informative. Both readings are
reported; the decision needs the **cost** reading, and the accuracy reading qualifies it.

Every "quality" below is **post-repair quality**, computed by the consuming analysis from
the per-tier facts this bank exports — never the first-attempt pass rate. Reading these
rules on the first-attempt rate would reinstate the double penalty on cheap-start
mechanisms that the estimand correction removed.

| result | what it licenses |
|---|---|
| `reduced` costs **less** per disagreeing task at permutation p ≤ 0.05, **and** its post-repair quality is within the 0.05 non-inferiority margin of `points` | **Replace the scored rubric with the floor plus shortcuts.** Delete the points arithmetic. The saving is real and paid for at equal quality — and this is before `decision_cost` is counted, which can only widen the gap in `reduced`'s favour, since a lookup costs less to run than a scored rubric. |
| `points` costs **less** at p ≤ 0.05 and is non-inferior | **Keep the scored rubric, and the second dimension is worth adding.** The arithmetic is earning its complexity: it is routing to cheaper adequate tiers than the shortcuts do. |
| the cost difference is **not significant** (p > 0.05) | **Replace the scored rubric with the floor plus shortcuts anyway** — on the tie-break, not on the evidence. Two mechanisms that cost the same at equal quality are not equal: one costs more to *run*, and `decision_cost(points) > decision_cost(reduced)` is true by inspection (a rubric pass is work a lookup does not do). A tie on the measured terms is a loss on the unmeasured one. **This is the rule that most needs stating in advance**, because after the fact a tie is the easiest result to read as "change nothing". |
| fewer than **5** informative discordant rungs | **No verdict. Nothing changes.** The sign test cannot reach α at all below 5, and the scorecard says `underpowered` rather than reporting a null. The cost reading is still printed and is still directional evidence, but it does not license a change on its own. |
| `points` post-repair quality exceeds `reduced`'s by **more** than the 0.05 margin | **Keep the scored rubric regardless of cost.** Quality is the constraint; a cheaper mechanism that breaches it has not won. Note this must be checked on the post-repair figure: on first-attempt rates a cheap-start mechanism can breach the margin and still deliver the same work once its gate-caught failures are repaired. |

### R3 — a threshold move (25 or 55)

A numeric threshold moves **only** on all four of:

1. the control separates (R1);
2. the rungs bracketing that threshold have **robust** ground-truth readings — not point
   estimates — which requires tranche 3;
3. the observed crossover interval, the score range over which the cheapest adequate tier
   steps up, **excludes** the current threshold;
4. the recalibration playbook's **cross-distribution** rule is satisfied: the same direction
   reproduces on a second, differently-shaped task distribution. One narrow distribution at
   small n updates the calibration note and the `models.toml` provenance, **not** the
   thresholds.

**No threshold move is licensed by this bank alone**, because condition 4 cannot be met by
one bank by definition. This bank can supply conditions 1–3 and half the evidence for 4.

### R4 — what leaves everything unchanged

Stated explicitly so that inaction is also a pre-registered outcome rather than a default:

- the control does not separate, at any repeat count;
- fewer than 5 informative discordant rungs, however the trials fell;
- every mechanism's quality falls outside the non-inferiority margin of the best (the bank
  floored — no tier does this work, so routing is not the variable);
- the ground-truth readings are determinate but the mechanism ordering flips between
  τ = 0.6, 0.7 and 0.8 (the sensitivity sweep is reported alongside the primary; an
  ordering that depends on the bar is not an ordering).

**Nothing is retired or changed on the basis of a measurement without power, and
`unmeasured` is never written as `null` in prose or as `0` in the artifact.**

---

## What this battery still cannot settle

Stated up front so no reader has to infer it from a silence.

1. **The decision cost of any mechanism.** Not measured here and not measurable here. Every
   `C(m)` is a lower bound. The ordering it implies is decisive only where the gap exceeds
   the difference in what the mechanisms cost to run.
2. **How often the mechanisms disagree on a real workload.** The discordant set is enriched
   by design. A per-disagreement saving cannot be converted into an expected saving per
   session without a workload sample this bank does not contain.
3. **Any threshold move.** R3 condition 4 needs a second distribution. One bank cannot
   satisfy a cross-distribution rule.
4. **Whether escalation-on-red actually recovers.** The arms are `single-session` and
   open-loop: the verifier grades a finished artifact and no repair happens. The bank
   supplies the *inputs* to the retry term — failure rate, gate-visibility, per-tier cost —
   but never observes a weak model, confronted with a red gate, succeeding on the retry.
   A mechanism that escalates is priced here on an assumption, not an observation.
5. **The trivial band (score 0–19) and the top band (72–100).** Structurally unreachable:
   the first because a verifiable task carries logic, the second because the rubric cannot
   reach it without firing its own shortcut. Any routing claim about those ranges is
   extrapolation.
6. **"The weak tier suffices for trivial work" at more than K=1.** The weak band holds one
   rung. Repeats cannot fix K.
7. **A robust reading for a genuinely marginal tier.** A tier whose true pass rate is 0.8
   needs roughly 100 repeats for its Wilson lower bound to clear τ=0.70. At three arms that
   is unaffordable for even one rung, so marginal tiers will read as point estimates
   permanently.
8. **Whether the authored `counter/` patch is what a weak model actually writes.** Every
   rung's hard criteria are stated as verbatim bullets in its fixture README, and the
   instruction points the model at that README — so the discovery step the displaced-cause
   shape gates on is partly handed over. Authoring cannot answer this at any price; only
   the run can.
9. **The oracle-quality crossing (ADR-0008).** Every task still ships its thin/standard/
   strong criterion slice and `counter-strong` demonstrates the strong oracle has headroom
   on every rung, but the slicer that reports each tier's slope across the three levels is
   not built and ADR-0008 is not accepted. The bank does not depend on it; the oracle
   *reading* of the bank does.

---

## Open: the second blind rating

The design asks for **two blind raters**, as `model-tier-v1` had. `scores.toml` carries
**one**. The bank was authored in non-interactive sessions with no way to convene a second
blind rater, so this is an open pre-run step. To keep the gap cheap to close, every task
records a full per-axis breakdown and a test asserts the axes sum to the score — a second
rater can disagree on a named axis rather than re-derive a number.

The declarations most likely to move, and what moves with them:

- `fix-decimal-round`'s domain axis, taken as regulatory (+12) because half-away-from-zero
  rounding of money is an accounting rule. At +8 it scores 50, and its `reduced` shortcut
  stops firing — it would leave the discordant set, taking K from 8 to 7 and the sign
  test's tolerance from one miss to zero.
- `plan-migration-order`'s shortcut declaration. A rater who reads constraint C3 as
  "multi-stage migration with rollback" fires the strong shortcut, and that rung likewise
  leaves the discordant set.

**Both risks run the same way: K falls.** The bank is authored with K=8 against a floor of
5, so it survives losing two — but a third would put the sign test back below the line, and
that is the number to watch when the second rating lands.

---

## Layout

```
tasks/model-tier-v2/
  bank.toml            name, dataset_version (2), holdout
  scores.toml          rubric scores + per-axis breakdown, [reduced] mechanism,
                       [genre], [analysis] parameters, [control] rule
  oracles.toml         thin/standard/strong criterion sets per task
  tranche-plan.toml    the buy plan: tranches, drop rule, chunking (supersedes
                       screen-plan.toml)
  bankverify.py        shared, scenario-blind verifier helpers
  <task>/
    task.toml          instruction, limits, [verify] hard_criteria, [gate]
    verify.py          emits all three oracle levels; exit code gates on standard
    fixtures/          staged into the workspace
    original/          harness-side stash (byte-identical to the fixture)
    solution/ counter/ counter-strong/   the three graded overlays
```

Arms: `scenarios/model-tier-v2/{haiku,sonnet5,opus5}.toml`, identical but for `model`.
`scenarios/model-tier-v2-screen/` is the two-arm subset the control rule reads; its arms
resolve to the same `config_hash` as their census twins, so a control trial is a census
trial and neither is bought twice (a test asserts the hashes match).

Tests: `tests/test_bank_model_tier_v2.py` (stdlib-runnable, ~3 min — it runs every verifier
over every overlay) and `tests/test_calibration.py` (the statistics: per-trial scoring, the
adequacy bar, failure-mode classification, `C(m)`, the discordance analysis, the substrate
schema, and the repeat-count re-derivations).
