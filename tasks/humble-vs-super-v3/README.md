# Task bank: `humble-vs-super-v3` — the harder, correctness-discriminating bank

The v1/v2 banks hit a **ceiling**: their bug reports spoon-fed the fix (they named the
exact failing example), so every capable arm nailed `fix_correct` and the *only*
criterion that moved was `regression_test_present` (test-discipline). v3 is built so
**correctness itself discriminates** — the naive fix is subtly wrong, so several
per-criterion rows carry signal, not just one.

The contrast and method are otherwise identical to v2 (same arms minus the spoon-fed
tasks; see `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` and the v2 report).
Each task is a realistic, **stdlib-only** Python package with a planted defect, scored
**blind** to which arm produced it (ADR-0003).

## How v3 is harder (the design rule)

Each task obeys one rule: **the hidden requirement is documented but easy to
under-deliver under haste.** The instruction states only the *symptom* and says
"behaves as documented" — it does NOT enumerate the edge cases. The full contract lives
in the package docstring / README. So discipline *causes* correctness:

- a rushing arm fixes the visible symptom and ships → fails a hidden, documented criterion;
- a disciplined arm (reads the whole contract, traces the root cause, enumerates edge
  cases, verifies before claiming done) honors all of it → passes.

This is the legitimate signal: not clairvoyance (the behavior is documented), but
whether the arm's process surfaces the rest of the contract.

| task | trap type (discipline rewarded) | symptom names | documented-but-unhinted criteria |
|------|--------------------------------|---------------|----------------------------------|
| `fix-dedup-records` | root cause / read-the-contract (systematic-debugging) | only the *case* duplicate | `dedup_whitespace`, `keeps_first_row` |
| `fix-interval-merge` | interacting edge cases (TDD enumeration) | "stays separate" + "comes back shorter" | `merge_adjacent` **and** `merge_contained` (a fix usually gets one) |
| `fix-money-split` | "looks done" / spec fidelity (verification-before-completion) | parts don't sum to total | `fair_distribution` (sum looks fixed; fairness rule missed) |

Every task also carries `no_regression` (shipped suite stays green — an anchor at 100%)
and `regression_test_present` (the swap — the same test-discipline signal v1/v2 measured).

## Calibration

"Bare sometimes fails" is **empirical**, not assumed (data-engineering-discipline axiom
3: real spawns find what authoring can't). The bank is validated by a cheap pilot
(`bare` + a disciplined arm, a few repeats) **before** the powered matrix: the target is
a bare all-criteria pass-rate well inside (0, 1). If a criterion floors (all arms fail)
or ceilings (all pass), it is retuned or dropped. See `V3_NOTES.md`.

## Layout & verifier contract

Identical to v1 — see `../humble-vs-super-v1/README.md` for the full layout, the
`bugfix_verify.py` swap mechanism, and the blindness argument. The only structural
difference is that each `verify.py` emits **several** named correctness criteria instead
of a single `fix_correct`. `bugfix_verify.py` is reused **byte-identical**.
