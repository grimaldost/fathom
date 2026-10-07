---
description: Render a fathom scorecard from the committed ledger (idempotent; spends nothing)
argument-hint: "<bank> [--dataset-version V] [--per-trial]"
allowed-tools: Bash
---

Render the fathom scorecard for a bank from its committed ledger.

1. Resolve the data root: `$FATHOM_HOME` if set, else the nearest directory at or
   above the current one whose `fathom.toml` has a `[data_root]` table, else ask
   the user. The directory must carry that marker, and it must not be the
   plugin's own tree, a plugin cache directory, or inside either. If
   `$FATHOM_HOME` is set but the current directory sits inside a different data
   root, ask the user which one they mean: `FATHOM_HOME` wins without any error.
2. From the data root directory, run the engine this plugin ships:
   `uv run --no-dev --frozen --project "${CLAUDE_PLUGIN_ROOT}" python -m fathom --home "<data root>" report $ARGUMENTS`
   Keep both uv flags: `--no-dev` stops the first call from installing the
   development tools into the plugin's environment, and `--frozen` uses the
   plugin's lock file as shipped instead of rewriting it.
3. The scorecard lands at `report/scorecard-<bank>.md` in the data root (not
   committed; regenerable at any time). Open it and summarize it for the user.

When reading it:
- Lead with the **Per-Criterion Pass Rates** table: it shows where arms differ.
  The headline pass rate counts a trial as a pass only when every criterion is
  true.
- **Economy** gives min/median/max per trial; where the ranges overlap, the arms
  are not separated at this number of trials. **Arm Health**, when present, marks
  arms whose trials reached `max_turns`: their pass rates are lower bounds.
- **Pairwise vs Bare Anchor** appears only when the ledger holds pairwise grading
  rows; `fathom run` does not write them, so it is normally absent.
- Calibration sections render only for banks that ship `scores.toml` and
  `[verify] hard_criteria`.
- With few trials, every difference is directional; the verdict lines say so.
- By default the scorecard shows the bank's current `dataset_version` and warns which older
  versions it left out. `--dataset-version V` renders an older one instead, into
  `report/scorecard-<bank>--V.md` so the current scorecard stays; its first line says it is a
  historical view, and its calibration and turn caps come from the current `tasks/` tree. A
  version the ledger does not hold exits 1 and lists the ones it does.
- `--per-trial` writes the scorecard as without it, then prints a table to stdout with one
  line per trial: status, run rows, estimated USD, input and output tokens, turns and
  wall-clock seconds, each summed over the trial's run rows. A `*` after a USD figure means a
  run of that trial reported no cost, so the figure leaves it out. Trials are keyed by
  config hash, so two arms that share a name stay apart, each labelled with a hash prefix. It
  combines with `--dataset-version`.
- `fathom report` reads `ledger/<bank>.jsonl` and `tasks/<bank>/` in the data
  root; it takes no directory flags. With no ledger for the bank it exits 1 and
  names the path it looked for.
