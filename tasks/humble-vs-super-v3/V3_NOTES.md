# humble-vs-super-v3 — the harder bank + higher-n confirmatory pass

**Created:** 2026-06-16. **Motivation:** v2 confirmed humblepowers 0.4.0 closed the
test-discipline gap, but its quality edge rested on a *single* discriminating criterion
(`regression_test_present`) at n=10/arm — directional, not conclusive (overlapping
Wilson CIs). v3 follows the two STATUS next-steps, fused: a **harder bank** where
correctness itself discriminates (so >1 criterion carries signal), run at **higher n**.

## What's different from v2

| | v2 | v3 |
|---|---|---|
| Tasks | spoon-fed bug reports (exact failing example given) | symptom-only reports; full contract in the docstring, not enumerated |
| What discriminates | only `regression_test_present` (10/11 criteria ceilinged) | several correctness criteria, by design |
| Arms | stack-humble · super-only · stack-super | **+ `bare`** (calibration floor / discrimination anchor) |
| Plugins | vendored under v2's tree | **mounted from v2's tree** (same content → identical `config_hash` for the shared arms; v3 self-contains only if it graduates to a committed instrument) |
| Holdout | `fix-cache-eviction-bug` | none (all 3 tasks live) |

A **separate bank** (not v2's ledger): `fathom report` aggregates by arm *name* with no
`dataset_version` filter, so mixing instruments into one ledger would blend columns. v2
stays the 0.4.0 baseline; v3 is its own clean ledger.

## The three trap tasks (why each discriminates)

- **`fix-dedup-records`** — root cause vs symptom. Symptom is a *case* duplicate; the
  documented contract also requires surrounding-whitespace normalization and keep-first
  semantics. `.lower()`-only fix passes `dedup_case`, fails `dedup_whitespace` /
  `keeps_first_row`.
- **`fix-interval-merge`** — two interacting edge cases. `merge_adjacent` (touching =
  `last_end + 1`) and `merge_contained` (merged end = `max`, not latest). A rushed fix
  handles one clause of the symptom and forgets the other; only enumerate-all passes both.
- **`fix-money-split`** — "looks done". The sum bug is visible, so every fix passes
  `sums_exact`; the documented fairness rule (leftover one-each to earliest, larger
  first) is missed by a dump-the-remainder fix → fails `fair_distribution`.

## Hypothesis

If v3 calibrates (bare lands inside (0,1) on the correctness criteria), it will show
**whether the humble/super discipline gap moves correctness, not just test-presence** —
a stronger, multi-criterion version of the v2 question — at an n that can make the
verdict conclusive rather than directional.

## Plan (pilot-gated — protects the spend)

There is no `--scenarios` arm filter, so the pilot uses a **subset scenarios dir**
(`scenarios/humble-vs-super-v3-pilot/` = `bare.toml` + `stack-super.toml`, byte-identical
to the full set). Identical `config_hash` means the pilot trials **resume into** the full
matrix — nothing is re-spent.

```sh
uv run ruff format --check . && uv run ruff check . && uv run pytest   # gates
uv run fathom smoke                                                      # spawn-isolation go/no-go
# 1. CALIBRATION PILOT (cheap): bare (floor) vs stack-super (ceiling) — does it discriminate?
uv run fathom run humble-vs-super-v3 --scenarios-dir scenarios/humble-vs-super-v3-pilot \
    --repeats 3                                     # 2 arms x 3 tasks x 3 = 18 trials, ~$15
uv run fathom report humble-vs-super-v3
# 2. POWERED MATRIX (only if the pilot calibrates): all 4 arms; R set by the pilot effect size.
#    bare + stack-super trials from the pilot resume in automatically.
uv run fathom run humble-vs-super-v3 --scenarios-dir scenarios/humble-vs-super-v3 --repeats <R>
```

Reduce/retune difficulty if a correctness criterion floors (all arms fail) or ceilings
(all pass) in the pilot. Only commit the powered matrix once `bare` is demonstrably
inside (0, 1).
