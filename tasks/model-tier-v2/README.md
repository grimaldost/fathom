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

## The admission screen (Part B) is NOT satisfied

The design admits a task only after a two-arm screen — weak and strong, `--repeats 5`,
unanimity on every repeat. **That screen has not run: it costs money and this program
authored only.** What is done instead is the offline half — the counter/counter-strong
demonstrations above, which prove the instrument can separate. What is undone is the
empirical half, which is the half that catches a task that saturates in practice.

Concretely: the screen is 2 arms × 9 tasks × 5 repeats ≈ 90 trials, a $180 ceiling at the
$2/trial rail. That is over the rail this bank's plan was sized to, which is the reason
the first paid stage below is the full 3-arm matrix at low repeats rather than the
screen: it buys the mid arm's boundary placement with the same trials, and a task that
saturates shows up as 100% across all three arms just as visibly.

## The planned matrix

```sh
uv run fathom smoke
uv run fathom validate model-tier-v2 --strict
uv run fathom verify-arming --scenarios-dir scenarios/model-tier-v2
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2 --repeats 2 --dry-run
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2 --repeats 2 --max-budget-usd 100
uv run fathom report model-tier-v2
```

**`--scenarios-dir` is load-bearing here, and this bank has a trap.** The default
`scenarios/` glob also resolves to exactly **three** arms (`bare`, `series`,
`single-long-session`), so omitting the flag prints an identical
`scenarios=3 tasks=8 repeats=2 / planned: 48 trials` line and silently runs the wrong
experiment. The arm names in the ledger are the only tell. Always pass the flag.

| stage | arms × tasks × repeats | trials | ceiling |
|---|---|--:|--:|
| first paid stage | 3 × 8 × 2 | 48 | **$96.00** |
| full power target | 3 × 8 × 5 | 120 | $240.00 |

The ceiling is the flat $2/trial rail (C4), not an expectation: `model-tier-v1`'s
comparable 42-trial pilot cost about $6 in observed tokens, so the first stage should
land nearer $7-15. Resume makes the staging free — the key is
`(bank, dataset_version, task_id, config_hash, repeat)`, so re-invoking at `--repeats 5`
later keeps the first two repeats and pays only for repeats 3-5.

**Power, stated plainly.** At `--repeats 2` a (task, arm) cell pools 2 trials × 2-3 hard
criteria = 4-6 Bernoulli draws; a 6/6 cell carries a Wilson 95% CI of roughly
[0.61, 1.00]. That is **not** enough to call a cell saturated or to move a threshold —
it is enough to see the ladder's shape and to catch a bank that ceilings. Moving a
tier cut needs the `--repeats 5` stage and the cross-distribution rule in the
recalibration playbook. No conclusion of the form "tier X should be dropped" can come
from stage one.

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
