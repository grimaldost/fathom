# Task bank: `humble-vs-super-v5`

The merged-state fork of the plugin-level humblepowers-vs-superpowers question
(`docs/specs/2026-06-14-fathom-humble-vs-super-design.md`). Each task is a realistic,
**stdlib-only** Python project carrying a *planted, subtle* defect. Three arms — `bare`,
`stack-humble`, `stack-super`, in `scenarios/humble-vs-super-v5/` — are compared on the
same tasks, blind to which arm produced each result (ADR-0003).

> **This bank is a FORK, not a reproduction.** The task content is a byte-identical copy
> of `humble-vs-super-v2`'s, but the instrument around it has moved on two axes at once:
> the treatment plugin is **humblepowers 0.9.1** (v1–v4 measured 0.3.1 / 0.4.0 — five
> minors back), and the base model is **`claude-opus-5`** (v1–v4 measured
> `claude-opus-4-8`, which the lineup no longer serves). Its numbers are a **new
> measurement**. They may not be pooled with, differenced against, or read as a
> replication of the v1–v4 ledgers. `dataset_version` is bumped to `2` as a **fork
> marker** — not as collision protection, since the bank name is already in the resume
> key and a v2 resume was never possible; with the task content byte-identical to v2's it
> is the only field left that records that the instrument moved. See `V5_NOTES.md` for the
> full design rationale, the pre-registered gates, and the spend rails.

## Task families

| family | tasks |
|--------|-------|
| bug-fix / regression | `fix-offbyone-paginator`, `fix-tz-dst-normalize`, **holdout** `fix-cache-eviction-bug` |
| small-feature edge-case-trap | `feature-csv-coalesce`, `feature-retry-backoff` |

Four tasks are live; `fix-cache-eviction-bug` is the sealed holdout (ADR-0005) that
`bank.toml`'s `holdout` list excludes from routine `fathom run` matrices. It is spent
only at a declared checkpoint, via `--include-holdout`. It is authored and unit-tested
like the others.

## The planted bugs (why they discriminate)

Each bug passes the *obvious* case so the shipped suite ships green and a naive guess
looks right, but fails a *hidden* case — so an undisciplined arm can land a wrong or
incomplete fix and fail `fix_correct`.

| task | bug | naive over-fix that still fails |
|------|-----|--------------------------------|
| paginator | `total_pages` floors instead of ceiling-dividing — drops the partial last page | `// + 1` (breaks exact multiples and the empty case) |
| tz/dst | DST decided by month only (`4 ≤ month ≤ 10`), ignoring the exact transition days | widening to `3 ≤ month ≤ 11` (breaks early-March / November) |
| cache | `get` does not refresh recency, so eviction degrades to FIFO | wrong `popitem`/insertion order (breaks the shipped overflow test) |

**Known and priced:** on **these exact tasks**, correctness has already ceilinged. Pooled
over v1 and v2 — which ran this same task content **on `claude-opus-4-8`** — `fix_correct`
and `no_regression` are **50/50 in every arm on both `fix-*` tasks**, and every criterion of
both feature tasks is **40/40**, the unarmed `bare` arm included. (Ceilings measured on the
older model carry forward as upper bounds; **floors do not** — see `regression_test_present`
below.) v3 replicated the pattern on a different task
set (0/180 at n=45,
`docs/reports/2026-06-16-humble-vs-super-powered-confirmatory.md`). v5 therefore does
**not** expect the correctness criteria to discriminate, and no verdict about correctness
should be read off them. What this bank measures — and the single criterion-slot that
still has headroom — is stated in `V5_NOTES.md` § "What v5 can and cannot answer".

## Layout

```
humble-vs-super-v5/
  bank.toml                 # name, dataset_version, holdout
  bugfix_verify.py          # SHARED harness-side verifier library (never staged)
  plugins/                  # vendored, immutable plugin trees (see plugins/VENDORED.md)
  <task-id>/
    task.toml               # id, instruction, [limits], [verify]
    fixtures/               # staged into the trial workspace (git-initialised)
      <package>/            # the buggy baseline code
      tests/                # shipped suite — PASSES on the buggy fixture, misses the bug
      README.md
    original/               # harness-side stash (never staged)
      <module>.py           # the buggy original, byte-identical to the fixture source
      tests/                # the shipped suite, byte-identical to the fixture tests
    verify.py               # blind acceptance grader (never staged)
```

