# model-tier-v2 — the tier-separating calibration bank

Nine bug-fix tasks on a graded difficulty ladder, built to the design of record
[`docs/specs/2026-07-14-tier-separating-bank-design.md`](../../docs/specs/2026-07-14-tier-separating-bank-design.md).
The arms are model tiers (weak / mid / strong); the ladder is meant to show where each
tier's capability ceiling falls.

**Authored, not run.** No ledger exists for this bank. Everything below is offline
evidence produced by the verifiers themselves, at zero spend.

> **Screen status, 2026-08-12 — blocked at the smoke gate, $0 spent.** The screen
> (below) is licensed and priced, and its first block was taken to the point of spending
> before it stopped: `uv run fathom smoke` returned **5/8** with
> `Failed to authenticate: OAuth session expired and could not be refreshed` on both
> spawns that make a real model call, reproduced twice. That is neither ALL PASS nor the
> engine-boundary-only 7/8 that the discipline permits, so no paid trial was bought and
> no ledger line was written. The `credential-only spawn authenticates & completes` and
> `system-prompt injection reaches the model` checks are the two that fail; the mount
> checks still pass because they read the CLI's `init` event, which is emitted before
> any model call. **The unblock is a host re-authentication, which is a human step** —
> after it, `fathom smoke` must be re-run and must pass before stage 0a is bought.
> Everything else in this file is pre-registered, tested, and unchanged by the block.

## Why this bank exists

`model-tier-v1` is **saturated**: six of seven scored tasks are aced by every tier, no
task resolves empirically to mid or strong, and a 10/10 cell carries a Wilson 95% CI of
[0.72, 1.00]. Its on-diagonal count of 1/7 has been reproduced three times, and each
time the honest reading was the same — a null manufactured by a bank with no headroom,
not an observed answer about the rubric. The CRAF-B11 question (*does the
choosing-models score separate model tiers on OUTCOME?*) cannot be decided on that
instrument.

So the requirement here is headroom: on every task there must be a plausible answer
that clears the reported symptom and still fails, and the difference must be one that
capacity plausibly explains.

## The separating shape

Each task plants a **displaced cause**: the fault surfaces where the instruction points,
and the fix belongs somewhere else that a second consumer also depends on. Patch the
symptom site and the reported case goes green while the unnamed consumer stays broken.
Three variants, so separation is not an artifact of one trick — displaced cause, backend
parity, cross-module invariant.

That shape is **necessary but not sufficient**: v1's `fix-nonlocal-urlkey` had it and
saturated anyway. The shape is why a task is a candidate; the Part B screen (below) is
what would admit it.

## The roster

