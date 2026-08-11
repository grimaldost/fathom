# model-tier-v2 — the tier-separating bank, authored and validated (unrun)

**Date:** 2026-08-11 · **Bank:** `model-tier-v2` · **Spend:** $0 · **Ledger:** none

The bank the recalibration playbook has been calling its "known limitation" now exists.
It is authored, validated and offline-demonstrated; it has not been run. This note
records what was built, what the offline evidence establishes, and — the part a reader
needs most — what it deliberately does not.

Full detail lives with the instrument, in
[`tasks/model-tier-v2/README.md`](../../tasks/model-tier-v2/README.md). Design of record:
[`docs/specs/2026-07-14-tier-separating-bank-design.md`](../specs/2026-07-14-tier-separating-bank-design.md).

## Why

`model-tier-v1` is saturated. Six of its seven scored tasks are aced by every tier, no
task resolves empirically to mid or strong, and a 10/10 cell carries a Wilson 95% CI of
[0.72, 1.00]. Its on-diagonal 1/7 has reproduced three times, and each time the honest
reading was that the null is manufactured by the bank rather than observed about the
rubric. The CRAF-B11 question — *does the choosing-models score separate model tiers on
outcome?* — has no power on that instrument. This bank is the instrument with headroom.

## What was built

Nine bug-fix tasks, each planting a displaced cause: the fault surfaces where the
instruction points and the fix belongs somewhere a second, unnamed consumer also depends
on. Scores span 20 to 71 on the pinned model-complexity rubric. Three arms —
`haiku` / `sonnet5` / `opus5`, identical but for `model`, undated aliases. Plus a tenth
task, `control-nonlocal-parse`, which is a positive control rather than a rung (added in
the repair pass below). Ten tasks, one sealed holdout, nine in the run set.

Every task ships three harness-side overlays and every one of them was run through the
real verifier:

| what | claim it settles | result |
|---|---|---|
| `fixtures/` untouched | the arm has something to fix | 5-6 of 8-9 criteria start false on all nine tasks |
| `solution/` | the verifier is satisfiable — no arm is asked the impossible | every criterion true, exit 0, on all nine |
| `counter/` | the criteria are violable, and the separation mechanism is real | passes **every** thin criterion, fails ≥1 standard criterion, on all nine |
| `counter-strong/` | the standard→strong contrast is not vacuous | passes the **whole** standard oracle, fails ≥1 strong criterion, on all nine |

`tests/test_bank_model_tier_v2.py` is that evidence as a gate: 17 tests, 117 subtests,
36 verifier passes, ~2 minutes, stdlib-runnable.

`fathom validate model-tier-v2 --strict`: **27 pass, 0 fail, 0 warn, 0 unverifiable**.
`fathom verify-arming --scenarios-dir scenarios/model-tier-v2`: 3 arms, 0 declaring a
treatment axis — model-only controls, so arming is structurally satisfied with zero
spawns and nothing is deferred.

## The oracle axis, at a third of the design's cost

The design specifies model × oracle-quality as nine arms and 405 spawns. This bank runs
three arms and gets the same experiment, because the crossing is **open-loop**: the arm
produces an artifact, the verifier grades it afterwards, and the oracle never reaches the
spawn (single-session arms run no gate; `verify.py` never enters the workspace). Three
same-model arms differing only in `verify.py` would sample the same artifact distribution
three times. So each verifier emits one criterion dict covering thin ⊂ standard ⊂ strong,
`oracles.toml` records the levels, and the exit code gates on standard — the v1 contract,
so headline pass rates stay comparable. The nesting becomes exact per artifact instead of
true in expectation, which is strictly better for estimating the interaction.

The design's own worry about this axis — that the standard→strong leg could come back
null for measurement reasons — is answered as far as authoring can answer it: on every
task a patch exists that satisfies the entire standard oracle and still fails a strong
criterion, and a test asserts it.

## Repair pass (2026-08-11, same day): four blocking defects, none of them cosmetic

