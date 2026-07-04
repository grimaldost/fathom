# ADR-0005 — Every bank carries sealed holdout tasks; a spent holdout is dev data

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

fathom's verdicts feed tuning loops (tool descriptions, prompts, method changes).
Anything tuned against the full task bank overfits it; the craft-collection
trigger-eval rounds demonstrated this concretely (a holdout run once stopped being
a holdout — recorded as an operating rule on 2026-06-10). Scores on tasks the
tuning loop has seen measure memorization of the bank, not tool effectiveness.

## Decision

Each bank's manifest names a holdout subset. Holdout tasks are excluded from
routine matrices and from any tuning iteration; they run only at declared
checkpoints (e.g., a version promotion), their results are reported in a separate
scorecard section, and once used to make a tuning decision they are reclassified
as dev tasks — replacements are authored and sealed before the next checkpoint.

## Alternatives considered

- **No holdout** — every task becomes dev data immediately; longitudinal
  improvement claims become unfalsifiable.
- **Rotating k-fold reuse** — statistically appealing but operationally heavy at
  a 3–5 task scale, and reuse across rounds still leaks tuning signal.

## Consequences

- New invariant: **holdout sealing** — bank manifests mark holdouts; matrices
  exclude them by default; reports separate them; spending one is a recorded
  event that triggers replacement authorship.
- Bank authorship cost rises slightly (holdouts must be replaced when spent);
  this is the price of falsifiable improvement claims.
