# model-tier-v2 — the tier-separating calibration bank

Nine bug-fix tasks on a graded difficulty ladder, built to the design of record
[`docs/specs/2026-07-14-tier-separating-bank-design.md`](../../docs/specs/2026-07-14-tier-separating-bank-design.md).
The arms are model tiers (weak / mid / strong); the ladder is meant to show where each
tier's capability ceiling falls.

**Authored, not run.** No ledger exists for this bank. Everything below is offline
evidence produced by the verifiers themselves, at zero spend.

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

**How to read it — by its own rule, not by the confusion matrix.** "Separates" means
`haiku`'s pooled Wilson CI is disjoint from `opus5`'s on its two hard criteria. Not
"lands on-diagonal": at its own v1 rates the cheapest-adequate statistic reads
*indeterminate* even at repeats=5, because `sonnet5` at 0.8 overlaps `opus5` while
sitting outside ε — a correct answer to "which tier is cheapest-adequate" and a useless
one for "does the ladder separate at all". The rule fixes the repeat count, too:
haiku-vs-opus5 CIs are [0.150, 0.850] vs [0.510, 1.000] at repeats=2 (overlapping),
[0.097, 0.700] vs [0.610, 1.000] at 3 (overlapping), and [0.168, 0.687] vs
[0.722, 1.000] at **5 (disjoint)**. Bought at repeats 2 the control cannot separate
even when the ladder does, so stage 1 is the minimum that answers its question.

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

## The decision statistic, and how `hard_criteria` is derived

`calibration.py` computes every (arm, task) cell from `hard_criteria` **alone**. That
makes the choice of hard criteria the whole instrument, and it is now derived from
measurement rather than picked:

> A criterion is admitted iff, through the real verifier, it is FALSE on the untouched
> fixture, FALSE on `counter/`, and TRUE on `solution/`. Standard-level admissibles
> come first, then strong-level ones, stopping at three and never below two.

The rule exists because the first authoring picked by hand and shipped **five diluted
cells**: on `fix-clamp2`, `fix-tz-window`, `fix-merge-3way`, `fix-ledger-replay` and
`fix-graph-cycle`, the symptom patch already satisfied one hard criterion, so its cell
scored 0.5 rather than 0. A 0.5-vs-1.0 cell is CI-overlapping — **indeterminate** — at
every repeat count this program can afford, and indeterminate is the off-diagonal
branch. Simulated through fathom's own `empirical_right_tier` under the noiseless
alternative (the rubric is exactly right and every arm behaves as the overlays
predict), the diluted variant ceilings at **4/8 on-diagonal with 4/8 indeterminate at
repeats=2, and still 5/8 at repeats=5** — $240 for an instrument that cannot reach its
own answer. The derived variant reaches **9/9 at repeats=2**, at no extra spend.

Three, not two, is the power target: at repeats=2 a three-criterion cell pools six
draws, and Wilson keeps 1/6 (upper 0.56) clear of 6/6 (lower 0.61) — one criterion
coming out true by luck still leaves the cell readable, where a two-criterion cell
(1/4 upper 0.67 vs 4/4 lower 0.51) goes indeterminate. `fix-clamp2` admits only two;
it is the weak anchor and has no third independent consumer to check.

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

## The admission screen (Part B): stage 0, priced and pre-registered

The design admits a task only after a two-arm screen — weak and strong, `--repeats 5`.
The first authoring skipped it as unaffordable and went straight to the 3-arm matrix.
It is now stage 0, scoped to the four rungs that need it:

```sh
uv run fathom run model-tier-v2 \
  --scenarios-dir scenarios/model-tier-v2-screen \
  --tasks feature-ndjson-merge,fix-strip-unicode,fix-tz-window,fix-decimal-round \
  --repeats 5 --max-budget-usd 2
```

40 trials, $80 ceiling, ~$9-20 observed. The four are the **mid band**, and the mid
band is where the whole boundary-placement question lives: both the 25 and the 55 cut
rest on the claim that a weak model fails these and a mid model passes them. Three
reasons to doubt it, all of which the screen settles empirically: every fixture README
states the full contract including the second consumer the instruction never names, and
the instruction points the model at that README — so the discovery step the shape is
meant to gate on is partly handed over; two of the counter overlays are violability
probes rather than plausible model output (`fix-clamp2`'s deletes a working branch —
no model writes that); and v1's own evidence has haiku acing 6/7 tasks including
`fix-nonlocal-urlkey`, the same displaced-cause shape.