Scores are the pinned model-complexity rubric
(`choosing-models/references/scoring-rubric.md`), one rater — see
[Open: the second blind rating](#open-the-second-blind-rating). Predicted tier is
`tier_for_score`: 0-25 weak / 26-55 mid / 56-100 strong.

| task | shape | score | predicted tier | what the standard oracle catches |
|---|---|--:|---|---|
| `fix-clamp2` | single function | 20 | weak | the bound the rewrite dropped |
| `feature-ndjson-merge` | shared-helper fan-out | 38 | mid | the second reader path, unnamed |
| `fix-strip-unicode` | single function | 40 | mid | everything that is not an accent |
| `fix-tz-window` | displaced cause | 50 | mid | the second consumer of the day window |
| `fix-decimal-round` | backend parity | 54 | mid | the other side of zero, and a parity grid |
| `fix-quota-rollup` | cross-module invariant | 60 | strong | the two readers of a stale rollup (holdout) |
| `fix-graph-cycle` | displaced cause | 62 | strong | the other readers of the duplicated edge |
| `fix-merge-3way` | cross-module | 67 | strong | the same rule in the nested entry point |
| `fix-ledger-replay` | backend parity | 71 | strong | a repeated void the incremental path double-counts |
| `control-nonlocal-parse` | **positive control** | 65 | strong | two consumers of one mis-split parser (ported from v1) |

**Spread gate, honestly.** The 55 edge is **double-covered** — `fix-decimal-round` at 54
(Δ1 below) and `fix-quota-rollup` at 60 (Δ5 above) — which the design expected the rubric
to refuse, and a test asserts it. The 25 edge has one rung, `fix-clamp2` at 20 (Δ5).
**The weak band holds one task.** That is a real shortfall against the ≥2-per-band
target and it is the same structural finding v1 recorded: once a task is substantial
enough to plant a displaced cause in, the rubric's cross-shape floor lifts it to at least
26. `fix-strip-unicode` was authored as a ~22 rung and scored 40. The consequence for
the analysis is concrete — the weak band's dose-response leg rests on **one task**, so
"the weak tier suffices for trivial work" will be a claim with K=1, and repeats cannot
fix K.

`fix-quota-rollup` is the sealed holdout (ADR-0005). It is the redundant half of the
deliberately double-covered 55 rung, so sealing it costs the least band coverage.

### The positive control

`control-nonlocal-parse` is not a rung. It is `model-tier-v1`'s `fix-nonlocal-parse`,
ported verbatim, and it is in the run set to make a **null interpretable**.

Without it, the modal outcome of this bank — every task saturates, every cheapest-
adequate arm reads `weak`, on-diagonal count near 1/9 — is numerically the v1 result
this bank exists to replace, and nothing in the data separates *"the complexity score
does not predict the tier"* from *"this bank had no headroom for a tier to matter"*.
Those two license opposite decisions and one of them is a deletion. With K=9 the
binomial 95% CI on any on-diagonal count spans both (5/9 → [0.21, 0.86]), and repeats
cannot raise K.

The control is the one task on the committed `ledger/model-tier-v1.jsonl` with an
observed monotone tier gradient on its hard criteria: **haiku 2/5, sonnet 3/5,
sonnet5 4/5, opus 5/5, opus5 5/5**. Nothing about it was retuned — same instruction,
fixture, stashed original, shipped suite, and the same two hard criteria — because a
control is worth having only if its prior reading transfers. It is therefore exempt
from this bank's oracle slice, its `counter-strong` overlay, and the `hard_criteria`
derivation rule; each exemption is asserted in the test suite rather than left to
prose. Its score (65) is v1's two-rater final, which is why it has no per-axis
breakdown in `scores.toml`.

What it buys, in one line: **if the ladder does not separate on the control either,
the run says nothing about tiers** — the instrument or the lineup moved, and no
"retire tier X" conclusion is available from any part of the matrix.

**How to read it — by its own rule, not by the confusion matrix.** Not "lands
on-diagonal": at its own v1 rates the cheapest-adequate statistic reads *indeterminate*,
because `sonnet5` at 0.8 overlaps `opus5` while sitting outside ε — a correct answer to
"which tier is cheapest-adequate" and a useless one for "does the ladder separate at
all". The control is therefore scored by its own rule and **excluded from the confusion
matrix**, in code (`calibration.control_separation`, declared in `scores.toml`'s
`[control]` table), not in prose.

**The rule, and the repeat count it forces.** The control separates iff a **one-sided
Fisher exact test** of `haiku` against `opus5`, on per-trial pass counts, gives
`p ≤ 0.05` — at no fewer than **10 repeats per arm**.

The rule that shipped in the first repair was "haiku's Wilson CI disjoint from opus5's,
at repeats=5". It was a coin flip, and under the per-trial estimator (below) it is worse
than that. Both candidate rules are costed here by exact enumeration over both arms'
binomial draws at the control's own recorded v1 rates — haiku 2/5 → 0.4, opus5 5/5 → 1.0
— and the table is recomputed by a test, not quoted:

| repeats per arm | P(disjoint Wilson CIs) | P(Fisher one-sided ≤ 0.05) |
|--:|--:|--:|
| 2 | 0.000 | 0.000 |
| 3 | 0.000 | 0.216 |
| 5 | **0.078** | 0.337 |
| 8 | 0.315 | 0.826 |
| **10** | 0.633 | **0.945** |
| 15 | 0.905 | 0.998 |

So the disjoint-CI rule would need repeats=15 to clear the 0.9 bar; the Fisher rule
clears it at 10, which is what the bank buys. The replacement is arithmetic, not taste.

**The honest limit on that 0.945.** It plugs opus5 in at 1.0, which is a point estimate
off five trials. At a true opus5 rate of 0.9 the same rule gives 0.659 at repeats=10 and
needs 20 to reach 0.951; at haiku 0.5 instead of 0.4 it gives 0.828 at 10 and 0.927 at
12. The pre-registration buys 10 because that is the bar stated ("≥ 0.9 at v1's own
observed rates") and because the sensitivity runs in one direction only: a control that
fails to fire at 10 **blocks** the tier conclusions rather than licensing any, so an
underpowered miss costs a run and not a wrong answer. The scorecard prints
`underpowered` rather than `does not separate` when fewer than 10 repeats are on the
ledger, so the two failure modes never read the same.

## The evidence: satisfiable, violable, and where each oracle bites

Every task ships three harness-side overlays beside `fixtures/`, never inside it, so
`stage_task` cannot copy them into a workspace:

- `solution/` — the reference fix. `fathom validate` uses it for
  `verifier passes on the reference solution`.
- `counter/` — the plausible patch at the reported symptom: what a model that reads the
  instruction and not the README would write.
- `counter-strong/` — a fix that satisfies the **whole** standard oracle and still misses
  the root cause.

`tests/test_bank_model_tier_v2.py` runs all three through the real verifiers on every
task. The table is that test's content, and it is the answer to "can these criteria be
met, and can they fail?":

| task | score | untouched fixture | reference solution | standard criteria the symptom patch fails | strong criteria the standard-passing patch fails |
|---|--:|---|---|---|---|
| `fix-clamp2` | 20 | 5/8 false | all true | `clamp_above_preserved`, `no_regression`, `regression_test_present` | `clamp_float_exact`, `clamp_bounded_and_idempotent` |
| `fix-strip-unicode` | 40 | 6/9 false | all true | `non_latin_preserved`, `symbols_preserved` | `decomposed_input_equivalent`, `covers_unlisted_accents`, `idempotent_and_mark_free` |
| `feature-ndjson-merge` | 38 | 6/8 false | all true | `merge_lines_dedupes`, `merge_lines_position_preserved` | `merge_records_dedupes`, `merge_all_paths_agree` |
| `fix-tz-window` | 50 | 6/8 false | all true | `slots_cover_transition_day`, `regression_test_present` | `window_bounds_every_day`, `windows_tile_without_gap` |
| `fix-decimal-round` | 54 | 6/8 false | all true | `fast_half_up_negative`, `backend_parity_binary_grid` | `backend_parity_decimal_literals`, `parity_through_line_total` |
| `fix-quota-rollup` | 60 | 6/8 false | all true | `remaining_reflects_usage`, `over_quota_detected`, `regression_test_present` | `rollup_invariant_at_source`, `rollup_invariant_with_late_member` |
| `fix-graph-cycle` | 62 | 6/9 false | all true | `dependency_count_deduplicated`, `tree_lists_each_dependency_once`, `regression_test_present` | `neighbours_lists_each_dependency_once`, `add_edge_idempotent` |
| `fix-merge-3way` | 67 | 5/8 false | all true | `nested_same_change_agrees` | `deletion_applies_flat`, `deletion_applies_nested` |
| `fix-ledger-replay` | 71 | 6/8 false | all true | `parity_duplicate_void` | `parity_void_before_post`, `parity_prefix_sweep` |

In every row the counter passes **every** thin criterion — the symptom patch is a
genuine pass under a thin oracle, which is the whole point of the oracle axis.

What this evidence does **not** establish: that a real weak model writes the counter.
The overlays are authored patches, chosen to be the plausible shortcut; they prove the
instrument can separate, not that the tiers will. Only the screen below can say that,
and it costs money.

## The oracle axis: a criterion slice, not an arm

The design specifies model × oracle-quality as a 3 × 3 crossing — nine arms, 405 spawns,
plus an arm → (tier, oracle) resolver in `calibration.py`. **This bank realises the same
experiment with three arms.** The reasoning, recorded here because it is a deliberate
departure from the spec:

The crossing is **open-loop** — the design says so itself. The arm produces an artifact
and the verifier grades it afterwards; the oracle never reaches the spawn (these arms are
`single-session` and run no gate, and `verify.py` never enters the workspace). Three
same-model arms differing only in `verify.py` would therefore draw three samples from the
*same* artifact distribution. Grading one artifact at all three levels is the same
experiment for a third of the spend — and it makes the nesting (thin ⊆ standard ⊆ strong)
exact per artifact instead of true only in expectation, which is strictly better for
estimating the interaction.

So each `verify.py` emits one criterion dict covering all three levels, and
[`oracles.toml`](oracles.toml) records which criteria belong to which level, per task.
The exit code gates on **standard** only — the `model-tier-v1` contract — so the headline
pass rate stays comparable across banks, and `[verify] hard_criteria` remains the
capability-gated subset of standard that `calibration.py` reads today.

**What still has to be built before the oracle result renders:** `calibration.py` has no
oracle axis. Reporting each tier's slope across thin → standard → strong needs a slicer
that reads `oracles.toml` and recomputes the hard fraction per level. That is analysis
over an existing ledger — it can be written after the run — and it stays gated behind
**ADR-0008**, which is not accepted. The bank does not depend on it; the oracle *reading*
of the bank does.

The design's honest limitation (b) — that the standard → strong contrast is not protected
by the admission screen and could come back null for measurement reasons — is answered as
far as authoring can answer it: on **every** task, the `counter-strong` overlay passes the
whole standard oracle and fails at least one strong criterion, and a test asserts it. The
strong oracle has demonstrable headroom over standard. Whether real models land in that
gap is exactly what the run would measure.

## The decision statistic: one draw per trial

`calibration.py` computes every (arm, task) cell from `hard_criteria` **alone**, and a
trial is **one Bernoulli draw**: it passes iff *every* hard criterion is true. That is
ADR-0009, and it replaces the pooled estimator ADR-0007 D3 specified.

**Why, measured.** The pooled estimator counted a task's `k` hard criteria as `k`
independent draws (`successes = Σ true hard`, `n = Σ total hard`). On this bank family
they are not independent — they are the same draw. Over every completed
multi-criterion trial on the committed `ledger/model-tier-v1.jsonl` — 175 trials, 7
tasks, 5 arms — the hard set came out **all-true or all-false, 175 times out of 175**.
The whole histogram is `(2 criteria, 0 true) × 6`, `(2, 2) × 144`, `(3, 3) × 25`.

Pooling therefore multiplied each interval's `n` by `k` and bought nothing, narrowing
every CI by roughly `√k` and licensing repeat counts that cannot resolve the cells they
were sized for. The two concrete casualties are the two numbers the first plan rested
on, and both are re-derived below: the matrix's `--repeats 2` and the control's
`--repeats 5`.

The conjunction is the honest single draw whether or not the correlation holds — if
criteria ever come apart, an all-pass draw is conservative rather than inflated. So the
scorecard now prints **mixed-hard trials** (some hard criteria passed, others failed)
straight off the ledger: at 0 the estimator is exact, above 0 it is conservative and
ADR-0009 asks to be re-opened. The assumption is checkable rather than asserted.

**No committed reading moves.** Because the criteria are perfectly correlated the
per-trial point estimates equal the pooled ones exactly; only the intervals widen.
`model-tier-v1` still reads 1/7 on-diagonal, `fix-nonlocal-parse` still indeterminate,
still 40/60/80/100/100 — pinned by a test against the committed ledger. This is a
re-estimation, not a revision of the record.

### How `hard_criteria` is derived

> A criterion is admitted iff, through the real verifier, it is FALSE on the untouched
> fixture, FALSE on `counter/`, and TRUE on `solution/`. Standard-level admissibles
> come first, then strong-level ones, stopping at three and never below two.

The rule exists because the first authoring picked by hand and handed the symptom patch
a free hard criterion on five tasks. It is unchanged. Its **justification** is not:
"three" was defended as a power target ("six pooled draws at repeats=2"), which was the
pooled estimator's arithmetic and is now known to be empty — `k` does not move the draw
count, it moves the difficulty of the conjunction. Three survives for two reasons that
do: it is the only lever authoring has against the standard-oracle ceiling that
saturated v1, and a one-criterion hard set puts the entire tier verdict on a single
verifier assertion. Two is the floor. `fix-clamp2` admits only two — it is the weak
anchor and has no third independent consumer to check. **Power now comes from repeats,
and only from repeats.**

### Where the overlays land, per-trial

The decision statistic is contracted on three positions, and the test suite measures all
of them through the real verifiers on every task:

| overlay | per-trial draw | what it proves |
|---|:--:|---|
| `fixtures/` alone | **0** | nothing is banked before the arm does anything |
| `counter/` | **0** | the symptom patch cannot reach the bar |
| `solution/` | **1** | the bar is reachable |

`counter-strong/` is the fourth overlay and is deliberately **not** one of the three: it
belongs to the oracle axis, not the tier axis. Under the pooled estimator it landed at
1/3–2/3 of the hard set on every rung (0.33 on `fix-tz-window`, `fix-merge-3way`,
`fix-ledger-replay`; 0.5 on `fix-clamp2`; 0.67 on the rest) — squarely in the
CI-overlapping middle that reads indeterminate. Per-trial there is no middle: it fails
at least one hard criterion everywhere and scores **0**, determinate. A test pins that
side, so the reading cannot drift back into ambiguity unnoticed.

**Recorded consequence.** On five tasks the last admissible criterion is a strong-level
one, so `hard_criteria` is no longer a subset of `standard` as it was in v1: the pass
bar on those tasks is "fixed the root cause, checked independently". Exit codes still
gate on `standard`, so the two are decoupled. Three criteria that were in the v1-shaped
hard sets are gone for cause — `clamp_above_preserved`, `real_cycle_still_raises` and
`true_conflict_still_reported` are TRUE on the untouched buggy source, i.e. regression
guards a do-nothing arm banks for free, not capability checks at a displaced consumer.
They remain in the standard oracle and still gate the exit code.

Raising the bar creates a floor hazard, and it is guarded: a task **no** arm can do
would score 0.0 everywhere, the cheapest arm would be trivially "within ε of the best",
and the row would read `weak` — a floored task masquerading as one the weak tier
suffices for, in exactly the direction that would license retiring the dear tiers.
`empirical_right_tier` now returns `indeterminate` when the best arm's mean is 0.

## The admission screen (Part B): every buyable rung, priced and pre-registered

The design admits a task only after a two-arm screen — weak and strong, `--repeats 5`.
The first authoring skipped it entirely; the first repair scoped it to **four of the
nine rungs** (the mid band) and let the other five into the matrix on authoring evidence
alone. That is the weakest place to trust authoring: every rung's hard criteria are
stated as verbatim bullets in the fixture README, and the task instruction points the
model at that README, so the discovery step the displaced-cause shape is meant to gate
on is partly handed over. Whether a real weak model writes the `counter/` patch or reads
the contract and writes the `solution/` one is not a question authoring can answer at
any price — and v1's own evidence has haiku acing 6/7 tasks including
`fix-nonlocal-urlkey`, the same displaced-cause shape.

The scope is now a machine-readable file, [`screen-plan.toml`](screen-plan.toml), and a
test asserts the rule that keeps it honest: **every rung the matrix can buy is named in
a screen block, and a rung that is not screened is not buyable.** Keeping the scope in
prose is exactly how it drifted.

| block | rungs | band | arms × tasks × repeats | trials |
|---|---|---|---|--:|
| **A — previously unscreened** | `fix-clamp2`, `fix-graph-cycle`, `fix-merge-3way`, `fix-ledger-replay` | weak (1) + strong (3) | 2 × 4 × 5 | 40 |
| **B — mid band** | `feature-ndjson-merge`, `fix-strip-unicode`, `fix-tz-window`, `fix-decimal-round` | mid (4) | 2 × 4 × 5 | 40 |

Block A is bought first: it is the block carrying the unmeasured assumption, and a
dropped rung there changes the matrix most (the weak band holds one rung, so losing
`fix-clamp2` empties it). Block B is the original stage 0, unchanged in scope, arms,
repeats and decision rule.

`fix-quota-rollup` is the sealed holdout, is **not** screened, and is therefore **not
buyable**: `--include-holdout` is out of bounds for this bank until it has a screen of
its own. `control-nonlocal-parse` is not a rung and is not screened; it is bought at
repeats=10 and read by the control rule.

```sh
uv run fathom run model-tier-v2 \
  --scenarios-dir scenarios/model-tier-v2-screen \
  --tasks fix-clamp2,fix-graph-cycle,fix-merge-3way,fix-ledger-replay \
  --repeats 5 --max-budget-usd 2
```

**Decision rule, fixed before the spend**, and read off per-trial pass counts (0..5 per
arm):

| verdict | condition | consequence |
|---|---|---|
| SATURATED | `haiku` passes 5/5 | the weak tier already does it — no boundary information. **DROP** |
| FLOORED | `opus5` passes 0/5 | no tier does it — the instrument's ceiling, not a cut. **DROP** |
| ADMITTED | otherwise | the rung enters the matrix |

`SEPARATING` is an informational label on top of ADMITTED — one-sided Fisher exact
`p ≤ 0.05`, which at repeats=5 needs `haiku ≤ 1/5` against `opus5` 5/5. It is
deliberately **not** an admission bar: requiring it would demand of a single rung, at
n=5, the evidence the whole matrix is bought to produce. If every rung in a band drops,
that band is empty and no cut through it is testable; if every rung drops, the matrix is
not bought at all.

The screen is not an extra purchase: its arms resolve to the same `config_hash` as the
matrix arms, so the matrix resumes over it (a test asserts the hashes match).

## The planned matrix

```sh
uv run fathom smoke
uv run fathom validate model-tier-v2 --strict
uv run fathom verify-arming --scenarios-dir scenarios/model-tier-v2

# stage 0a — screen block A: the rungs the first plan left unscreened.
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2-screen \
  --tasks fix-clamp2,fix-graph-cycle,fix-merge-3way,fix-ledger-replay \
  --repeats 5 --max-budget-usd 2

# stage 0b — screen block B: the mid band. Apply the decision rule to both blocks
#            and DROP the rungs that fail before anything else is bought.
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2-screen \
  --tasks feature-ndjson-merge,fix-strip-unicode,fix-tz-window,fix-decimal-round \
  --repeats 5 --max-budget-usd 2

# stage 1 — the positive control at the repeats its rule needs (10, not 5).
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2 \
  --tasks control-nonlocal-parse --repeats 10 --max-budget-usd 2

# stage 2 — the matrix over the ADMITTED rungs only, resuming over both screens.
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2 \
  --tasks <admitted rungs> --repeats 5 --max-budget-usd 2
uv run fathom report model-tier-v2
```

**`--scenarios-dir` is load-bearing here, and this bank has a trap.** The default
`scenarios/` glob also resolves to exactly **three** arms (`bare`, `series`,
`single-long-session`), so omitting the flag prints an identical count line and
silently runs the wrong experiment. The plan now prints an `arms:` line naming them,
which is the tell to read before letting a matrix run on; the ledger's `scenario`
field is the after-the-fact confirmation.

**Stage 2 is `--tasks`-scoped, not a bare matrix run.** A bare run would re-admit the
rungs the screen just dropped. The admitted list is written into the run notes when the
screen is read, and the sealed holdout is never in it.

| stage | arms × tasks × repeats | new trials | ceiling @ $2 cap |
|---|---|--:|--:|
| 0a — screen, block A | 2 × 4 × 5 | 40 | $80.00 |
| 0b — screen, block B | 2 × 4 × 5 | 40 | $80.00 |
| 1 — positive control | 3 × 1 × 10 | 30 | $60.00 |
| 2 — matrix over R admitted rungs | 3 × R × 5 − 10R done | 5R | $10R |
| **program total, if all 8 rungs are admitted** | 150 distinct trials | 150 | **$300.00** |
| **program total, if 4 are admitted** | 110 distinct trials | 110 | **$220.00** |

The matrix cost is a function of the screen's result, which is the point of buying the
screen first: every rung the screen drops removes 15 unbought trials from stage 2 and
subtracts nothing from what the run can conclude, because a saturated or floored rung
was never going to carry a boundary.

**Read the cost numbers correctly — this is where the first plan went wrong.**
`--max-budget-usd` is a **per-spawn** cap, not a run total: fathom has no total-run cap
at all. The first plan passed `--max-budget-usd 100`, which *raised* each spawn's cap
from the $5 default to $100 — a 20x loosening of the only runaway guard — while reading
in the report as a $100 program rail. The plan's ceiling line now derives from the cap
that will actually bind, so the flag's real effect is visible before the spend: the
same matrix prints $108 at `--max-budget-usd 2` and **$270** with no flag at all.

`$2` per spawn is chosen against the record, not the rail: across 1059 committed spawns
the max is $2.76 and only 8 exceed $2, none of them on a model-tier bank
(`model-tier-v1`: mean $0.236, max $0.576). It should never bind — and if it does, the
trial is visible in the ledger rather than silently truncated, so a spawn that lands
within a few percent of the cap is re-run at a higher cap before the matrix is read.

**The binding guard is cumulative, not per-invocation:** read the summed `cost_usd_est`
out of `ledger/model-tier-v2.jsonl` between stages and stop at the rail. At v1's
observed rates ($0.236/trial mean, $0.576 max) a 150-trial program lands near **$35-55**
against a $300 worst case with no precedent in the record. That the aggregate ceiling
exceeds a $100 rail is a decision taken deliberately, and the arithmetic is stated
rather than hidden: an honestly-powered matrix cannot fit a $100 *ceiling* at $2/spawn
(the control alone is $60), so the rail is read as **observed cumulative cost**, checked
between stages, or the program is cut down by dropping rungs — never by dropping the
control, which puts the run back in v1's uninterpretable-null position.

**Power, stated plainly — and re-derived at one draw per trial.** The first plan bought
`--repeats 2` on the pooled estimator's arithmetic. Under ADR-0009 that arithmetic is
gone, and the re-derivation is executable
(`tests/test_calibration.py::TestPerTrialScoring`):

| repeats | noiseless mid rung (haiku 0/n, sonnet5 n/n, opus5 n/n) |
|--:|---|
| 2 | **indeterminate** — 2/2 [0.34, 1.00] overlaps 0/2 [0.00, 0.66] |
| 3 | **indeterminate** — 3/3 [0.44, 1.00] overlaps 0/3 [0.00, 0.56] |
| 4 | `mid`, determinate — 4/4 [0.51, 1.00] clears 0/4 [0.00, 0.49] |
| 5 | `mid`, determinate |

Four is the first repeat count at which a **perfect** contrast separates at all. The
matrix is bought at **five**, because real arms land between the overlays and a rung
whose arms sit at 0.4 and 0.8 is indeterminate at four however clean the world is. Five
is a floor, not a guarantee: it is the cheapest count that is not provably insufficient.

That is also the honest limit of this program. `--repeats 5` gives the screen power to
call a rung saturated and gives the matrix a determinate reading on rungs that separate
cleanly; it does not give it power to *move a threshold*. Moving a tier cut needs the
cross-distribution rule in the recalibration playbook. **No conclusion of the form "tier
X should be dropped" is available from this bank**, and none is available at any stage
if the control does not separate.

## Decisions this bank made where the design left room

- **Bank name `model-tier-v2`**, per the design. Ledger lands at
  `ledger/model-tier-v2.jsonl`; `model-tier-v1` is untouched and stays the baseline.
- **Three arms, not nine** — the oracle axis is a criterion slice (above).
- **Model ids are undated aliases** (`claude-haiku-4-5`, `claude-sonnet-5`,
  `claude-opus-5`), matching the choosing-models lineup. A dated snapshot pins the bank
  to a model that stops being served.
- **Effort is `high` on all three arms.** On Opus 5 thinking is on by default and
  disabling it is rejected above `high`, so `high` is the setting that keeps the three
  arms comparable rather than the setting that maximises any one of them.
- **Every task declares a `[gate] run`** — the shipped suite, green on the untouched
  fixture — even though these arms never run it. It makes the gate property *verifiable*
  rather than unverifiable (`validate --strict` is clean at 27 pass / 0 fail / 0 warn /
  0 unverifiable) and leaves gated strategies available without a bank edit. No
  scenario declares `[gate] extra`. The command names only paths that exist in the
  staged workspace, and a test **executes** each one from the workspace to prove it
  runs — the ablation-v2 defect was a gate command carrying a literal `/path/to/...`
  that the strategy handed to the shell verbatim, and a string that is never executed is
  a string nobody checks.
- **`timeout_s = 180` on every verifier.** These verifiers shell out to the unittest
  suite up to three times (`no_regression`, then the two halves of the regression swap);
  the 60 s default would time out and score the trial an error.
- **`regression_test_present` is anchored at the root-cause module.** A patch that never
  touches that module leaves the swap a no-op, so the criterion reads false. That is
  deliberate — on a displaced-cause task it doubles as a root-cause detector — but it
  means the criterion is not purely about test-writing discipline on this bank, and a
  reader comparing it to v1's should know that.

## Open: the second blind rating

The design's acceptance criteria ask for **two blind raters**, as v1 had. `scores.toml`
carries **one**. The bank was authored in a single non-interactive session with no way to
convene a second, blind rater, so this is an open pre-run step, not a completed one. To
keep the gap cheap to close, `scores.toml` records the full per-axis breakdown for every
task, and a test asserts the axes sum to the score — a second rater can disagree on a
named axis rather than re-derive a number. Until that rating exists the band
populations, and therefore the confusion matrix's rows, are provisional.

The most likely axis to move is `fix-decimal-round`'s domain score, taken as regulatory
(+12) because half-away-from-zero rounding of money is an accounting rule. At +8 it
scores 50 and the 55 edge loses its lower rung.

## Layout

```
tasks/model-tier-v2/
  bank.toml            name, dataset_version, holdout
  scores.toml          per-task rubric scores, per-axis breakdown, [control] rule
  oracles.toml         thin/standard/strong criterion sets per task
  screen-plan.toml     admission-screen scope, blocks and decision rule
  bankverify.py        shared, scenario-blind verifier helpers
  <task>/
    task.toml          instruction, limits, [verify], [gate]
    verify.py          emits all three oracle levels; exit code gates on standard
    fixtures/          staged into the workspace: buggy package + a suite that
                       passes on the bug
    original/          harness-side stash for the regression swap (byte-identical
                       to the fixture)
    solution/          reference fix        — satisfiability
    counter/           symptom patch        — violability, thin passes
    counter-strong/    standard-passing fix — strong-oracle headroom
```

Arms: `scenarios/model-tier-v2/{haiku,sonnet5,opus5}.toml`, identical but for `model`.

Tests: `tests/test_bank_model_tier_v2.py` (stdlib-runnable;
`python tests/test_bank_model_tier_v2.py`). It runs the verifiers over every overlay and
takes about two minutes — the cost of proving the bank before spending on it. The
statistics behind the plan are tested separately and cheaply in
`tests/test_calibration.py` (per-trial scoring, the repeat re-derivation, the Fisher
control rule, and the committed-v1-reading regression guard).
