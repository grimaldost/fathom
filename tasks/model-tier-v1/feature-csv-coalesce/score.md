# score — feature-csv-coalesce

- **author_score:** 40
- **band:** mid
- **predicted tier:** mid / Sonnet (26-55)
- **rationale:** A small feature build from a SPEC (typed CSV reader) with three named
  edge cases — empty input, ragged rows (pad short / drop extra), and empty-cell type
  coercion — plus its own edge-covering tests. More than a one-liner: it requires
  holding several behaviors at once, so a weak model is mixed while a mid model clears it.
