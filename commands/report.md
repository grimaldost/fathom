---
description: Render a fathom scorecard from the committed ledger (idempotent; spends nothing)
argument-hint: "<bank>"
allowed-tools: Bash
---

Render the fathom scorecard for a bank from its committed ledger.

1. Resolve the fathom checkout (`$FATHOM_HOME`, else the current fathom repo,
   else ask).
2. From that directory, run: `uv run python -m fathom report $ARGUMENTS`
3. The scorecard lands at `report/scorecard-<bank>.md` (gitignored, regenerable).
   Open it and summarize the verdict for the user.

When reading it:
- The **Per-Criterion Pass Rates** table is the discriminating signal — lead with
  it, not just the headline pass-rate.
- The **Pairwise vs Bare Anchor** section is **always empty in v1** (the judge
  ships dark) — do not present it as a populated quality axis.
- Calibration views render only for banks that ship `scores.toml` + `hard_criteria`.
