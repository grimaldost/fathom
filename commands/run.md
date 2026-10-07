---
description: Run the paid fathom scenario matrix against a bank (real spend; resumable)
argument-hint: "<bank> [--dry-run] [--repeats K] [--scenarios-dir DIR] [--tasks-dir DIR] [--ledger-dir DIR] [--limit N] [--tasks ID,ID] [--interleave] [--max-spawn-usd USD] [--max-run-usd USD] [--include-holdout] [--skip-credential-check] [--skip-bank-validation] [--skip-arming-check] [--no-lock] [--lock-wait-s SECONDS]"
allowed-tools: Bash
---

Run the fathom eval matrix — **this spends real money**. Do not skip the
preconditions.

Preconditions:
1. The smoke gate passed **this session** (run `/fathom:smoke` if not; it takes
   `--no-engine-boundary` when the data root has no `scenarios/series.toml`).
2. The plan was reviewed, and its arm names, trial count and USD ceiling are
   acceptable (run `/fathom:plan` if not).
3. If the bank's arms live in a subdirectory of `scenarios/`, `--scenarios-dir` is
   set, or the wrong arms run silently.

Then:
1. Resolve the data root: `$FATHOM_HOME` if set, else the nearest directory at or
   above the current one whose `fathom.toml` has a `[data_root]` table, else ask
   the user. The directory must carry that marker, and it must not be the
   plugin's own tree, a plugin cache directory, or inside either: the ledger the
   run appends to is the committed record and belongs in the user's data root,
   and a cache refresh deletes that tree. If `$FATHOM_HOME` is set but the
   current directory sits inside a different data root, ask the user which one
   they mean before spending: `FATHOM_HOME` wins without any error.
2. From the data root directory (so relative path options resolve inside it), run
   the engine this plugin ships:
   `uv run --no-dev --frozen --project "${CLAUDE_PLUGIN_ROOT}" python -m fathom --home "<data root>" run $ARGUMENTS`
   Keep both uv flags: `--no-dev` stops the first call from installing the
   development tools into the plugin's environment, and `--frozen` uses the
   plugin's lock file as shipped instead of rewriting it.

Tell the user before and while running:
- Before the first spawn, `fathom run` checks that the credential has life left
  (exit 15 if not), that the bank validates (exit 12 if not), and, with one cheap
  real spawn per treatment arm, that each arm's treatment reaches the spawn
  (exit 11 if not; the same check as `fathom verify-arming`). Each refusal leaves
  the ledger untouched. `--skip-credential-check`, `--skip-bank-validation` and
  `--skip-arming-check` each turn one check off. Use them only to re-run a matrix
  whose checks already passed this session (or, for the credential check, when
  the credential lives where the check cannot read it), never to get past a
  refusal.
- A run holds a per-bank lock, so two matrices do not share one credential's rate
  budget; a second run on the same bank waits. `--lock-wait-s SECONDS` gives up
  after SECONDS (exit 10, ledger untouched); `--no-lock` skips the lock, only when
  the other run uses another credential. `--dry-run` plans without spending, as
  `/fathom:plan` does, and takes no lock.
- It is resumable: re-invoking skips completed trials, so interrupting and
  resuming loses nothing already bought. `fathom stop <bank>` (same invocation
  form, `stop` in place of `run`) asks a running matrix to halt after the trial in
  flight (the run exits 16).
- `--limit N` caps new trials, counted from the start of the plan's order: arm by
  arm by default, so `--limit` cuts whole arms off the end; with `--interleave`,
  repeat by repeat, so `--limit` keeps whole repeats (arms × tasks runs repeat 0 of
  every arm). `--interleave` changes the order only, not which trials are bought.
  `--tasks ID[,ID...]` restricts the run to named tasks,
  the way to buy a small screen first. `--max-spawn-usd USD` is the cap for each
  **spawn** (default $5), not a run total; a series trial makes several spawns,
  each under the cap. Raising it loosens the runaway guard and raises the printed
  ceiling to match. `--max-run-usd USD` stops this invocation between trials once
  it has spent that much (exit 14).
- `--tasks-dir` and `--ledger-dir` relocate the bank source and the ledger (the
  defaults are `tasks/` and `ledger/` in the data root). They resolve against the
  current directory, like any command-line path. `--ledger-dir` writes the
  append-only record somewhere other than the committed `ledger/`, so use it only
  for a side study kept apart on purpose: `fathom report` has no matching flag.
- `--include-holdout` also runs the bank's sealed holdout tasks (marked `holdout`
  in the ledger, reported separately). Only for a deliberate decision to spend
  them (ADR-0005), never by default.
- An authentication or usage-limit failure stops the matrix cleanly (exit 10) and
  records nothing for that trial; re-invoke once it is fixed.
- The argument hint lists every flag except the older spelling `--max-budget-usd`;
  `fathom run --help` describes each one.
- Results append to `ledger/<bank>.jsonl` in the data root. Afterwards, re-render
  the ledger index (`index --write`, same invocation form as above). The `run summary:`
  line says `ledger index is now stale: refresh it with fathom --home <data root> index
  --write` (with `--home`, since step 2 passes it) when the rows the run appended left a
  kept index out of date; it says nothing on a dry run, when the run appended no rows,
  when the index is current, when the root keeps no index, or when `--ledger-dir` sent
  the rows to a side ledger. Then run `/fathom:reconcile`, and render the scorecard with
  `/fathom:report <bank>`.
