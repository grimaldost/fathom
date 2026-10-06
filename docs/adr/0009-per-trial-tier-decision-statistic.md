# ADR-0009 — The tier decision statistic is one draw per trial, not one per criterion

> **Note (0.8.0):** particulars were removed from this record for the standalone engine.

- **Status:** Accepted
- **Date:** 2026-08-12
- **Supersedes:** ADR-0007 **D3** only. ADR-0007 records six decisions under a single
  number; D1, D2, D4, D5 and D6 stand unchanged, so superseding the whole document
  would retire five decisions nothing is wrong with. ADR-0007's status now reads
  "Accepted (D3 superseded by ADR-0009)", which is the ADR-log convention applied at
  the granularity that document actually decides at.

## Context

ADR-0007 D3 computes a (task, arm) cell's confidence interval on hard criteria **pooled
across trials**: `successes = Σ true HARD criteria`, `n = Σ total HARD criteria`. It
recorded the risk in one line — "the pooled proportion treats correlated criteria as
independent, so the CI is a heuristic width, not an exact coverage guarantee" — and
shipped anyway, with nothing in place to check how correlated they actually are.

Hard criteria that check parts of one piece of work are not independent draws: they tend to
pass or fail together, because one mistake in the work usually breaks several of them at
once. In the limiting case a task's hard set comes out all-true or all-false as a unit, and
nothing in the pooled estimator can tell that case from independent criteria.

In that case a k-criterion cell contributes `k x n` draws while carrying the information of
`n`. Every interval is narrowed by roughly `sqrt(k)` for free, and repeat counts sized
against those intervals cannot resolve the cells they were bought for. Two consequences
follow from the arithmetic alone:

* Under one draw per trial, a noiseless rung — the weak arm failing every trial, the mid
  and strong arms passing every trial — reads **indeterminate at repeats 2 and 3**,
  because 2/2 vs 0/2 and 3/3 vs 0/3 have overlapping Wilson intervals. Four is the first
  repeat count at which a perfect contrast separates at all. A repeat count chosen
  against pooled intervals can therefore be too small to decide anything.
* A positive control read by "the weak arm's CI is disjoint from the strong arm's" has
  low power at realistic rates and modest repeats: it can stay silent most of the time
  even when the ladder really does separate, and a control that stays silent cannot
  license anything.

## Decision

**A trial is one Bernoulli draw. The draw is `every hard criterion true`.**

`arm_task_stats` returns `mean = passing_trials / trials` and a Wilson interval computed
on that same integer pair, exposed as `draws = (passing, trials)`. The key it replaces
was named `pooled`, after the inflation this decision removes.

It also returns `mixed_trials`, the count of trials where some hard criteria passed and
others failed, and the scorecard renders it. The conjunction is the honest single draw
either way — if criteria ever do come apart it is conservative rather than inflated —
but the assumption behind "one draw" is now checkable from the ledger instead of
asserted, and a nonzero count is the signal to re-open this ADR.

**A positive control is read by its own rule, not off the diagonal.** A bank may declare
one control in `scores.toml`'s `[control]` table (`task`, `weak_arm`, `strong_arm`,
`alpha`, `min_repeats`). It separates iff a **one-sided Fisher exact test** on the two
arms' per-trial pass counts gives `p <= alpha` at no fewer than `min_repeats` repeats per
arm. A declared control is excluded from the confusion matrix and from the per-band
dose-response; it renders in the per-task table flagged as a control.

## Alternatives considered

- **Keep pooling and widen ε instead.** Rejected: ε is in pass-rate units and the defect
  is in the interval's `n`. Widening ε makes the point-estimate criterion looser without
  making the interval honest, so the two criteria disagree in a *new* place rather than
  agreeing correctly.
- **Model the correlation (a beta-binomial / cluster-robust interval).** Rejected as
  unnecessary: at ρ = 1 the cluster-robust interval collapses to exactly the per-trial
  one, and total correlation is the case described above. It would add a nuisance
  parameter estimated from the same handful of trials it is meant to correct.
- **Score the mean per-trial fraction and keep a pooled CI (the shipped hybrid).**
  Rejected: this is the state being fixed. It reports a point estimate from one
  estimator and an interval from another, which is how a 0.5-vs-1.0 cell could look
  decisive in the mean and be indeterminate in the interval.
- **Keep disjoint Wilson CIs as the control rule and buy more repeats.** Costed, not
  dismissed: for the same power, the disjoint-interval rule needs more repeats than the
  Fisher rule. Both were computed by exact enumeration; the cheaper rule won on
  arithmetic, not on preference.
- **Drop the control and read the confusion matrix alone.** Rejected: an uninterpretable
  null is not a null, and a bank with no control cannot tell "the score does not predict
  the tier" from "this bank had no headroom".

## Consequences

**The invariant this creates:** *a (task, arm) cell contributes exactly as many draws as
the trials bought for it.* Any future statistic over `hard_criteria` — the oracle-level
slicer gated behind ADR-0008 included — inherits it. A criterion count is a difficulty
knob, never a sample size.

Repeat counts must now be derived, and the derivation is executable rather than quoted:
`tests/test_calibration.py::TestPerTrialScoring` re-runs the noiseless rung at repeats
2/3/4/5, and `TestFisherExact` and `TestPositiveControl` in the same file pin the control
rule. A bank that pre-registers its repeat counts should recompute its control's power by
exact enumeration in its own tests, so a repeat count nobody can reproduce fails a test.

**Point estimates do not move.** Where the hard criteria are perfectly correlated, the
per-trial point estimates equal the pooled ones exactly; only the intervals widen. This is
a re-estimation, not a revision of the record.

What gets harder: cells cost more. A tier verdict needs at least four repeats per arm before
even a perfect contrast can separate, and a positive control needs more on the two arms its
rule reads. That is the price of an interval whose `n` is the number of trials someone
actually paid for.
