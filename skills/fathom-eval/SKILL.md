---
name: fathom-eval
description: >
  Run and author scenario-blind tool-effectiveness evals with fathom — build a task
  bank and its arms, execute a scenario matrix against it, render the blind
  scorecard, and gate spend with the real-spawn smoke check. Use when the user wants
  to measure whether a coding tool, skill, prompt, plugin, hook, model tier, or
  execution strategy is worth it: "run a fathom eval", "A/B this skill", "does this
  skill actually help", "score this bank", "run the eval matrix", "compare bare vs
  armed", "author an eval bank/scenario/task", "write a verifier", "set up a fathom
  data root", "fathom init", "regenerate the scorecard", "is the bare arm ever
  failing", "dry-run the cost", "smoke first". Covers finding the data root, the
  validate→plan→smoke→run→report recipe, the bank/task/scenario schemas and the
  verify.py contract (in reference/authoring.md), the strategy catalog
  (single-session, gated-session, gated-review, reprompt-session, series), the cost
  rails, and the four invariants. Not for hand-editing the append-only ledger (never
  edit it); not for ordinary one-off coding or bug-fixing that is not an eval (that
  is plain implementation work); not for running the convoy multi-PR engine directly
  (that is convoy — fathom only drives it as the series arm).
---

# fathom — running and authoring tool-effectiveness evals

fathom measures whether an AI coding tool is worth using: it runs real coding tasks
under different configurations and execution strategies (**arms**), scores each
result **blind to which arm produced it**, and joins quality with cost (tokens,
turns, wall-clock, USD) into scorecards that accumulate over time.

To build a bank — data root, `bank.toml`, `task.toml`, fixtures, the verifier,
reference solutions, arms, `config_hash` — follow
[`reference/authoring.md`](reference/authoring.md). It is the complete guide. This
file covers running what is built.

A few bright lines, because breaking them spends money wrongly or corrupts the
record:

- **Never run a paid matrix without `fathom smoke` passing first**, this session.
- **Never edit `ledger/<bank>.jsonl` by hand.** It is append-only; reports regenerate
  from it. `fathom void` excludes a bad trial by appending a row.
- **Never point fathom at a plugin cache directory or the engine's own tree.** The
  ledger is committed and lives in the user's data root.
- **Pass `--scenarios-dir` for any bank whose arms live in a subdirectory**, or the
  run silently uses the arms in `scenarios/`.

## Running fathom, and finding the data root

This plugin runs the engine it ships. Every command below is written `fathom …`;
from the plugin, run it from the data root directory as

```sh
uv run --no-dev --frozen --project "${CLAUDE_PLUGIN_ROOT}" python -m fathom --home "<data root>" …
```

where the plugin root is the directory two levels above this skill's own
directory. This is the command the plugin's MCP server builds. Keep both uv flags:
`--no-dev` stops the first call from installing the development tools into the
plugin's environment, and `--frozen` uses the plugin's lock file as shipped instead
of rewriting it. The module form `python -m fathom` is used rather than the `fathom`
console script because some application-control policies block console-script
executables. If the user has fathom installed as a tool
(`uv tool install git+https://github.com/grimaldost/fathom@vX.Y.Z`), plain `fathom …`
is the same.

The **data root** is the user's directory of evaluation data, marked by a
`fathom.toml` with a `[data_root]` table:

```
<data root>/
  fathom.toml            # the marker; also accepted reconcile discrepancies
  .gitignore             # .fathom/ and report/
  .gitattributes         # LF line endings for every text file
  tasks/<bank>/          # banks
  scenarios/             # arms (*.toml), optionally one subdirectory per bank
  ledger/<bank>.jsonl    # committed, append-only results
  docs/reports/          # write-ups, and the generated LEDGER-INDEX.md
  docs/STATUS.md         # the index of analyses
  .fathom/               # runtime state (run locks, spawn streams); not committed
  report/                # rendered scorecards; not committed
```

