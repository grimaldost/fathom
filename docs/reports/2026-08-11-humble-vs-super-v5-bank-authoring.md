# humble-vs-super-v5 — the merged-state bank, authored, repaired, and deliberately not run

**Date:** 2026-08-11 · **Bank:** `humble-vs-super-v5` · **Spend:** $0 · **Ledger:** none ·
**Branch:** `eval/humble-vs-super-merged`

The bank exists, validates, arms on real spawns, and has a pre-registered analysis with
decision rules. It was **not run**, and this note is the record of that decision — written
because a decision taken on power grounds is exactly the kind that vanishes into a commit
message and gets re-litigated later as "we never got round to it".

Design rationale, the pre-registered gates and the spend rails live with the instrument in
[`tasks/humble-vs-super-v5/V5_NOTES.md`](../../tasks/humble-vs-super-v5/V5_NOTES.md) and
[`tasks/humble-vs-super-v5/README.md`](../../tasks/humble-vs-super-v5/README.md). Design of
record: [`docs/specs/2026-06-14-fathom-humble-vs-super-design.md`](../specs/2026-06-14-fathom-humble-vs-super-design.md).

## What the bank is

A fork of the v2 instrument to measure the **shipped** humblepowers body. The task content
is a byte-for-byte copy of v2's — same four live tasks, same fixtures, same `original/`
stashes, same per-task `verify.py` — pinned by `tests/test_humble_super_v5_mounts.py`.
What moves is the instrument around it.

| | v2 (2026-06-15) | v5 |
|---|---|---|
| humblepowers | 0.4.0 | **0.9.1** (craft-collection `main`, `b7b0097`) |
| superpowers | 5.1.0 @ `6fd4507` | unchanged |
| held-constant stack | engineering-discipline 0.1.2 + session-workflow 0.2.2 | unchanged, deliberately |
| base model | `claude-opus-4-8` | **`claude-opus-5`** |
| arms | stack-humble / super-only / stack-super | **bare / stack-humble / stack-super** |
| `dataset_version` | 1 | **2** (a fork marker; the bank name already prevents a resume collision) |

**Two axes moved and only one was a choice.** `claude-opus-4-8` is no longer served, so
pinning v2's model would produce a matrix that cannot run. The consequence is structural:
**v5's numbers may not be differenced against v1–v4's**, because a change in the treatment
and a change in the base model are confounded in that comparison and no arrangement of
these arms separates them. v5 supports the *within-v5* contrast only.

The held-constant stack was deliberately left at its 2026-06 pins even though `main` now
carries engineering-discipline 0.4.0 and session-workflow 0.21.0. Refreshing it would move
a third axis at the same time, and session-workflow 0.21.0 is several times the corpus of
0.2.2 — it would shift both disciplined arms' token and cost baselines by an amount
unrelated to the question. The honest cost of that choice: **v5 measures humblepowers 0.9.1
inside a 2026-06-era stack, not inside the merged toolkit.** That is a different, larger
bank.

## Offline evidence, all of it free

- `uv run ruff format --check . && uv run ruff check .` — clean (745 files).
- `uv run pytest` — 637 passed, 1 skipped, 112 subtests.
- `uv run fathom validate humble-vs-super-v5` — **5 pass / 0 fail / 0 warn / 10
  unverifiable**. The unverifiable profile is inherited from v2 and is a real limit, not a
  formality: these tasks ship no `solution/` overlay, so the verifiers are **not known to be
  satisfiable offline**, and a null on any of them cannot be distinguished from an
  unsatisfiable verifier. (Contrast `model-tier-v2`, authored the same day, which ships
  `solution/` + `counter/` + `counter-strong/` overlays and validates 30/0/0/0.) The
  practical mitigation here is historical rather than structural: these exact tasks have
  180 committed trials across v1 and v2 in which every criterion has been observed true,
  so satisfiability is established by the record instead of by an overlay.
- `uv run fathom verify-arming --scenarios-dir scenarios/humble-vs-super-v5` — **ALL
  VERIFIED** on real spawns (2026-08-11): `bare` control, `stack-humble` and `stack-super`
  each `[PASS/verified] declared=3` with the three plugin names read out of the init event.
  `tests/test_humble_super_v5_mounts.py` is the offline half of the same guard — it fails
  if a scenario points at a tree that is not there, if the two disciplined arms stop sharing
  an identical held-constant stack, if any field other than `[plugins]` drifts between arms,
  or if the re-vendored superpowers bytes differ from the measured snapshot.
- `uv run fathom smoke` — 7/8 during this pass; the single failure is `engine-boundary`,
  which concerns the convoy series arm and is untouched by this bank's single-session arms.

## Why it was not run: the power analysis, computed from the committed ledgers

