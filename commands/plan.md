---
description: Plan a fathom matrix (dry-run) — arms, trial count, USD ceiling, and resume state; spawns nothing
argument-hint: "<bank> [--repeats K] [--scenarios-dir DIR] [--tasks-dir DIR] [--limit N] [--tasks ID,ID] [--max-spawn-usd USD] [--include-holdout]"
allowed-tools: Bash
---

Plan a fathom eval matrix without spawning or spending anything.

1. Resolve the data root: `$FATHOM_HOME` if set, else the nearest directory at or
   above the current one whose `fathom.toml` has a `[data_root]` table, else ask
   the user (a new one is made with `fathom init DIR`). The directory must carry
   that marker, and it must not be the plugin's own tree, a plugin cache
   directory, or inside either. If `$FATHOM_HOME` is set but the current directory
   sits inside a different data root, ask the user which one they mean:
   `FATHOM_HOME` wins without any error.
2. From the data root directory (so a relative `--scenarios-dir` resolves inside
   it), run the engine this plugin ships:
   `uv run --no-dev --frozen --project "${CLAUDE_PLUGIN_ROOT}" python -m fathom --home "<data root>" run $ARGUMENTS --dry-run`
   (append `--dry-run` only if the user did not).
   Keep both uv flags: `--no-dev` stops the first call from installing the
   development tools into the plugin's environment, and `--frozen` uses the
   plugin's lock file as shipped instead of rewriting it.
3. Report the arm names the plan printed, the trial count (and how many are
   already done), and the USD ceiling: planned trials × the per-spawn cap in force
   (`--max-spawn-usd` if given, else $5), with series trials priced by their spawn
   count.

Guardrails to surface:
- If the bank's arms live in a subdirectory of `scenarios/` (for example
  `scenarios/example/`), **`--scenarios-dir` is required**, or the wrong arms are
  planned: the run reads `<dir>/*.toml` non-recursively. Check the arm names in
  the plan against what the user intends, and `ls scenarios/` in the data root if
  unsure.
- The ceiling is a worst case, not a spend cap. The real per-spawn cap is
  `--max-spawn-usd`, and `--max-run-usd` caps what one invocation may spend; both
  apply to the actual run.