Resolve it before running anything: `FATHOM_HOME` if set, otherwise the nearest
directory at or above the current one whose `fathom.toml` has `[data_root]`. It must
carry the marker, and it must not be the plugin's own tree, a plugin cache directory,
or inside either. If no directory qualifies, ask the user for their data root; if
they have none, create one with `fathom init <dir>`. It writes `fathom.toml` (the marker), a
`.gitignore` listing `.fathom/` and `report/`, and a `.gitattributes` whose first
rule, `* text=auto eol=lf`, pins LF line endings for every text file; it creates
`tasks/`, `scenarios/`, `ledger/` and `docs/reports/`; and it never overwrites a
file. The authoring guide, section 2, has the details.

The marker is the two lines `[data_root]` and `schema = 1`. `schema` must be the
integer 1: a marker without it, or with any other value (`"1"` in quotes included),
is refused wherever the engine meets it, and the search for a data root stops there
rather than walking past it. A marker with a later schema was written for a newer
fathom; the error asks to upgrade the engine (for the plugin, update the plugin).

`FATHOM_HOME` wins over the directory search, and the engine raises no error when it
names a different valid data root from the one the current directory sits in. If the
two disagree, ask the user which one they mean before running anything that writes or
spends. `fathom run` prints `data root: <path>` before its plan (dry runs included);
check it against the data root you intended.

The engine itself resolves the data root the same way (`--home`, then
`FATHOM_HOME`, then walking up from the working directory). It also accepts, with a
warning, an unmarked working directory that holds `tasks/` or `ledger/`; the plugin
does not, since a tool call has no terminal to warn on. Path options such as
`--scenarios-dir` and `--tasks-dir` resolve against the working directory, so run
commands from the data root directory or give those paths absolutely.

## The recipe

An **analysis** is a scenario matrix run against a task **bank**, scored into a
**scorecard**. In order:

```sh
# 0. Free: which engine version runs.
fathom --version

# 1. Free: can the bank tell arms apart? (fixture fails, solution passes, gate runs)
fathom validate <bank> [--strict]

# 2. Free: arms, trial count, worst-case USD ceiling, resume state. Spawns nothing.
fathom run <bank> --dry-run [--repeats K] [--scenarios-dir DIR]

# 3. A few cents: the real-spawn go/no-go gate. Expect "SMOKE RESULT: ALL PASS".
#    Pass --no-engine-boundary when the data root has no scenarios/series.toml.
fathom smoke

# 3b. Optional, a little: prove each treatment arm's injection reaches a live spawn.
#     `fathom run` repeats this before it spends unless --skip-arming-check.
fathom verify-arming [--scenarios-dir DIR]

# 4. Paid: the matrix. Resumable; re-invoking skips completed trials.
fathom run <bank> [--repeats K] [--scenarios-dir DIR] [--limit N] [--tasks ID,ID] \
    [--max-spawn-usd USD] [--max-run-usd USD] [--include-holdout]

# 5. Free: render report/scorecard-<bank>.md from the ledger. Regenerate any time.
fathom report <bank>
```

Slash commands wrap the main steps: `/fathom:smoke`, `/fathom:plan`, `/fathom:run`,
`/fathom:report`, `/fathom:reconcile`. The MCP tools `plan`, `report` and `smoke`
return the same results as structured data. There is **no** `run` MCP tool: a paid
matrix that can take hours is a shell command, not a tool call. `fathom stop <bank>`
asks a running matrix to halt after the trial in flight.

A worked example of the arithmetic: a bank `example` with one task and two arms
(`bare`, `nudge`) kept in `scenarios/example/` needs
`--scenarios-dir scenarios/example`, and `--repeats 3` plans 2 arms × 1 task × 3 = 6
trials, minus any already completed.

After a run, keep the data root's derived records current:

- `fathom index --write` re-renders `docs/reports/LEDGER-INDEX.md`, the stamp of each
  ledger's hash and completed trials per arm; commit it with the ledgers. Without
  `--write` it only checks, and exits 1 when stale.
- `fathom reconcile` checks every fact the data root records twice; exit 13 means a
  disagreement or a stale accepted exception.
- Write the result up under `docs/reports/` and list it in `docs/STATUS.md`.

## Cost, and when not to run

- The plan's ceiling is **planned trials × the per-spawn cap in force**
  (`--max-spawn-usd` if given, else $5), with series trials priced by their spawn
  count: per PR, one implementation, the template's fix attempts, and under a
  blocking review one review more than the fix attempts, each at its cap ($20, $3 and
  $5 unless `--max-spawn-usd` is given). It is a worst case, not an estimate.
