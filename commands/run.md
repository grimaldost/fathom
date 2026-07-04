---
description: Run the paid fathom scenario matrix against a bank (real spend; resumable)
argument-hint: "<bank> [--repeats K] [--scenarios-dir DIR] [--limit N] [--max-budget-usd USD] [--include-holdout]"
allowed-tools: Bash
---

Run the fathom eval matrix — **this spends real money**. Do not skip the
preconditions.

Preconditions:
1. `uv run python -m fathom smoke` passed **this session** (run `/fathom:smoke` if not).
2. `uv run python -m fathom run <bank> --dry-run …` was reviewed and the trial count + USD
   ceiling are acceptable (run `/fathom:plan` if not).
3. If the bank ships its own arms in a subdir, `--scenarios-dir` is set — or the
   wrong arms run silently.

Then:
1. Resolve the fathom checkout (`$FATHOM_HOME`, else the current fathom repo,
   else ask). Never run from a plugin cache-clone — the ledger it appends to is
   the committed longitudinal record and must live in the source tree.
2. From that directory, run: `uv run python -m fathom run $ARGUMENTS`

Tell the user before/while running:
- It is resumable — re-invoking skips completed trials; interrupt and resume freely.
- `--limit N` caps fresh trials; `--max-budget-usd USD` is the real per-**spawn**
  cap (a `series` trial spawns several subagents and can spend several times it).
- `--include-holdout` also runs the bank's sealed holdout tasks (trials marked
  `holdout` in the ledger, reported separately) — only for a deliberate promotion
  decision (ADR-0005), never by default.
- Results append to `ledger/<bank>.jsonl` (committed). Render the verdict with
  `/fathom:report <bank>` afterward.
