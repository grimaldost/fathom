# humble-vs-super-v5 — humblepowers at merged state (0.9.1), 3-arm

**Created:** 2026-08-11. **Lineage:** the task content is a byte-for-byte fork of
`humble-vs-super-v2`'s (same tasks, fixtures, `original/` stashes, per-task `verify.py`,
shared `bugfix_verify.py`), pinned by `tests/test_humble_super_v5_mounts.py`. v1–v4 are
preserved untouched.

## This is a fork, not a reproduction

Two axes moved at once, and only one of them was a choice.

| | v2 (2026-06-15) | v5 (this bank) |
|---|---|---|
| humblepowers | 0.4.0 | **0.9.1** (merged `main`, craft-collection `b7b0097`) |
| superpowers | 5.1.0 @ `6fd4507` | 5.1.0 @ `6fd4507` — unchanged |
| held-constant stack | engineering-discipline 0.1.2 + session-workflow 0.2.2 | unchanged (deliberately — see below) |
| base model | `claude-opus-4-8` | **`claude-opus-5`** |
| arms | stack-humble · super-only · stack-super | **bare · stack-humble · stack-super** |
| live tasks × repeats | 4 × 5 | **4 × 5 planned** (n=20 is a gated escape hatch, not the plan — see "Plan and cost") |
| `dataset_version` | 1 | **2** (a fork marker; the bank name already prevents a resume collision) |

**The model move was forced, not chosen.** `claude-opus-4-8` is no longer served — the
2026-08-11 lineup reconciliation recorded the strong tier as pinned to a model that had
been withdrawn, and `choosing-models`' `models.toml` now maps strong → `claude-opus-5`.
Pinning v2's model would produce a matrix that cannot run. The consequence is
unavoidable and must be carried into any reading of the results: **v5's numbers may not
be differenced against v1–v4's.** A change in the treatment and a change in the base
model are confounded in that comparison, and no arrangement of these arms separates
them. What v5 supports is the *within-v5* contrast — three arms on one model, differing
only in which plugin tree is mounted.

**The stack was deliberately not refreshed.** On `main` the two common-stack plugins now
read engineering-discipline 0.4.0 and session-workflow 0.21.0. Moving them would change
the instrument on a third axis simultaneously, and — because session-workflow 0.21.0 is
several times the corpus of 0.2.2 — would shift both disciplined arms' token and cost
baselines by an amount unrelated to the question. They stay pinned so the sole
craft-collection delta between the two disciplined arms remains *which discipline
library is mounted*. The honest cost of that choice: **v5 measures humblepowers 0.9.1
inside a 2026-06-era stack, not inside the full merged toolkit.** A merged-stack variant
is a different, larger question and belongs in its own bank.

**`bare` is back — and the floor it was meant to establish has already moved.** v2 dropped
`bare` because v1 had established the floor. v5 restores it because the base model changed.
But the claim this section carried until 2026-08-12 — that the instrument's discrimination
"has never been shown on `claude-opus-5`" — was **false, and contradicted by this repo's own
committed ledger**. `ledger/model-tier-v1.jsonl` measured an unarmed arm on `claude-opus-5`
four weeks before this bank was authored:

| arm | model | plugins | `regression_test_present` |
|---|---|---|---|
| `opus` | `claude-opus-4-8` | none | **0/30 (0%)** |
| `sonnet5` | `claude-sonnet-5` | none | 1/30 (3.3%) |
| `opus5` | **`claude-opus-5`** | none | **21/30 (70%)** |

Per task, `opus5` reads 5/5, 4/5, 1/5, 4/5, 5/5, 2/5 — **every task above 10%**. Reproduce
with `uv run python scripts-humble-v5/analysis.py criteria ledger/model-tier-v1.jsonl`.