This is the decisive section and every number in it is reproducible offline, without
credentials, with
`uv run python scripts-humble-v5/analysis.py criteria ledger/humble-vs-super-v1.jsonl ledger/humble-vs-super-v2.jsonl`.
`tests/test_humble_v5_analysis.py` recomputes each published figure from those ledgers, so
the forecast, the ceilings and the per-spawn cap cannot drift from the prose that would
spend money on them.

v1 and v2 ran **this exact task content under an identical tool allow-list**, so they are
the relevant prior. (v3's rates are not used: none of v3's three tasks is in this bank.)
Pooling them over v5's four live tasks gives 16 criterion-slots. **Fifteen are at 100% in
every arm.**

> **Correction, 2026-08-12.** Every figure in this section was measured on
> **`claude-opus-4-8`**; v5 runs on `claude-opus-5`. The **ceilings** carry forward as upper
> bounds. The **floor does not**: `ledger/model-tier-v1.jsonl` scored an unarmed
> `claude-opus-5` arm at **21/30 (70%)** on `regression_test_present` with a byte-identical
> `bugfix_verify.py`, against **0/30** for the otherwise-identical `claude-opus-4-8` arm.
> The "`bare` at 0/5 and 0/5" fact below is therefore an artefact of the withdrawn model, and
> Stage A has been **re-registered as an economy measurement** — see `V5_NOTES.md` § "What
> Stage A is for". This strengthens rather than weakens the decision recorded here: with the
> floor gone, a run buys even less on quality than this note originally claimed.

| task | criterion | pooled v1+v2 (`claude-opus-4-8`) | headroom |
|---|---|---|---|
| `feature-csv-coalesce` | all five, incl. `tests_present` | **40/40 each** | none |
| `feature-retry-backoff` | all five, incl. `tests_present` | **40/40 each** | none |
| `fix-tz-dst-normalize` | `fix_correct`, `no_regression` | 50/50 each | none |
| `fix-tz-dst-normalize` | `regression_test_present` | armed arms **44/45 (97.8%)** | ceilinged |
| `fix-offbyone-paginator` | `fix_correct`, `no_regression` | 50/50 each | none |
| `fix-offbyone-paginator` | `regression_test_present` | armed arms **32/45 (71%)** | **the only slot** |

Three consequences, in order of how much they cost:

1. **Both feature tasks are fully saturated, `bare` included — and they are the dearest
   tasks in the bank.** This is structural, not luck: their instructions enumerate the exact
   edges the verifier checks, so `tests_present` is *prompted rather than elicited*, which is
   why `bare` scored 100% on it while scoring **0/5 and 0/5** on `regression_test_present` in
   the two `fix-*` tasks, whose instructions mention no tests at all (**both on
   `claude-opus-4-8`** — see the correction above; the 0/5 half is not expected to reproduce
   on `claude-opus-5`). Over a full n=20 matrix
   those two tasks are **$86.39 of $153.76 — 56% of the spend buying the provably saturated
   half.** They are retained only as economy samples (they carry two of the four task-pairs
   the cost test needs); no quality claim may be read off them.
2. **The quality axis reduces to one criterion of one task**, `regression_test_present` on
   `fix-offbyone-paginator`, at n=20/arm. Pooled v1+v2 reads humble-family 17/25 (68%)
   against super-family 15/20 (75%), Fisher's exact **p = 0.75**, and **the sign already
   flipped between runs** (v1: humble 6/10 vs super 5/5; v2: humble 5/5 vs super 3/5). At
   n=20/arm against a 70% reference, Fisher at α=0.05 first reaches significance at 100% —
   it resolves a gap of roughly **30 percentage points**. The effect in evidence is
   single-digit and unstable in sign. **v5 has no power to resolve the humble-vs-super
   quality question, and buying n=20 does not change that.**
3. **The economy axis is the one with signal, and it is already resolved.** The
   pre-registered cost test (the former gate 3, and since 2026-08-12 the **whole** gate)
   says: run `--repeats 5`, compute the paired-by-task cost difference
   across the four tasks, and if it separates at p < 0.05, publish and do **not** buy the
   fill. On v2's data that gate is already met at n=5/cell — `stack-humble` → `stack-super`
   +16.1% mean, sd 3.6, **t = 8.95 on df = 3, p = 0.0029** — and pooling v1+v2 gives
   +27.0%, sd 5.5, t = 9.72, **p = 0.0023**, same sign on all four tasks. Median within-cell
   CV is 14.5%, which is what makes a paired test resolve at small n.

