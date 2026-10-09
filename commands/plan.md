---
description: Plan a fathom matrix (dry-run) — arms, trial count, USD ceiling, and resume state; spawns nothing
argument-hint: "<bank> [--repeats K] [--scenarios-dir DIR] [--tasks-dir DIR] [--limit N] [--tasks ID,ID] [--interleave] [--max-spawn-usd USD] [--include-holdout]"
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
3. Report the arm names the plan printed (each arm shows its name and config_hash
   prefix to distinguish forks from pools), the trial count (and how many are
   already done), and the USD ceiling: planned trials × the per-spawn cap in force
   (`--max-spawn-usd` if given, else $5), with series trials priced by their spawn
   count.
   When the bank's ledger already holds completed trials, the plan also prints one
   `expected:` line after the `planned:` line: the median cost per trial for the
   planned strategies (and per model where a group holds at least 5 trials), with
   its trial count, and that median times the planned trials. Report it beside the
   ceiling, as an estimate from this ledger's own history. It is not a cap, and no
   run is refused or stopped by it. With no history, no line is printed.
   Every plan then prints one `replication:` line: the bank's `[plan]
   repeats_per_cell` (in `bank.toml`) against the repeats asked for. Report it
   whenever it says `directional`: the bank declares no plan, declares 1, or the
   run asks for fewer repeats than the plan declares (a screen), so any contrast
   from the run is directional, not replicated. A malformed `[plan]` stops the
   plan with exit 1 and an `error:` line naming the `bank.toml` and the fault.
   When nothing is planned (the bank is finished for the requested repeats), two more
   lines follow the `planned:` line: `one more repeat:` gives the ceiling of one more
   trial per arm and task and the `--repeats` value that plans it ("at least one more"
   when the cells hold different numbers of repeats), and `completed in the ledger for
   these arms:` gives the count of completed trials across all repeats, which is the
   count the scorecard uses. Report both, so the user can decide on one more repeat
   without a second planning run.

Guardrails to surface:
- If the bank's arms live in a subdirectory of `scenarios/` (for example
  `scenarios/example/`), **`--scenarios-dir` is required**, or the wrong arms are
  planned: the run reads `<dir>/*.toml` non-recursively. Check the arm names in
  the plan against what the user intends, and `ls scenarios/` in the data root if
  unsure.
- The ceiling is a worst case, not a spend cap, and the `expected:` line is a past
  median, not a promise. The real per-spawn cap is
  `--max-spawn-usd`, and `--max-run-usd` caps what one invocation may spend; both
  apply to the actual run.
