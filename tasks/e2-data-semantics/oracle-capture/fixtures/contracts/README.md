# Contracts and sealed artifacts

## `daily_revenue.md`

The declared contract for the daily net revenue extract.

## `finance_known_good.json`

Figures finance derived by hand from the source documents, independently of this
pipeline. Used to settle disagreements about what a day's number should be.

## `tests/baseline_daily_revenue.json` — SEALED

A snapshot of what `daily_revenue.main()` printed at release 3.2. It was captured
from this pipeline's own output, so it records what the pipeline *did*, not what
it *should* do.

It is frozen: it is not regenerated, and it is not edited to make a suite green.
When the pipeline's output legitimately diverges from it, record the divergence
and the reason in `DIVERGENCES.md` and leave the file alone. Repairing a sealed
baseline is a change of its own, with its own reason.