`bugfix_verify.py`, `verify.py`, and `original/` are all siblings of `fixtures/`, so
`taskbank.stage_task` (which copies only `fixtures/`) never stages them and the candidate
never sees them. The `original/` stash is pinned byte-identical to the fixture by a
drift-guard test (`tests/test_verify_humble_super_bugfix.py`, which guards the v1 copy
these tasks were forked from; `tests/test_humble_super_v5_mounts.py` pins v5's copy to
v2's byte-for-byte).

## `verify.py` criteria (flat `{criterion: bool}` JSON, exit 0 iff all true)

- **`fix_correct`** — a hidden test (in `verify.py`, never shipped) imports the candidate
  package layout-agnostically and asserts the correct behavior on the bug-triggering
  input.
- **`no_regression`** — the canonical *shipped* suite (read from `original/tests/`, not
  from the workspace, so a candidate cannot weaken it) still passes against the candidate
  source.
- **`regression_test_present`** — the **swap**: the candidate's own suite is run on their
  source (must be green), then the stashed buggy original is swapped back in and the
  suite is run again (must go red). The shipped suite passes on the buggy source by
  construction, so a red can only come from a candidate-added, bug-covering test. This is
  the test-discipline signal; the instructions deliberately do **not** ask for a
  regression test, so the criterion varies across arms. **It is the only criterion that
  has ever discriminated on this bank family.**

  **On `claude-opus-4-8` — the model v1–v4 measured, and no longer the model this bank runs
  on — it separated `bare` (0%) from every disciplined arm (~100%).** Per task, pooled over
  v1+v2, even that was narrow: on `fix-tz-dst-normalize` the armed arms are 44/45 (97.8% —
  a ceiling with one stray failure), and `fix-offbyone-paginator` at 32/45 (71%) was the
  only criterion-slot in the bank with material headroom.

  > **That separation is not expected to hold on `claude-opus-5`, the model v5 runs on.**
  > This repo's `ledger/model-tier-v1.jsonl` scored an **unarmed** arm on `claude-opus-5`
  > at **21/30 (70%)** on this same criterion with a **byte-identical** `bugfix_verify.py`,
  > against **0/30** for the otherwise-identical `claude-opus-4-8` arm — per task 5/5, 4/5,
  > 1/5, 4/5, 5/5, 2/5. Those are different tasks (none of them in this bank), so the number
  > does not transfer, but the mechanism does: **on the current model an unarmed run writes
  > bug-covering regression tests unprompted at a substantial rate.** The `bare` (0%) floor
  > above is an artefact of the withdrawn model. See `V5_NOTES.md` § "What Stage A is for",
  > which re-registers this bank as an **economy** measurement for exactly this reason.

The two **feature** tasks score a different set — `behavior_correct`, `tests_present`, and
three per-task edge criteria. All ten are **40/40 in every arm** across v1+v2 (on
`claude-opus-4-8`), `bare` included, because those instructions enumerate the exact edges
the verifier checks: their
`tests_present` is *prompted*, not elicited. **The feature tasks cannot produce quality
signal on this bank**; they are retained as economy samples only (`V5_NOTES.md`).

### Blindness

`verify.py` reads the candidate's work only from `argv[1]` (the result-view). It also
reads its `original/` stash — but that stash is identical for every arm, so it carries no
scenario identity and cannot bias the A/B comparison (ADR-0003). No scenario identifier
ever appears in the verifier's argv or env.

### Known limitations

- The swap reintroduces the bug by overwriting a single module file
  (`<package>/<module>.py`), discovered flat or under `src/`. A heavy refactor that moves
  the bug logic into a *different* file would make `regression_test_present` a false
  negative; the focused "fix this bug" framing makes that rare, and `fix_correct` /
  `no_regression` are unaffected.
- **Plugin hooks do not fire in headless `claude -p`** (`src/fathom/scenario.py`,
  `SettingsConfig`). Both mounted plugin families ship hooks — superpowers' `SessionStart`
  hook injects its `using-superpowers` skill body, humblepowers 0.9.1's `UserPromptSubmit`
  router hook is inert-by-default anyway — and **neither runs**. Each plugin is therefore
  measured on its skill *descriptions* and the model's own dispatch, not on its
  hook-assisted onboarding. This has been true of every humble-vs-super run since v1, so
  it is a constant of the series rather than a v5 change; it still bounds what the numbers
  mean, most sharply for superpowers, whose hook is the arm that would otherwise announce
  the skill library. **Its bias has a direction and it is not symmetric: the dead hook
  works *against* superpowers on quality (its dispatch skill is never injected) but *for*
  it on cost (less injected corpus to pay for).** Superpowers nonetheless measured dearer
  in v1, v2 and v3 — so the harness constant does not manufacture the observed cost gap,
  it understates it. Carry this sentence into any published verdict.
- **The bank has no power over the third-party snapshot's presence.** `superpowers@6fd4507`
  is gitignored and untracked; see `plugins/VENDORED.md` for the decision, the integrity
  manifest, and the four controls that stand in for tracking it.