An adversarial review of the authored bank returned `needs_repair`. All four blocking
findings reproduced against the code and the real verifiers, and all four are fixed
here. They are recorded in full because three of them are defects of *reasoning about
the instrument*, which is the class this bank exists to avoid.

**1. The decision statistic was diluted on five of eight run tasks.** `calibration.py`
computes each (arm, task) cell from `hard_criteria` alone. On `fix-clamp2`,
`fix-tz-window`, `fix-merge-3way`, `fix-ledger-replay` and `fix-graph-cycle` the
symptom patch already satisfied one hard criterion, so its cell scored 0.5, not 0 — and
a 0.5-vs-1.0 cell is CI-overlapping, i.e. *indeterminate*, which is the off-diagonal
branch. Simulated through fathom's own `empirical_right_tier` under the noiseless
alternative (the rubric is exactly right; every arm behaves as the bank's overlays
predict), the shipped variant ceilings at **4/8 on-diagonal with 4/8 indeterminate at
repeats=2, and still 5/8 at repeats=5** — $240 for an instrument that cannot reach its
own answer in a perfect world. Three of the diluting criteria (`clamp_above_preserved`,
`real_cycle_still_raises`, `true_conflict_still_reported`) were TRUE on the untouched
buggy source: regression guards a do-nothing arm banks for free, not capability checks.
`hard_criteria` is now **derived** — admitted iff false on the fixture, false on the
counter, true on the solution — and the test suite re-derives it from the overlays and
compares. The derived variant reaches **9/9 at repeats=2 with no extra spend**. The
suite's gap is fixed too: it asserted only that the counter failed *some standard*
criterion, never that it failed every *hard* one, which is exactly how this shipped.

**2. There was no positive control, and the owner's rule makes an uninterpretable null
destructive.** Added: `control-nonlocal-parse`, v1's `fix-nonlocal-parse` ported
verbatim — the one task on the committed ledger with an observed monotone gradient
(haiku 2/5 → sonnet5 4/5 → opus5 5/5). Pre-registration below.

**3. The mid band was load-bearing and unscreened.** The design's own Part B screen is
now stage 0, scoped to the four mid rungs, with its decision rule fixed before the
spend (see the bank README).

**4. The cost control did the opposite of what the first report claimed.**
`--max-budget-usd` is **per-spawn**; passing `100` *raised* each spawn's cap from the
$5 default to $100 — a 20x loosening of the only runaway guard — while the plan line,
whose ceiling was a hardcoded $2/trial constant, printed the same reassuring $96 either
way. The ceiling now derives from the cap that will actually bind: the same matrix
prints $108 at `--max-budget-usd 2` and **$270** with no flag. Two related fixes fell
out: the plan prints an `arms:` line (the `--scenarios-dir` trap was invisible in a
count-only plan), and `--tasks` now exists, without which "screen the mid band before
paying for the mid arm" is not a command anyone can type.

One more defect surfaced while repairing #1 and is fixed with it: raising the pass bar
made the **floor** dangerous. A task no arm can do scored 0.0 everywhere, the cheapest
arm was trivially "within ε of the best", and the row read `weak` — a floored task
indistinguishable from one the weak tier genuinely suffices for, biased toward retiring
the dear tiers. `empirical_right_tier` now returns `indeterminate` when the best arm's
mean is 0. It cannot change any committed reading: every v1 task's best arm is at 1.0.

## Pre-registration: what licenses each branch of the owner's rule

Fixed before any spend, so no branch is chosen after seeing the numbers.

**The control is read by its own rule, not by the confusion matrix.** "Separates" means
`haiku`'s pooled Wilson CI is **disjoint from** `opus5`'s on the control's two hard
criteria. It deliberately is not "the control lands on-diagonal": at the control's own
observed v1 rates the cheapest-adequate statistic reads *indeterminate* even at
repeats=5, because `sonnet5` at 0.8 overlaps `opus5` while sitting outside ε. That is a
correct reading of "which tier is cheapest-adequate" and a useless one for "does the
ladder separate at all", which is the control's only job.

That rule also fixes the control's repeat count. At v1's observed rates:

