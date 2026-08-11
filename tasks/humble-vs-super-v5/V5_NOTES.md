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
| live tasks × repeats | 4 × 5 | **4 × 20** |
| `dataset_version` | 1 | **2** |

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

**`bare` is back.** v2 dropped it because v1 had established the floor. v5 restores it
because the base model changed: the instrument's ability to discriminate at all was
established on `claude-opus-4-8` and has never been shown on `claude-opus-5`. `bare` is
a calibration arm here, not a comparison — see the gate below.

## What v5 can and cannot answer

The prior evidence is unusually specific about where this bank family has signal, and
pretending otherwise would waste the spend.

- **Correctness ceilings.** v3 recorded **0/180 correctness failures at n=45/arm,
  `bare` included**, replicated by v4. `fix_correct` and `no_regression` are kept as
  regression detectors — they would catch a broken fork or a model that got worse — not
  as discriminators. **No verdict may be read off them.**
- **`regression_test_present` separates armed from unarmed, not humble from super.**
  v3 at n=45: bare 0%, stack-humble 100%, super-only 97.8%, stack-super 95.6% — the
  three disciplined arms statistically tied on overlapping Wilson CIs.
- **v5 has no power to resolve the humble-vs-super quality question.** At n=80/arm
  (4 tasks × 20 repeats), against a 100% reference, Fisher's exact test at α=0.05
  resolves a gap of roughly **8–10 percentage points**. The gap v3 actually measured is
  ~2–4pp. n=80 is therefore *below* the effect size in evidence, and n large enough to
  settle it is out of proportion to the decision. Treat the quality axis as a
  **non-inferiority check**: if 0.9.1 has *not* regressed, both disciplined arms sit
  near the ceiling and the axis is uninformative by design.
- **The economy axis is the one that buys something.** Per-trial USD, total tokens,
  turns and wall-clock are continuous, and v3 separated stack-humble from both
  superpowers arms by ~9–19% at n=45. Whether the ~2× growth of the humblepowers corpus
  between 0.4.0 and 0.9.1 (two new skills, several new reference files, a scripts tree)
  has eaten that cost advantage is the question v5 is actually powered for. The
  per-trial dispersion is not published, so the exact minimum detectable difference is
  not computable in advance — estimate it from the first chunk (below) rather than
  asserting it now.

### What must not be concluded from this bank

Whatever v5 returns, it **cannot** support retiring either plugin. A ceilinged criterion
is an absence of measurement, not evidence of equivalence; a cost difference on four
small stdlib Python tasks does not generalise to the work either library was written
for (multi-hour sessions, design work, review loops, orchestration), none of which this
bank contains. The single axis on which these disciplines have ever been shown to move
anything is test hygiene on small self-contained fixes.

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
    --repeats 20 --dry-run                                                # plan before spending

# CALIBRATION CHUNK FIRST (see the gate below) - resumes into the full matrix for free.
uv run fathom run humble-vs-super-v5 --scenarios-dir scenarios/humble-vs-super-v5 \
    --repeats 5 --max-budget-usd 2.0
uv run fathom report humble-vs-super-v5

# FILL to n=20 only if the calibration gate passes. Already-completed trials are skipped.
uv run fathom run humble-vs-super-v5 --scenarios-dir scenarios/humble-vs-super-v5 \
    --repeats 20 --max-budget-usd 2.0
```

`--scenarios-dir` is load-bearing: the glob is non-recursive and omitting the flag would
silently run the repo's top-level arms against this bank.

### Plan and cost

`--repeats 20` plans **240 trials** (3 arms × 4 live tasks × 20), fathom ceiling
**$480.00** — that ceiling is the fixed $2.00/trial guard rail, not a forecast. The
evidence-based forecast, from v3's observed per-trial USD scaled by the Opus 4.8 → Opus 5
factor of ×1.40 measured in the 2026-08-11 model-tier recalibration:

| arm | v3 $/trial (opus-4-8) | × 1.40 | × 80 trials |
|---|---|---|---|
| bare | 0.217 | 0.304 | ≈ $24 |
| stack-humble | 0.390 | 0.546 | ≈ $44 |
| stack-super | 0.482 | 0.675 | ≈ $54 |
| **total** | | | **≈ $122** |

Read that as a floor, not a point estimate: v3's per-trial figures come from three
bug-fix tasks, while v5's four live tasks include two *feature* tasks with 2400 s /
100-turn ceilings that are likely dearer. A realistic band is **$120–170**. `--repeats 5`
is ≈ **$30** of that and is the recommended first commitment.

### The calibration gate (spend-protecting, pre-registered)

Run `--repeats 5` (60 trials) and stop to read the scorecard before filling to n=20.

1. **Does the instrument still discriminate on `claude-opus-5`?** `bare` must land near
   0% on `regression_test_present`. If `bare` writes regression tests unprompted on the
   new model, the bank no longer measures test discipline and **the fill must not be
   bought** — the finding is that the model moved, which is worth reporting on its own.
2. **Do the correctness criteria ceiling as predicted?** If they do (expected), say so
   and do not mine them. If a correctness criterion has come off the ceiling, that is a
   substantive change on the new model and the design conversation reopens before more
   spend.
3. **What is the per-trial cost dispersion?** Compute it from the 60 trials and turn the
   economy question's minimum detectable difference into a number. If n=20 cannot
   resolve the cost gap that is actually present, buying it is waste.

The resume key `(bank, dataset_version, task_id, config_hash, repeat)` makes the fill
strictly additive: nothing already completed is re-spent, so the gate costs only
wall-clock.