Three things make this a real prior rather than a curiosity. The verifier is **byte-identical**
— `bugfix_verify.py` is sha256 `0b2453c4…` in `model-tier-v1`, `humble-vs-super-v1` and this
bank alike, so the same swap mechanism scored all three. The `opus`/`opus5` scenario files are
identical **except the `model` line**, so the 0% → 70% jump is attributable to the model and
nothing else. And the arm is unarmed in the same sense v5's `bare` is: `source = "none"`, no
plugins, with `Write` and `Bash` available (v5's `bare` additionally allows `Task`).

**What it is not:** a prediction on v5's own tasks. `model-tier-v1`'s six `fix-*` tasks
(`fix-clamp`, `fix-interval-merge`, `fix-money-split`, `fix-nonlocal-parse`,
`fix-nonlocal-urlkey`, `fix-titlecase`) are **none of them in this bank**, and the rate plainly
varies by task (1/5 to 5/5). What transfers is the mechanism, not the number: on
`claude-opus-5`, an unarmed model writes bug-covering regression tests unprompted at a
substantial rate, where on `claude-opus-4-8` it never did in 30 trials. v5's `bare` is
therefore expected to land **far above** the old floor — see "What Stage A is for", which is
re-registered around that expectation rather than against it. `bare`'s job in v5 is now the
**economy control**, not the calibration floor.

## What v5 can and cannot answer

The prior evidence is unusually specific about where this bank family has signal, and
pretending otherwise would waste the spend. **The numbers below come from v5's *own*
tasks** — v1 and v2 ran this exact task content under an identical tool allow-list, so
they are the relevant prior, not v3's (whose three tasks — `fix-dedup-records`,
`fix-interval-merge`, `fix-money-split` — are **not in this bank**).

Pooling the v1 and v2 ledgers over v5's four live tasks gives 16 criterion-slots. Fifteen
of them are at 100% in every arm. This is the single most important fact about the
instrument, and it is reproducible from the committed ledgers with
`python scripts-humble-v5/analysis.py criteria ledger/humble-vs-super-v1.jsonl
ledger/humble-vs-super-v2.jsonl`:

> **Every figure in the table below was measured on `claude-opus-4-8`.** v1 and v2 ran on
> the withdrawn model; v5 runs on `claude-opus-5`. The **ceilings** (the 100% rows) carry
> over as upper bounds with little risk — a criterion saturated by every arm on the older
> model is not going to develop headroom on a stronger one. The **floor does not carry
> over at all**: the `bare` column of `regression_test_present` is the one number the model
> move is known to have broken (0/30 → 21/30 on the unarmed `claude-opus-5` arm of
> `model-tier-v1`, above). Read the `headroom?` column as "headroom *between the armed
> arms*", which is what it was computed from.

| task | criterion | pooled v1+v2 (`claude-opus-4-8`) | headroom? |
|---|---|---|---|
| `feature-csv-coalesce` | `behavior_correct`, `empty_input`, `ragged_rows`, `type_coercion`, **`tests_present`** | **40/40 each** | none |
| `feature-retry-backoff` | `behavior_correct`, `zero_retry`, `jitter_bounds`, `error_propagation`, **`tests_present`** | **40/40 each** | none |
| `fix-tz-dst-normalize` | `fix_correct`, `no_regression` | 50/50 each | none |
| `fix-tz-dst-normalize` | `regression_test_present` | 44/50 — armed arms **44/45 (97.8%)** | ceilinged |
| `fix-offbyone-paginator` | `fix_correct`, `no_regression` | 50/50 each | none |
| `fix-offbyone-paginator` | `regression_test_present` | 32/50 — armed arms **32/45 (71%)** | **the only slot** |