| repeats | pooled draws | haiku | opus5 | disjoint? |
|--:|--:|---|---|---|
| 2 | 4 | 2/4 → [0.150, 0.850] | 4/4 → [0.510, 1.000] | no |
| 3 | 6 | 2/6 → [0.097, 0.700] | 6/6 → [0.610, 1.000] | no |
| 5 | 10 | 4/10 → [0.168, 0.687] | 10/10 → [0.722, 1.000] | **yes** |

So stage 1 at `--repeats 5` is the *minimum* that can answer the control's question, not
padding: bought at repeats 2 the control cannot separate even when the ladder does, and
the whole run would be uninterpretable for want of 9 trials.

| observed | reading | what is licensed |
|---|---|---|
| control separates **and** ladder separates | the score predicts the tier on this shape | report the confusion matrix; threshold moves still need the `--repeats 5` matrix and the recalibration playbook's cross-distribution rule |
| control separates, ladder does **not** | the instrument works; these rungs have no headroom | a statement about the BANK, not the rubric. Reshape or retire rungs. No tier conclusion. |
| control does **not** separate | the instrument or the lineup moved | **nothing follows about tiers from any part of the matrix.** Diagnose the control first. |
| any arm floors (best mean 0 on a task) | no purchase on that task | row is `indeterminate` by construction; excluded from the matrix reading |

The deletion branch — any conclusion of the form *"tier X should be retired"* —
requires the control to separate **and** the ladder not to, **and** a `--repeats 5`
matrix. It is not available from the staged program below at any stage. With K=9 the
binomial 95% CI on an on-diagonal count spans both live hypotheses (5/9 → [0.21,
0.86]), and repeats cannot raise K.

**Simulated instrument ceiling, from the committed files.** Grading the real overlays
through the real verifiers and driving fathom's own `empirical_right_tier` under the
noiseless alternative: **9/9 ladder rungs on-diagonal and determinate at repeats=2**,
unchanged when one hard criterion in the below-tier arm is flipped true by luck. The
same simulation on the pre-repair hard sets gave 4/8 with 4/8 indeterminate. The
control's own row is indeterminate there by construction, as above — it is not one of
the nine and is excluded from the on-diagonal count.

## The plan, and the rail

```sh
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2 --repeats 2 \
  --max-budget-usd 2 --dry-run
# fathom run: bank=model-tier-v2  scenarios=3  tasks=9  repeats=2
# arms:     haiku, opus5, sonnet5
# planned:  54 trials (0 already done)  ceiling: $108.00
```

Staged, so each invocation is decidable on its own and the screen's trials are reused
by the matrix (identical `config_hash`, asserted by a test):

| stage | arms × tasks × repeats | planned | ceiling @ $2/spawn |
|---|---|--:|--:|
| 0 — saturation screen | 2 × 4 × 5 | 40 | $80.00 |
| 1 — positive control | 3 × 1 × 5 | 15 | $30.00 |
| 2 — matrix, resuming over 0 and 1 | 3 × 9 × 2 − 22 | 32 | $64.00 |
| **program** | 87 distinct trials | 87 | **$174.00** |

**The aggregate ceiling exceeds the $100 program rail, and that is a decision to take
deliberately rather than a number to round down.** A complete matrix *with* the control
is 54 trials = $108 on its own, so no version of this program fits a $100 ceiling at a
$2/spawn cap; dropping the control puts the run back in v1's uninterpretable-null
position. Against the record the expected spend is **$22-55**: across 1059 committed
spawns the max is $2.76 and `model-tier-v1` averaged $0.236/trial. The binding guard is
therefore the cumulative `cost_usd_est` read out of the ledger between stages, stopping
at $100 — which is what the per-spawn cap cannot do.

**A trap specific to this bank:** the default `scenarios/` glob also resolves to exactly
three arms, so omitting `--scenarios-dir` runs `bare` / `series` /
`single-long-session` instead. The plan's new `arms:` line is the tell to read before
letting a matrix run on.

## What this does not establish

- **The admission screen has not run.** It is priced and pre-registered as stage 0
  (40 trials, $80 ceiling, ~$9-20 observed) but nothing has been spent. The offline
  demonstrations prove the *instrument* can separate; only the screen proves the
  *tiers* do.