- **The `expected:` line** under the plan's `planned:` line is the estimate: what a trial
  of the same strategy has cost in this bank's own ledger. It is the median over completed
  trials (a trial's cost is the sum of its run rows), per strategy and, where a model has
  at least 5 trials, per model, with the trial count `n`; planned trials times that median
  is the expected spend. A trial with no run rows, a run whose cost the provider did not
  report, an errored trial and a voided one are left out, and a strategy with no history
  is named as unpriced. Nothing is printed on an empty ledger. It is information only:
  no exit code or rail depends on it, and the ceiling and `--max-run-usd` still bound the
  spend. Read the two together: a ceiling far above the expected spend says how loose the
  cap is, not that the run will cost the ceiling.
- **`--max-spawn-usd`** (older spelling `--max-budget-usd`) is the cap for each
  **spawn**, not a run total. Raising it loosens the runaway guard, which is why the
  printed ceiling tracks it. A series trial spawns several agents, each under the
  cap.
- **`--max-run-usd`** stops one invocation between trials once it has spent that
  much (exit 14). For a guard across several invocations of a resumable matrix,
  stage the matrix and sum `cost_usd_est` from the ledger's run rows between stages.
- **`--limit N`** caps new trials (after resume filtering). The plan is ordered arm
  by arm, so `--limit` cuts whole arms off the end. **`--tasks ID[,ID...]`**
  restricts the run to named tasks — the way to buy a small screen before a full
  matrix.
- **`--tasks-dir` / `--ledger-dir`** relocate the bank source and the ledger.
  `--ledger-dir` writes the record somewhere other than the committed `ledger/`; use
  it only for a side study kept apart on purpose, since `fathom report` has no
  matching flag.
- `--skip-credential-check`, `--skip-bank-validation` and `--skip-arming-check` each
  turn off one pre-spend check, only for a re-run whose checks passed this session.
  `--no-lock` and `--lock-wait-s SECONDS` control the per-bank run lock.
  `fathom run --help` describes every flag.
- Prefer a `--dry-run` and a small `--tasks` or `--limit` pilot before a full matrix.
  Re-running resumes; nothing already bought is repeated.

Do **not** start a paid run when smoke has not passed this session, the plan has not
been reviewed, the bank's arms live in a subdirectory but `--scenarios-dir` was not
set, or you only need to re-read an existing result (`report` is free).

## Environment and exit codes

- `FATHOM_HOME` — the data root.
- `FATHOM_STREAM_DIR` — optional. Where each spawn's raw stream-json output is kept,
  one file per spawn, named after the trial, for later analysis (tool calls, skill
  activation). When unset, `fathom run` keeps them under the data root's
  `.fathom/streams/<bank>/` for arms with a `[context]` inject or a tool grant. A
  series arm's agents are spawned by its engine, not by fathom, and none of their
  streams is kept there. A failure to keep a stream never affects the trial.

Neither variable, nor any other `FATHOM_*` variable, is in a trial agent's environment,
and neither is the directory fathom was started in (`PWD`, `OLDPWD`) or any variable
whose value names the data root (`PATH` keeps only its entries outside it): fathom
removes them from each spawn's environment, a series engine's included, and from the
environment of a gated arm's gate commands. `FATHOM_HOME` would tell the agent where
the data root is, which holds each task's reference solution and verifier, and the
stream tag carries the arm's name. A gate that finds its tools only through a virtual
environment inside the data root therefore fails. An arm's own `[env]` table is
applied after that and may set any name, but `${FATHOM_HOME}` in it substitutes as
empty. Each spawn gets its own copies of the arm's `[context]` and `[plugins]` files,
so a mounted plugin must work without a `.venv` or `.git` of its own; the arming check
spawns from copies too, so it shows a plugin that does not before a run. A fix spawn is
shown the gate commands as written, placeholders not filled in, and their output with
the task directory's and the data root's paths masked. Whatever a gate command
creates in the workspace is removed when it exits. The authoring guide (section 10,
"Tools and default-deny") says what is left to the bank author, and section 7 asks
verifiers to run the agent's code in a child process.

`fathom run` exits `0` on success, `10` on an infrastructure error (auth or usage
limit, fixture drift, lock timeout — the matrix stops cleanly and the ledger stays the
resume checkpoint), `11` on an unarmed treatment arm, `12` on an invalid bank, `14`
on the per-invocation spend rail, `15` when the credential has too little life left,
`16` when `fathom stop` halted it, and `1` on a usage error (unloadable bank, no
scenarios in the scenarios directory, unknown strategy, unknown `--tasks` id). Every
nonzero exit leaves the ledger as the resume checkpoint.

`fathom smoke` exits `0` only when every check was **proven**: a failed check and a
skipped one both make it nonzero. `fathom verify-arming` exits `0` when every
declaring arm is proven armed (or none declares a treatment), `11` when one is not,
and `1` when the scenarios directory holds no scenarios. `fathom validate` exits `12`
when a property fails (or, under `--strict`, warns or is unverifiable).
`fathom reconcile` exits `13` on a disagreement, a stale accepted exception, or a
refusal before any check ran.

## Strategy catalog

A scenario's `strategy` is required; an unknown name is rejected before anything
spawns. Details in the authoring guide, section 10.

| strategy | what it does | spawns per trial |
|---|---|---|
| `single-session` | the instruction, once; the usual control (`bare`) | 1 |
| `gated-session` | implementation, then the task's gate and a bounded fix loop | 1 + up to 2 |
| `gated-review` | gated-session plus one review pass and at most one more fix | more |
| `reprompt-session` | implementation + one unconditional generic reprompt; the control for the gate's information | 2 |
| `series` | drives an external multi-PR engine (convoy is the reference) | many |

`series` needs the engine's checkout (`[tools] source = "repo"`, `repo = <path>`) and
a `series.toml` template in each task; it is long and dominates a matrix's cost.
`gated-*` need the task to define a `[gate] run` (or the arm a `[gate] extra`).

## The four invariants (ADRs under the engine's `docs/adr/`)

- **Blindness** (ADR-0003) — verifiers see only a copy of the final workspace, with
  no arm identity in argv or environment and no variable naming the data root, from an
  empty working directory; cost joins **after** scoring.
- **Append-only ledger** (ADR-0002) — no code rewrites a ledger line; resume key =
  `(bank, dataset_version, task_id, config_hash, repeat)`; only
  `status == "completed"` counts as done.
- **Spawn isolation** (ADR-0004) — a credential-only temporary `CLAUDE_CONFIG_DIR`;
  headless default-deny (never `bypassPermissions`); explicit allow and disallow
  lists; no `FATHOM_*` variable, no launch directory and no variable naming the data
  root in a spawn's or a gate command's environment; a trial spawn's command line names
  staged copies of the arm's `[context]` and `[plugins]` files.
- **Standard-library core** — modules under `src/fathom/` import the standard
  library only.

## Reading the scorecard

After `fathom report <bank>`, read `report/scorecard-<bank>.md` in the data root:

- **Per-Criterion Pass Rates** — where arms usually differ. Lead with it; the headline
  pass rate counts a trial as a pass only when every criterion is true.
- **Economy** — per arm: tokens, turns, wall-clock, spawns per trial, estimated USD,
  with min/median/max. Overlapping ranges mean the arms are not separated at this
  number of trials.
- **Arm Health** — present when trials reached `max_turns`; those pass rates are
  lower bounds.
- **Efficiency** — per-trial means, quality per 100k tokens, and a Pareto mark
  (`★`, or `★?` when the token ranges overlap). This is where "is the treatment worth
  its cost?" is read.
- **Pairwise vs Bare Anchor** — appears only when the ledger holds pairwise grading
  rows, which `fathom run` does not write.
- **Calibration** — only for banks that ship `scores.toml` and `hard_criteria`.

## When not to use this skill

- The task is ordinary implementation or debugging, not an eval — just do the work.
- You want to run convoy's multi-PR engine on real work — use convoy directly; fathom
  only drives it as a measured arm.
- You want to change a past result — you cannot; the ledger is append-only, and an
  invalidated run is archived (`ledger/archive/`), never edited.
- You only want an impression of whether a tool "feels" better, without a scored,
  blind comparison — that is not what fathom is for.
