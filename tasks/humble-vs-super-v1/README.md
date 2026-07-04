# Task bank: `humble-vs-super-v1`

The bank for the plugin-level humblepowers-vs-superpowers question
(`docs/specs/2026-06-14-fathom-humble-vs-super-design.md`). Each task is a realistic,
**stdlib-only** Python project carrying a *planted, subtle* defect. The five arms
(`bare`, `humble-only`, `super-only`, `stack-humble`, `stack-super`, in
`scenarios/humble-vs-super/`) are compared on the same tasks, blind to which arm
produced each result (ADR-0003).

## Task families

| family | section | tasks |
|--------|---------|-------|
| bug-fix / regression | §6 (this PR) | `fix-offbyone-paginator`, `fix-tz-dst-normalize`, **holdout** `fix-cache-eviction-bug` |
| small-feature edge-case-trap | §7 | `feature-csv-coalesce`, `feature-retry-backoff` (to be added) |

`fix-cache-eviction-bug` is the sealed holdout (ADR-0005): `bank.toml`'s `holdout`
list excludes it from routine `fathom run` matrices; it is spent only at a declared
checkpoint. It is authored and unit-tested like the others.

## The planted bugs (why they discriminate)

Each bug passes the *obvious* case so the shipped suite ships green and a naive guess
looks right, but fails a *hidden* case — so an undisciplined arm can land a wrong or
incomplete fix and fail `fix_correct`.

| task | bug | naive over-fix that still fails |
|------|-----|--------------------------------|
| paginator | `total_pages` floors instead of ceiling-dividing — drops the partial last page | `// + 1` (breaks exact multiples and the empty case) |
| tz/dst | DST decided by month only (`4 ≤ month ≤ 10`), ignoring the exact transition days | widening to `3 ≤ month ≤ 11` (breaks early-March / November) |
| cache | `get` does not refresh recency, so eviction degrades to FIFO | wrong `popitem`/insertion order (breaks the shipped overflow test) |

## Layout

```
humble-vs-super-v1/
  bank.toml                 # name, dataset_version, holdout
  bugfix_verify.py          # SHARED harness-side verifier library (never staged)
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
`taskbank.stage_task` (which copies only `fixtures/`) never stages them and the
candidate never sees them. The `original/` stash is pinned byte-identical to the
fixture by a drift-guard test (`tests/test_verify_humble_super_bugfix.py`).

## `verify.py` criteria (flat `{criterion: bool}` JSON, exit 0 iff all true)

- **`fix_correct`** — a hidden test (in `verify.py`, never shipped) imports the
  candidate package layout-agnostically and asserts the correct behavior on the
  bug-triggering input.
- **`no_regression`** — the canonical *shipped* suite (read from `original/tests/`,
  not from the workspace, so a candidate cannot weaken it) still passes against the
  candidate source.
- **`regression_test_present`** — the **swap**: the candidate's own suite is run on
  their source (must be green), then the stashed buggy original is swapped back in and
  the suite is run again (must go red). The shipped suite passes on the buggy source by
  construction, so a red can only come from a candidate-added, bug-covering test. This
  is the test-discipline signal; the instructions deliberately do **not** ask for a
  regression test, so the criterion varies across arms.

### Blindness

`verify.py` reads the candidate's work only from `argv[1]` (the result-view). It also
reads its `original/` stash — but that stash is identical for every arm, so it carries
no scenario identity and cannot bias the A/B comparison (ADR-0003). No scenario
identifier ever appears in the verifier's argv or env.

### Known limitation

The swap reintroduces the bug by overwriting a single module file
(`<package>/<module>.py`), discovered flat or under `src/`. A heavy refactor that moves
the bug logic into a *different* file would make `regression_test_present` a false
negative; the focused "fix this bug" framing makes that rare, and `fix_correct` /
`no_regression` are unaffected.
