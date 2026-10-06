# Measured terms — a cost term in a comparison is purchased, not modelled

**The rule.** Any term that appears in a comparison must be **purchased at the smallest n that
resolves it** before the comparison is priced. A modelled term is admissible for **budgeting
only**, for deciding whether a run is affordable, and never as a quantity a verdict rests on.

## Why

A forward model of cost (tokens times price, turns times a per-turn figure) can miss the level
of a cost by a large factor, and a comparison is usually assumed to forgive that, because the
error should divide out on both sides of the contrast. It does not have to. Two arms differ in
exactly the things the model simplifies: how much context they carry, how often they delegate,
how many turns they take. So the model's error can differ between the arms, and then it lands
on the contrast itself, not only on the levels. A programme whose estimand contains a cost term,
and which models that term, reports a number whose error is unbounded in the direction that
matters.

## What follows in practice

- **Cheap tranche first.** Buy the smallest slice that resolves the disputed term before
  committing to the expensive one. If the forward model is wrong, the small slice finds out at a
  fraction of the price the full matrix would have paid to learn the same thing.
- **A modelled term is labelled everywhere it appears.** fathom reports a cost it did not
  measure as `null`, never `0` (`decision_cost_usd` in the calibration views), and a total that
  includes such a term says it is a lower bound. A modelled multiplier can be used to
  reserve budget; it cannot be published as a measurement.
- **A choice made on a tiny denominator inherits that denominator's noise.** Selecting a cell
  because a pilot showed headroom on three or four trials builds the selection on noise; complete
  the cell to a denominator that can carry the choice before relying on it.

## Scope

This governs terms inside an **estimand**, anything a published contrast is computed from. It
does not govern planning arithmetic: the dry-run ceiling, a budget line, or a go/no-go
affordability check may all use a model, and should say so.
