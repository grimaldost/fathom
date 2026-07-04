# score — fix-clamp

- **author_score:** 10
- **band:** low
- **predicted tier:** weak / Haiku (0-25)
- **rationale:** A one-line conditional bug (the upper bound is simply missing from
  `clamp`); the docstring states the full contract and a single `if x > hi` restores
  it. No edge-case reasoning beyond reading the spec — the weakest tier should clear it.
