---
description: Plan a fathom matrix (dry-run) — trial count, USD ceiling, and resume state; spawns nothing
argument-hint: "<bank> [--repeats K] [--scenarios-dir DIR] [--limit N] [--include-holdout]"
allowed-tools: Bash
---

Plan a fathom eval matrix without spawning or spending anything.

1. Resolve the fathom checkout (`$FATHOM_HOME`, else the current fathom repo,
   else ask). Never run from a plugin cache-clone.
2. From that directory, run: `uv run python -m fathom run $ARGUMENTS --dry-run`
   (append `--dry-run` if the user did not).
3. Report the trial count, the arm names the plan printed, the USD ceiling
   (`trials × the per-spawn cap in force` — `--max-spawn-usd` if given, else $5),
   and the resume state (how many trials are already done vs fresh).

Guardrails to surface:
- If the bank ships its own arms in a subdir (e.g. `skill-pyeng-v1` →
  `scenarios/skill-pyeng`), **`--scenarios-dir` is required** or the wrong arms
  are planned. Check `ls <checkout>/scenarios/` if unsure.
- The USD ceiling is advisory, not a spend cap; the real per-spawn cap is
  `--max-spawn-usd` (used on the actual run).
