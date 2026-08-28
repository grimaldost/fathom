# Measured terms — a cost term in a comparison is purchased, not modelled

**The rule.** Any term that appears in a comparison must be **purchased at the smallest
n that resolves it** before the comparison is priced. A modelled term is admissible for
**budgeting only** — for deciding whether a run is affordable — never as a quantity a
verdict rests on.

## Why, with the number that bought the rule

A forward token model predicted a decision cost of **$0.085**; the measurement found
**$0.298**. That alone would be a familiar 3.5x calibration miss, and a comparison is
usually forgiving of those because the error is assumed to divide out on both sides.

It did not. The same model predicted the arm-to-arm **premium** at **$0.0800** where the
measurement found **$0.2252** — a **2.8x miss on the contrast itself**, not merely on the
levels. A differential error does not cancel. Any programme whose estimand contains a cost
term and models that term is reporting a number with an unbounded error in the direction
that matters.

## What follows in practice

- **Cheap tranche first.** Buy the smallest slice that resolves the disputed term before
  committing to the expensive one. The routing programme's small tranche was bought before
  a $240 one and revealed the forward model was wrong by 3.5x; had the expensive tranche
  gone first, the same discovery would have cost roughly 15x more to make.
- **A modelled term is labelled, everywhere it appears.** `decision_cost_usd` is reported
  as `null`, never `0`, and every total carrying it says it is a lower bound. Reporting a
  modelled term as a measured one is the shape that produced the x3.81 residue: real
  undercount, refuted mechanism, a multiplier usable for reserving budget and not
  publishable as a measurement.
- **A cell chosen on a tiny denominator inherits that denominator's noise into the
  choice.** A pilot cell was selected as the one with demonstrated headroom on a `bare`
  reading of **0/4**; completed to n=10 the same arm read **3/10**. The headroom was real
  but smaller, and the selection argument was built on noise.

## Scope

This governs terms inside an **estimand** — anything a published contrast is computed
from. It does not govern planning arithmetic: the dry-run ceiling, a budget line, or a
go/no-go affordability check may all use a model, and should say so.

*Promoted by the 2026-08-28 triage delta (FATH-B66), from the 2026-08-12 buy wave.*
