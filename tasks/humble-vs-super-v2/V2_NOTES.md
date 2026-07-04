# humble-vs-super-v2 — re-run with humblepowers 0.4.0 (3-arm)

**Created:** 2026-06-15. **Lineage:** byte-for-byte copy of the `humble-vs-super-v1`
task bank (same tasks, fixtures, `original/` stashes, per-task `verify.py`, and the
shared `bugfix_verify.py`), changing only the plugin set and the arm design. v1 is
preserved untouched as the **humblepowers 0.3.1 baseline**; report each bank
separately (`uv run fathom report humble-vs-super-v1` vs `… humble-vs-super-v2`).

## What changed from v1

| | v1 (baseline) | v2 (this bank) |
|---|---|---|
| humblepowers | 0.3.1 | **0.4.0** |
| Arms | bare · humble-only · super-only · stack-humble · stack-super (5) | **stack-humble · super-only · stack-super (3)** |
| Tasks / verifier / fixtures | — | identical (frozen copy) |

Dropped `bare` — its floor (0% regression-test discipline) is already established by
the v1 run — and `humble-only` — humblepowers is designed to operate *within* its
stack, so the isolated arm under-represents it (confirmed in the v1 analysis). The
matched, apples-to-apples contrast is **stack-humble vs stack-super** (both inside
the held-constant common stack = engineering-discipline + session-workflow);
`super-only` is the un-stacked superpowers reference.

## Hypothesis

v1 result: superpowers wrote a regression test 90–100% of the time vs humblepowers
50–60%, at ~30–40% higher cost — humblepowers' calibration doctrine ("don't load a
discipline unless its benefit beats the context cost") declining TDD on small,
well-specified fixes. The v1 craft-collection feedback argued that **if humblepowers
closed that regression-test gap it would Pareto-dominate** (equal discipline at lower
cost, since the cost gap is mostly corpus size, not the test-writing itself).
humblepowers 0.4.0 — which adds a `planned-execution` skill and foregrounds red-green
TDD + evidence-before-claims verification in its dispatch — is the candidate fix.
**v2 tests whether 0.4.0 raises `stack-humble`'s `regression_test_present` rate toward
`stack-super`'s while keeping its cost advantage.**

## Plugins (vendored, immutable)

Self-contained under `plugins/` (its own copy, so this analysis does not depend on
v1's tree surviving). humblepowers **0.4.0** (treatment) · superpowers v5.1.0 @
`6fd4507` (contrast) · engineering-discipline 0.1.2 + session-workflow 0.2.2
(held-constant stack). superpowers + the stack are byte-identical to v1's, so their
content hash (`config_hash`) matches v1 — the only intended treatment change is the
humblepowers version.

## Run

```sh
uv run fathom smoke
uv run fathom run humble-vs-super-v2 --scenarios-dir scenarios/humble-vs-super-v2 --repeats 5 --dry-run
uv run fathom run humble-vs-super-v2 --scenarios-dir scenarios/humble-vs-super-v2 --repeats 5
uv run fathom report humble-vs-super-v2
```

Same ceiling caveat as v1: in v1 only `regression_test_present` discriminated (10 of
11 criteria ceilinged at 100% across arms). The other criteria again confirm no
correctness regression but carry little signal. This bank is the right instrument for
the specific "did 0.4.0 close the gap?" question — not a broad quality re-measurement
(that needs a harder bank).