- **Both feature tasks are fully saturated — including their test-discipline criterion.**
  Every criterion of `feature-csv-coalesce` and `feature-retry-backoff` is 40/40 in
  **every** arm, `bare` included. This is structural, not luck: those instructions
  enumerate the exact edges the verifier checks ("covering the happy path and each edge
  case SPEC.md names: empty input, ragged rows, and empty-cell / type coercion"), so
  `tests_present` is **prompted rather than elicited** — which is precisely why `bare`
  scored 100% on it while scoring 0% on `regression_test_present` in the `fix-*` tasks,
  whose instructions mention no tests at all (**both figures on `claude-opus-4-8`**; the
  0% half of that contrast is the one the model move broke). **The two feature tasks cannot produce
  quality signal in v5, and they are the dearest tasks in the bank** (≈$0.54–0.65/trial
  against ≈$0.34–0.39 for the paginator). They are retained **only as economy samples** —
  they carry two of the four task-pairs the pre-registered cost test needs (below) — and
  no quality claim may be read off them.
- **Correctness ceilings.** `fix_correct` and `no_regression` are 100% in every arm on
  every task, replicated by v3 (0/180 at n=45) and v4. They are kept as regression
  detectors — they would catch a broken fork or a model that got worse — not as
  discriminators. **No verdict may be read off them.**
- **The quality axis rests on one criterion of one task.** After the ceiling analysis
  above, the entire quality question reduces to `regression_test_present` on
  `fix-offbyone-paginator`, at n=20/arm. That is not enough. Pooled v1+v2 on that task
  reads humble-family 17/25 (68%) against super-family 15/20 (75%) — Fisher's exact
  p = 0.75 — and **the sign already flipped between runs** (v1: humble 6/10 vs super 5/5;
  v2: humble 5/5 vs super 3/5). At n=20/arm against a 70% reference, Fisher at α=0.05
  first reaches significance only at 100%, i.e. it resolves a gap of about **30
  percentage points**; against a 100% reference it resolves down to 75%, a 25pp gap. The
  effect in evidence is single-digit and unstable in sign. **v5 has no power to resolve
  the humble-vs-super quality question**, and buying n=20 does not change that. This
  paragraph once ended "treat the axis as a non-inferiority check only" — **withdrawn**: a
  non-inferiority reading needs a floor, and on `claude-opus-5` there is none (see "What
  Stage A is for"). The quality axis is **not measured** by this bank on this model.
- **The economy axis is the one that buys something.** Per-trial USD, total tokens, turns
  and wall-clock are continuous, and on v5's own task mix v2 separated `stack-humble` from
  `stack-super` by +13.1% / +21.2% / +14.3% / +15.6% — **the same sign on all four
  tasks** — at only n=5/cell. Whether the ~2× growth of the humblepowers corpus between
  0.4.0 and 0.9.1 (two new skills, several new reference files, a scripts tree) has eaten
  that advantage is the question v5 is actually powered for. Median within-cell CV across
  the 32 v1+v2 cells is **14.5%**, which is what makes the paired-by-task test below
  resolve at small n.

### What must not be concluded from this bank

Whatever v5 returns, it **cannot** support retiring either plugin. A ceilinged criterion
is an absence of measurement, not evidence of equivalence; a cost difference on four
small stdlib Python tasks does not generalise to the work either library was written
for (multi-hour sessions, design work, review loops, orchestration), none of which this
bank contains. The single axis on which these disciplines have ever been shown to move
anything is test hygiene on small self-contained fixes.

**Note the unit.** Repeats are not independent tasks. Task-level n is **4**, and after the
ceiling analysis above it is effectively **1** for quality — one criterion on
`fix-offbyone-paginator`. Any "library X is better" claim from this bank generalises over
a population of one small stdlib Python bug-fix, whatever the trial count says. The
economy axis is better off (four tasks, same sign on all four) but still speaks only to
short single-session fixes.

**One harness constant belongs in the verdict.** Plugin hooks do not fire in headless
`claude -p`, so superpowers' `SessionStart` hook — which injects its `using-superpowers`
dispatch skill — never runs. That biases *against* superpowers on quality and *for* it on
cost; superpowers still measured dearer in v1, v2 and v3, so the constant understates the
cost gap rather than manufacturing it.

## Arming — the known blocker, and how it is closed

`stack-super`'s tree is gitignored third-party content and **fathom only warns on a
missing mount**. A missing tree would degrade the contrast arm into roughly
"stack-minus-a-discipline-library" and manufacture a null that looks like a measurement.
Full decision, licensing rationale and re-vendoring recipe: `plugins/VENDORED.md`.

Observed for this bank on 2026-08-11, before any matrix spend:

```
uv run fathom verify-arming --scenarios-dir scenarios/humble-vs-super-v5
  bare:         (control - nothing to verify)
  stack-humble: [PASS/verified] declared=3 registered=['engineering-discipline', 'humblepowers', 'session-workflow']
  stack-super:  [PASS/verified] declared=3 registered=['engineering-discipline', 'session-workflow', 'superpowers']
ARMING RESULT: ALL VERIFIED
```

Both treatment arms were observed armed on real spawns, by plugin name, in the init
event. `tests/test_humble_super_v5_mounts.py` is the offline half of the same guard: it
runs with no credentials and fails if a scenario points at a tree that is not there, if
the two disciplined arms stop sharing an identical held-constant stack, if any field
other than `[plugins]` drifts between arms, or if the re-vendored superpowers bytes
differ from the measured snapshot.

## Run

Re-vendor `superpowers@6fd4507` first if this is a fresh clone (`plugins/VENDORED.md`);
the guard test skips with instructions when it is absent, and `verify-arming` is the
hard stop.

```sh
uv run ruff format --check . && uv run ruff check . && uv run pytest      # free gates
uv run fathom validate humble-vs-super-v5                                 # free; must pass
uv run fathom smoke                                                       # spawn isolation
uv run fathom verify-arming --scenarios-dir scenarios/humble-vs-super-v5  # EXIT_UNARMED = stop
uv run fathom run humble-vs-super-v5 --scenarios-dir scenarios/humble-vs-super-v5 \
    --repeats 5 --dry-run                                                 # plan before spending

# STAGE A - the whole pre-registered commitment: 60 trials, forecast ~$38.
# It buys ONE number: the paired-by-task cost gap on claude-opus-5. Not a quality run.
uv run fathom run humble-vs-super-v5 --scenarios-dir scenarios/humble-vs-super-v5 \
    --repeats 5 --limit 60 --max-budget-usd 1.75

# MANDATORY between every chunk: actual cumulative spend, from the ledger.
uv run python scripts-humble-v5/analysis.py spend ledger/humble-vs-super-v5.jsonl
uv run python scripts-humble-v5/analysis.py cost ledger/humble-vs-super-v5.jsonl     # THE result
uv run python scripts-humble-v5/analysis.py criteria ledger/humble-vs-super-v5.jsonl # recorded, not a verdict
```

`--scenarios-dir` is load-bearing: the glob is non-recursive and omitting the flag would
silently run the repo's top-level arms against this bank.

Stage B (the fill to n=20) is **not** the plan — it is an escape hatch, bought only if the
cost test below fails to resolve. If it is bought, it is bought in `--limit 60` chunks with
a `spend` check between each. **Stage B buys no quality information either** — it fills n on
the same ceilinged criteria:

```sh
# STAGE B - ONLY if the cost test does not resolve, and ONLY with an explicit rail decision.
# 180 further trials, forecast ~$115. Re-invoke until "planned: 0 trials".
uv run fathom run humble-vs-super-v5 --scenarios-dir scenarios/humble-vs-super-v5 \
    --repeats 20 --limit 60 --max-budget-usd 1.75
uv run python scripts-humble-v5/analysis.py spend ledger/humble-vs-super-v5.jsonl   # STOP AT $150
```

### The rails, and what each one actually does

This is the part that was wrong in the first draft of these notes, so it is spelled out.

- **`--max-budget-usd` is a PER-SPAWN cap, not a budget.** It is passed straight through
  to the `claude` CLI (`src/fathom/adapters/claude_cli.py`), where it *terminates the
  session*. It caps one trial. **Nothing in fathom's run loop halts on cumulative
  spend** — `_CEILING_PER_TRIAL_USD = 2.00` (`src/fathom/cli.py`) is only the number
  `--dry-run` multiplies into the printed ceiling. A single `--repeats 20` invocation is
  therefore uninterruptible and unbounded short of 240 × $2 = $480.
- **The cumulative stop is procedural and it is mandatory.** Run every stage in
  `--limit 60` chunks and recompute actual spend from the ledger between chunks:
  `python scripts-humble-v5/analysis.py spend ledger/humble-vs-super-v5.jsonl` sums
  `cost_usd_est` over `kind=="run"` lines. **Written stop rule: if cumulative spend
  reaches $150, stop and do not re-invoke.** The resume key makes stopping free and
  restarting free.
- **The per-spawn cap is $1.75, not $1.00.** A cap set near the mean would truncate real
  trials, and a truncated trial is a *corrupted* measurement, not a saved dollar. The
  observed per-trial maximum across the 180 v1+v2 trials is $1.128, i.e. **$1.58 scaled
  by ×1.40**, with p95 at $1.05; the dearest cell (`stack-super` × `fix-tz-dst-normalize`)
  reached $1.37 scaled. A $1.00 cap would have truncated more than 5% of trials, and it
  would have truncated them *disproportionately in the dearest arm* — manufacturing
  exactly the cost advantage this bank exists to measure honestly. $1.75 sits above the
  observed maximum (so no legitimate trial is cut) and below fathom's own $2.00 guard (so
  a genuine runaway still trips earlier than the default).

### Plan and cost

`--repeats 20` plans **240 trials** (3 arms × 4 live tasks × 20), fathom ceiling
**$480.00** — that ceiling is the fixed $2.00/trial guard rail, not a forecast.

The forecast is built from **v1 and v2, which ran this exact task content under an
identical tool allow-list** (`scenarios/humble-vs-super/*.toml` matches v5's byte-for-byte
off the plugin axis), scaled by the Opus 4.8 → Opus 5 factor of ×1.40 measured in the
2026-08-11 model-tier recalibration. v3's rates are **not** used: none of v3's three tasks
is in this bank, and its mix is cheaper.

| arm | source | $/trial (opus-4-8) | × 1.40 | × 80 trials |
|---|---|---|---|---|
| `bare` | v1 | 0.2992 | 0.4189 | $33.51 |
| `stack-humble` | v2 | 0.4966 | 0.6952 | $55.61 |
| `stack-super` | v2 | 0.5771 | 0.8079 | $64.63 |
| **total (n=20)** | | | | **$153.76** |

**Point estimate ≈ $154, realistic band $130–200.** The upside risk is real and one-sided:
Opus 5 runs thinking-on by default at `effort = "high"`, and humblepowers 0.9.1 is roughly
twice the corpus of the 0.4.0 that produced v2's rates.

**This does not fit under a $150 rail.** The full n=20 matrix is above it before any
upside risk is counted. Stage A is the commitment that does fit:

| stage | trials | forecast |
|---|---|---|
| **A — `--repeats 5`** | 60 | **$38.44** |
| B — fill to `--repeats 20` | +180 | +$115.32 |

Per-task, the full n=20 matrix splits **$86.39 across the two feature tasks** and $67.37
across the two `fix-*` tasks — i.e. **56% of the spend buys the half of the bank that is
provably saturated on quality** (see above). The feature tasks are kept because they carry
two of the four task-pairs the cost test needs; if the rail is tight, dropping them is the
cheapest possible cut and costs **no quality information whatsoever**.

> **Rail decision required before Stage B.** Stage A ($38) is within any plausible rail
> and is pre-registered as the whole plan. Stage B takes the bank to ≈$154, above the
> $150 rail, and must not be started without an explicit owner decision.

### What Stage A is for (re-registered 2026-08-12, before any spend)

**Stage A is an ECONOMY measurement.** It is not a quality measurement, and it is not a
calibration run. This replaces the earlier registration, which put a discrimination check
(gate 1) at the front and read Stage A as a quality instrument. That registration was
built on a floor — unarmed `bare` at 0% on `regression_test_present` — that this repo's own
`model-tier-v1` ledger had **already broken on `claude-opus-5`** before v5 was authored. The
old text is not softened here; it was wrong on the published evidence, and a pre-registration
that predicts a floor the evidence contradicts is worse than none.

**The predicted state of the quality axis at Stage A, stated in advance:**

| criterion class | slots | predicted at Stage A |
|---|---|---|
| feature-task criteria (all 10) | 10 | 100% in all three arms — `bare` included, because prompted |
| `fix_correct`, `no_regression` | 4 | 100% in all three arms |
| `regression_test_present` × 2 `fix-*` tasks | 2 | **all three arms in a ~70–100% band** |

Every criterion in this bank is therefore predicted to land at or near ceiling **in every
arm**, `bare` included. That leaves the quality axis with **no floor, no discrimination
check, and no non-inferiority reading**: three arms crowded into a 70–100% band at n=5/cell
cannot be ordered, and "the armed arms are not worse" is unfalsifiable when the control is
not meaningfully below them. **No quality claim — including a non-inferiority claim — may be
read off Stage A.** The earlier note calling the quality axis "a non-inferiority check" is
withdrawn: that reading required a floor, and there isn't one.

What remains is the axis the bank is genuinely powered for. **Stage A buys one number:**
whether the ~2× growth of the humblepowers corpus between 0.4.0 and 0.9.1 has eaten the
per-trial cost advantage `stack-humble` held over `stack-super`, measured on `claude-opus-5`.
That question is untouched by the ceiling problem — cost is continuous, paired by task, and
the same four task-pairs carry it whether or not any criterion discriminates.

**The pre-registered test (the old gate 3, now the whole gate).** Evaluated per-task from the
ledger, not read off the scorecard:

> Compute the **paired-by-task** per-trial cost difference between `stack-humble` and
> `stack-super` across the four live tasks (four pairs, one per task) and run a paired
> t-test. **If it separates the arms at p < 0.05, publish the verdict and DO NOT buy the
> fill.** Only a non-significant result licenses Stage B, and then only with the rail
> decision above.

Prior: v2 resolved this gap at n=5/cell on `claude-opus-4-8` — pairs +13.1%, +21.2%, +14.3%,
+15.6%, same sign on all four, mean **+16.1%**, sd 3.6, **t = 8.95 on df = 3, p = 0.0029**;
median within-cell CV 14.5%, which is what makes a paired test resolve at n=5. Stage A
re-measures that gap's *sign and rough size* on the new model and the shipped corpus. Buying
n=20 would narrow a confidence interval that **no pre-registered decision depends on**.

**The two former gates, demoted to observations.** Both are still computed and recorded,
because an unmeasured criterion is not a null and the ledger is the record. Neither gates
spend any longer:

1. **Unarmed `regression_test_present` — expected to FAIL the old bright line, and that is
   not news.** The retired rule was `bare ≤ 10%` per `fix-*` task. On `claude-opus-5` the
   unarmed `model-tier-v1` arm scored 21/30 (70%) with a byte-identical verifier, per-task
   5/5, 4/5, 1/5, 4/5, 5/5, 2/5 — **every task above the line**. `bare` is therefore
   **expected to breach 10% on both `fix-*` tasks**, this is a prediction registered before
   the spend, and a breach **licenses nothing and blocks nothing**. Recording it costs
   nothing extra: `bare`'s trials are already bought as the economy control.
2. **Correctness ceilings.** Still expected at 100% in all three arms on all four tasks.
   Retained as a **fork/regression detector**: it would catch a broken fork or a model that
   got worse, and it is the one result that still stops the run.

**What a surprise would mean, and what it would license.** Registered in advance so a
surprise cannot be reinterpreted after the fact:

| observation at Stage A | reading | licenses |
|---|---|---|
| `bare` **breaches** 10% on the `fix-*` tasks (predicted) | the `model-tier-v1` opus-5 prior replicates on this bank's tasks | nothing — the expected case; proceed to the cost test |
| `bare` lands **≤ 10%** on both `fix-*` tasks (surprise) | the opus-5 prior does **not** transfer to these tasks; the floor still exists here and the task set, not the model, drives it | **no quality verdict.** At n=5/cell a floor is a *precondition*, not a result. It licenses only reopening the design — the quality axis would become worth powering, which is a **new bank sized for it**, not the Stage B fill (which buys n=20 on a question needing ~30pp of resolution) |
| a correctness criterion comes **off** the ceiling | substantive change on the new model, or a broken fork | **stop.** Do not buy the fill; reopen the design |
| the cost test does **not** separate at p < 0.05 | the 0.9.1 corpus may have eaten the advantage | Stage B, and only with the explicit rail decision above |

Note the asymmetry in row 2 on purpose: the *predicted* outcome licenses nothing, and the
*surprising* outcome licenses nothing either — only a differently-sized instrument. Stage A
cannot be turned into a quality measurement by a favourable result.

### The analysis is per-task, and the scorecard's Per-Criterion table is not it

`fathom report`'s **Per-Criterion Pass Rates** table pools each criterion **across tasks**
(`src/fathom/report.py`, `crit_counts` is keyed by criterion name, iterating `task_list`).
For this bank that is actively misleading: the `regression_test_present` row blends the
**ceilinged** `fix-tz-dst-normalize` with the **only informative** `fix-offbyone-paginator`
into one n=40/arm figure — halving the visible gap and inflating apparent n. On v2's data
that pooled row reads humble 100% (10/10) vs super 80% (8/10); **on v1 it reads humble 80%
(16/20) vs super 100% (10/10) — it flips sign.**

**Pre-registered analysis:** group `kind == "trial"` lines from
`ledger/humble-vs-super-v5.jsonl` by **scenario × task_id × criterion**, and read the cost
axis paired by task. `scripts-humble-v5/analysis.py` (`criteria` / `cost` / `spend`) is that
grouping, stdlib-only and runnable without credentials. Read the scorecard for orientation;
read the per-task tables for the verdict.

The resume key `(bank, dataset_version, task_id, config_hash, repeat)` makes every stage
strictly additive: nothing already completed is re-spent, so stopping at any chunk boundary
costs only wall-clock.