- **The counters are authored patches**, chosen as the plausible shortcut. They are not
  evidence that a weak model writes them — and two are weaker than that: `fix-clamp2`'s
  counter deletes a working branch, which no model would write, so it is a violability
  probe rather than a model of the shortcut. (The review also called `fix-strip-unicode`'s
  counter a strawman for using `encode('ascii','ignore')`; that is the *fixture's* planted
  bug. The counter is `NFKD` then `encode('ascii','ignore')`, which is the canonical
  copy-paste idiom and a realistic shortcut. Recorded because the distinction is the
  difference between a strawman and a genuine discovery test.)
- **`scores.toml` has one rater, not two.** The design asks for two blind raters. The
  bank was authored in a single non-interactive session with no way to convene a second.
  The per-axis breakdown is recorded in full so the gap is cheap to close, and a test
  asserts the axes sum to the score. Until then the band populations are provisional.
- **The weak band holds one task.** `fix-strip-unicode` was authored as a ~22 rung and
  scored 40; once a task is substantial enough to plant a displaced cause in, the
  rubric's cross-shape floor lifts it to at least 26. So the "weak tier suffices for
  trivial work" leg will rest on K=1, and repeats cannot fix K. The 25 edge has one rung
  (Δ5); the 55 edge is double-covered (Δ1 below, Δ5 above), which the design expected the
  rubric to refuse.
- **No oracle result renders yet.** `calibration.py` has no oracle axis; the slope
  estimator that reads `oracles.toml` is unbuilt and stays gated behind **ADR-0008**,
  which is unaccepted. That is analysis over an existing ledger and can follow the run.
  When it is built it must compute the slope on the capability subset only: the two
  hygiene criteria are test-writing discipline and would dominate the thin→standard leg
  (`regression_test_present` is 0/5 for four of five v1 arms, and 0/15 vs 15/15 across
  humble-vs-super-v3's bare/skill contrast). Recorded in `oracles.toml` beside the data.
- **ADR-0008 is still `Status: Proposed`,** and the design of record requires it accepted
  *before any build or spend*. The bank ships the oracle criterion slice, so the gate
  covers the build that already happened, not only the unbuilt analysis. Accepting or
  amending it is a precondition of stage 0, not a follow-up.
- **`fathom smoke` has not been re-read since the repair.** The recorded 7/8 predates
  it, and nothing here touches spawn isolation — but the gate is written as a fresh
  read immediately before any spend, so it is a stage-0 precondition, not a carried-over
  result. (No spawn of any kind was made in this pass; the repair was authoring only.)
- **At `--repeats 2` a cell pools 4-6 Bernoulli draws** (Wilson 95% CI on 6/6 ≈
  [0.61, 1.00]). Stage two can show the ladder's shape and catch a ceiling. It cannot
  move a tier cut, and nothing of the form "tier X should be retired" follows from it.
  The 9/9 the derived hard sets reach in simulation is a statement about a noiseless
  world where every arm lands exactly on an overlay; real arms land between them, and a
  cell that comes out at 0.5 is indeterminate no matter how many repeats are bought.
- **The instruction points the model at a README that states the full contract**,
  including the second consumer the instruction itself never names. That hands over
  part of the discovery step the displaced-cause shape is meant to gate on. It is not
  repaired by authoring — a README that hid the contract would make the strong criteria
  unknowable and unfair — so it is the empirical question stage 0 exists to settle.

## Incidental: `fathom smoke` is 7/8, and the failure is not credentials

Run during this authoring pass: every credential-dependent check **passes** (isolated
config, credential-only spawn, stream parsing, default-deny refusal, system-prompt
injection, both plugin-mount checks). The single failure is
`engine-boundary: non-bypass permission mode reaches the spawned CLI — engine spawned no
claude invocation (boundary not exercised)`, which concerns the convoy series arm and is
untouched by this bank's single-session arms. Recorded here because a stale note had the
suite failing 5/8 on an expired OAuth session; that is no longer the failure mode.