**Decision rule, fixed before the spend.** Per task: if `haiku` passes every hard
criterion on all 5 repeats, that task is SATURATED — it carries no information about a
boundary and is reshaped or dropped before the mid arm is bought. If all four saturate,
the mid band is empty and the matrix is not bought at all. A task neither arm passes is
at the floor, not at a boundary.

The screen is not an extra purchase: its arms resolve to the same `config_hash` as the
matrix arms, so the matrix resumes over it (a test asserts the hashes match).

## The planned matrix

```sh
uv run fathom smoke
uv run fathom validate model-tier-v2 --strict
uv run fathom verify-arming --scenarios-dir scenarios/model-tier-v2

# stage 0 — saturation screen (see above). Read the ledger, apply the decision rule.
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2-screen \
  --tasks feature-ndjson-merge,fix-strip-unicode,fix-tz-window,fix-decimal-round \
  --repeats 5 --max-budget-usd 2

# stage 1 — the positive control, deep enough to show a gradient
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2 \
  --tasks control-nonlocal-parse --repeats 5 --max-budget-usd 2

# stage 2 — the matrix, resuming over both
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2 \
  --repeats 2 --max-budget-usd 2
uv run fathom report model-tier-v2
```

**`--scenarios-dir` is load-bearing here, and this bank has a trap.** The default
`scenarios/` glob also resolves to exactly **three** arms (`bare`, `series`,
`single-long-session`), so omitting the flag prints an identical count line and
silently runs the wrong experiment. The plan now prints an `arms:` line naming them,
which is the tell to read before letting a matrix run on; the ledger's `scenario`
field is the after-the-fact confirmation.

| stage | arms × tasks × repeats | planned | ceiling @ $2 cap |
|---|---|--:|--:|
| 0 — saturation screen | 2 × 4 × 5 | 40 | $80.00 |
| 1 — positive control | 3 × 1 × 5 | 15 | $30.00 |
| 2 — matrix, resuming over 0 and 1 | 3 × 9 × 2 − 22 done | 32 | $64.00 |
| **program total** | 87 distinct trials | 87 | **$174.00** |
| (matrix alone, if bought without staging) | 3 × 9 × 2 | 54 | $108.00 |

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
out of `ledger/model-tier-v2.jsonl` between stages and stop at $100. At v1's observed
rates the whole 87-trial program lands near **$22-55**, against a $174 worst case that
has no precedent in the record. The aggregate ceiling exceeding the $100 rail is a real
decision to take deliberately: a complete matrix WITH the control cannot fit a $100
ceiling at $2/spawn (54 trials = $108 on its own), so the rail is either read as
observed cumulative cost or the control is dropped — and dropping it puts the run back
in v1's uninterpretable-null position.

**Power, stated plainly.** At `--repeats 2` a (task, arm) cell pools 2 trials × 2-3 hard
criteria = 4-6 Bernoulli draws; a 6/6 cell carries a Wilson 95% CI of roughly
[0.61, 1.00]. Under the noiseless alternative the derived hard sets make every cell
determinate at repeats=2 — but that is a statement about a perfect world, not a claim
of power. Real arms land between the overlays, and a cell at 0.5 is indeterminate no
matter how many repeats are bought. Stage 0's `--repeats 5` is the only part of this
program with power to call a task saturated. Moving a tier cut needs the full
`--repeats 5` matrix and the cross-distribution rule in the recalibration playbook.
**No conclusion of the form "tier X should be dropped" is available from stage 2**, and
none is available at any stage if the control does not separate.

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
  scores.toml          per-task rubric scores + the per-axis breakdown
  oracles.toml         thin/standard/strong criterion sets per task
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
`python tests/test_bank_model_tier_v2.py`). It runs 36 verifier passes and takes about
two minutes — the cost of proving the bank before spending on it.