So the matrix would buy: nothing on quality (no power, by the bank's own arithmetic), and a
re-measurement on `claude-opus-5` of an economy gap already separated on `claude-opus-4-8`
— a gap whose *magnitude* no pre-registered decision depends on.

**The decision:** do not spend. Recorded as $0 with the instrument left runnable, not
deleted. The one thing a run would genuinely add — whether the ~2× growth of the
humblepowers corpus between 0.4.0 and 0.9.1 has eaten the cost advantage on the new model —
is a real question, and Stage A ($38 forecast, $120 ceiling) is the priced, pre-registered
way to buy it whenever it is worth $38. Nothing about the instrument blocks that.

## The plan and the rails, if it is ever bought

```
uv run fathom run humble-vs-super-v5 --scenarios-dir scenarios/humble-vs-super-v5 \
    --repeats 5 --limit 60 --max-budget-usd 1.75
# fathom run: bank=humble-vs-super-v5  scenarios=3  tasks=4  repeats=5
# planned:  60 trials (0 already done)  ceiling: $120.00
```

| stage | trials | dry-run ceiling | forecast |
|---|--:|--:|--:|
| **A — `--repeats 5`** (the whole pre-registered commitment) | 60 | $120.00 | **$38.44** |
| B — fill to `--repeats 20` (escape hatch only) | +180 | $480.00 total | +$115.32 |

The forecast is built from v1/v2 per-trial rates scaled by the Opus 4.8 → Opus 5 factor of
×1.40 measured in the 2026-08-11 recalibration: `bare` $0.2992 → $33.51/80 trials,
`stack-humble` $0.4966 → $55.61, `stack-super` $0.5771 → $64.63; **$153.76 total, band
$130–200**, with one-sided upside risk (Opus 5 runs thinking-on at `effort = "high"`, and
the treatment corpus roughly doubled). **The full matrix does not fit a $150 rail before any
upside risk is counted.**

Three rail facts, spelled out because the first draft of the plan had them wrong:

- **`--max-budget-usd` is a PER-SPAWN cap, not a budget.** It is passed straight through to
  the CLI, where it terminates one session. **Nothing in fathom's run loop halts on
  cumulative spend** — the dry-run ceiling is a flat $2.00/trial constant on this branch. A
  single `--repeats 20` invocation is uninterruptible and unbounded short of $480.
- **The cumulative stop is procedural and mandatory:** run in `--limit 60` chunks and
  recompute actual spend from the ledger between them —
  `uv run python scripts-humble-v5/analysis.py spend ledger/humble-vs-super-v5.jsonl` sums
  `cost_usd_est` and exits non-zero at $150. The resume key makes stopping and restarting
  free.
- **The per-spawn cap is $1.75, not $1.00.** Observed per-trial maximum over the 180 v1+v2
  trials is $1.128 = **$1.58 scaled**, p95 $1.05. A $1.00 cap would truncate >5% of trials,
  disproportionately in the dearest arm, **manufacturing the very cost gap this bank
  measures**. A truncated trial is a corrupted measurement, not a saved dollar.

## What this bank cannot license, run or unrun

Stated plainly because the owner's rule binds hardest exactly here.

- **Nothing in this work supports retiring either plugin.** A ceilinged criterion is an
  absence of measurement, not evidence of equivalence. Fifteen of sixteen criterion-slots
  are ceilinged.
- **The unit is the task, not the trial.** Task-level n is **4**, and after the ceiling
  analysis it is effectively **1** for quality — one criterion on one small stdlib Python
  bug-fix. Any "library X is better" claim from this bank generalises over a population of
  one, whatever the trial count says. The economy axis is better off (four tasks, same sign
  on all four) but still speaks only to short single-session fixes.
- **A cost difference on four small stdlib Python tasks does not generalise** to the work
  either library was written for — multi-hour sessions, design work, review loops,
  orchestration — none of which this bank contains. The single axis on which these
  disciplines have ever been shown to move anything is test hygiene on small self-contained
  fixes.
- **A harness constant belongs in any verdict.** Plugin hooks do not fire in headless
  `claude -p`, so superpowers' `SessionStart` hook — which injects its dispatch skill —
  never runs. That biases *against* superpowers on quality and *for* it on cost. Superpowers
  still measured dearer in v1, v2 and v3, so the constant understates the cost gap rather
  than manufacturing it.
- **`fathom report`'s Per-Criterion table is not the analysis.** It pools each criterion
  across tasks, blending the ceilinged `fix-tz-dst-normalize` with the only informative
  `fix-offbyone-paginator` into one n=40/arm figure — halving the visible gap and inflating
  apparent n. On v2's data that pooled row reads humble 100% vs super 80%; **on v1 it reads
  humble 80% vs super 100% — it flips sign.** The pre-registered analysis is per scenario ×
  task × criterion, computed from the ledger by `scripts-humble-v5/analysis.py`.

## Open

- Stage A itself, whenever the "did 0.9.1 eat the cost advantage on Opus 5" question is
  worth $38.
- The 10 unverifiable validate checks: adding `solution/` overlays to the v5 tasks would
  close them and cost nothing but authoring time. The task content is currently
  byte-identical to v2's, so any overlay must be added under a new `dataset_version` or as
  files the resume key does not see.
- A merged-stack variant (engineering-discipline 0.4.0 + session-workflow 0.21.0) is a
  different bank, not a knob on this one.
