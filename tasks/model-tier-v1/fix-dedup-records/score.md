# score — fix-dedup-records

- **author_score:** 50
- **band:** mid (HOLDOUT)
- **predicted tier:** mid / Sonnet (26-55)
- **rationale:** The bug report names only the case symptom, but the documented contract
  also requires surrounding-whitespace normalization and keep-first semantics. A
  symptom-only `.lower()` fix passes one criterion and fails the others; reading the
  whole contract is mid-tier work. Reserved as the bank holdout.
