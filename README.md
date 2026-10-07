<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/fathom-hero-dark.svg">
  <img alt="fathom" src="assets/fathom-hero-light.svg" width="100%">
</picture>

[![ci](https://img.shields.io/github/actions/workflow/status/grimaldost/fathom/ci.yml?style=flat-square&labelColor=2A3238&label=ci)](https://github.com/grimaldost/fathom/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.12%2B-00666D?style=flat-square&labelColor=2A3238)](pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-00666D?style=flat-square&labelColor=2A3238)](LICENSE)

**Scenario-blind tool-effectiveness evals.** fathom measures whether an AI coding tool is worth
using. It runs real coding tasks under different configurations and execution strategies
(**arms**), scores each result **without knowing which arm produced it**, and joins quality
with cost (tokens, turns, wall-clock, estimated USD) into a scorecard that accumulates over
time. Typical questions: does this skill, prompt, plugin or hook improve results; which model
tier is enough for this kind of task; did a new version of a tool regress.

This repository is the engine: the harness, its command line and its Claude Code plugin. It
ships no task banks and no results. Those are your data, and they live in a **data root** of
your own, usually a private repository.

## Install

Requirements: Python 3.12 or later, [uv](https://docs.astral.sh/uv/), git, and the `claude`
CLI on PATH with a working login. Each spawn authenticates from a copy of the CLI's
credential file and nothing else.

```sh
uv tool install git+https://github.com/grimaldost/fathom@v0.10.0
fathom --version
```

Or work from a clone: `uv run fathom …` inside it, or `uv run --project <clone> fathom …`
from anywhere else. To move to a later release, run `uv tool install` again with the new tag.

## Quick start

A **bank** is a set of coding tasks, each a starting repository, an instruction, and a
`verify.py` that scores the final state as named true/false criteria. An **arm** is one way
of attempting those tasks: model, effort, allowed tools, execution strategy, and any
treatment such as injected context. **To build a bank and its arms, read the authoring guide:
[`skills/fathom-eval/reference/authoring.md`](skills/fathom-eval/reference/authoring.md).** It
starts there, continues in `arming.md` and `bank-design.md` beside it, and covers the data
root, `bank.toml` and `task.toml`, fixtures, the verifier contract, reference solutions and
validation, what makes a bank able to discriminate, every arm field and strategy,
`config_hash`, running, and reading the scorecard.
[`examples/data-root/`](examples/data-root/) is a complete working example, explained file by
file in its [README](examples/data-root/README.md). The quickest first bank is a copy of it:
create a data root, copy the example's bank and arms into it, and edit them.

```sh
fathom init my-evals                          # create an empty data root
cd my-evals
cp -r <engine>/examples/data-root/tasks/example tasks/my-bank    # a bank to edit
cp -r <engine>/examples/data-root/scenarios/. scenarios/         # its two arms
# set name = "my-bank" in tasks/my-bank/bank.toml, then write your own tasks and arms
fathom validate my-bank                       # free: checks each task (below)
fathom run my-bank --dry-run --repeats 3      # free: arms, trial count, USD ceiling
fathom smoke --no-engine-boundary             # a few cents: spawn isolation on real spawns
fathom run my-bank --repeats 3                # paid; resumable
fathom report my-bank                         # free: writes report/scorecard-my-bank.md
fathom index --write                          # free: updates docs/reports/LEDGER-INDEX.md
fathom reconcile                              # free: do the derived records agree?
```

`<engine>` is a clone of this repository (`git clone https://github.com/grimaldost/fathom`).
What each step does:

- **`fathom validate`** runs each task's verifier twice, locally: on the untouched fixture,
  where at least one criterion must be false (there is work to do), and on the task's
  reference solution, where it must pass (the work can be done). It also runs the task's gate
  command if it has one, and checks that the scripts named by that command and by each gated
  arm's `[gate] extra` exist. It may print a `note:` saying that a paid run will keep each
  agent's raw output under `.fathom/streams/<bank>/`; that needs no action.
- **`fathom run --dry-run`** prints the data root, the arms it found, the trials still to buy
  and a worst-case cost ceiling, and spawns nothing.
- **`fathom smoke`** is the first step that spends. It tests the spawn environment on this
  machine (the login, isolation, the run lock), not the bank, so it belongs just before a paid
  run. One of its checks drives a series engine against a stub `claude` and needs the data
  root's `scenarios/series.toml`, so it fails in a data root without one.
  `--no-engine-boundary` skips that check; pass it unless you have a series arm (authoring
  guide, `arming.md` section 12). The check is then left out, not reported as skipped, so the
  smoke can still end in `SMOKE RESULT: ALL PASS`.
- **`fathom index --write`** re-renders `docs/reports/LEDGER-INDEX.md`, which records each
  ledger's hash and completed trials per arm. Run it after each paid run and commit it with
  the ledger; `fathom reconcile` fails while it is out of date. When the rows a run appended
  to the data root's ledger leave the index stale, its `run summary:` line says so and
  names this command, as `fathom --home ROOT index --write` when the run was given
  `--home`. It says nothing on a dry run, when the run appended no rows, when the index is
  current, when the root keeps no index, or for a `--ledger-dir` side ledger.

## The data root

`fathom init [DIR]` creates:

```
my-evals/
  fathom.toml          # the marker: [data_root] with schema = 1; later, accepted reconcile discrepancies
  tasks/               # banks, one directory per bank
  scenarios/           # arms, one *.toml per arm (a bank's own arms can sit in a subdirectory)
  ledger/              # one append-only <bank>.jsonl per bank; commit it
  docs/reports/        # your write-ups, and the generated LEDGER-INDEX.md
  .gitignore           # .fathom/ (run locks, stop requests, spawn streams) and report/ (scorecards)
  .gitattributes       # * text=auto eol=lf: LF line endings for every text file
```

`DIR` defaults to `--home` if given, else the current directory. It never overwrites an
existing file: a file already there is kept and listed as kept, and an existing `.gitignore`
that lacks `.fathom/` or `report/`, or an existing `.gitattributes` without the LF rule, gets a
note. It refuses an engine checkout or a directory inside one, and an existing `fathom.toml`
that cannot be read, has no `[data_root]` table, or declares a schema other than 1.

The LF pin matters because injected files and mounted plugin trees are hashed by their bytes
into each arm's `config_hash`, which is part of the resume key: a checkout that rewrote line
endings would give those arms new hashes and plan again trials already bought. The ledger index
does not depend on it: it reads CRLF as LF before hashing a ledger. Add a `docs/STATUS.md`
listing the analyses you run.

The marker is `schema = 1` under `[data_root]`, and `schema` must be the integer 1. A marker
without it, or with any other value, is an error wherever fathom meets it, and the search for
a data root stops there instead of walking past it. A later schema means the data root was
written for a newer fathom, and the error asks you to upgrade.

Every command that reads or writes data finds the data root in this order:

1. `fathom --home DIR <command>`;
2. the `FATHOM_HOME` environment variable;
3. the nearest directory at or above the current directory whose `fathom.toml` has a
   `[data_root]` table;
4. otherwise the current directory, with a warning, if it has `tasks/` or `ledger/`; if not,
   the command stops and says how to create or point at a data root.

A `FATHOM_HOME` left set from other work therefore wins over the directory you are in, with no
error when it names another valid data root. Unset it, or set it to the data root you mean;
`fathom run` prints `data root: <path>` before its plan, dry runs included.

`tasks/`, `scenarios/`, `ledger/`, `report/` and `.fathom/` resolve against the data root.
Explicit path options (`--tasks-dir`, `--scenarios-dir`, `--ledger-dir`) resolve against the
current directory, as command-line paths usually do, so from outside the data root give them
as absolute paths. One engine install serves any number of data roots.

Each ledger row records the `engine_version` that wrote it and a `written_at` time. Both are
provenance only: neither is part of the resume key, so upgrading the engine does not re-buy
completed trials.

## Commands

| Command | What it does | Spends |
|---|---|---|
| `fathom init [DIR]` | Create a data root. | nothing |
| `fathom validate <bank>` | Check each task: the fixture fails the verifier, the reference solution passes it, the gate runs, and the paths the gate commands name exist. | nothing |
| `fathom run <bank> --dry-run` | Print the arms, the trials still to buy, and a worst-case USD ceiling. | nothing |
| `fathom smoke` | Prove credential isolation, default-deny, stream parsing, plugin mounting, the run lock and the series-engine boundary on tiny real spawns. `--no-engine-boundary` when the data root has no `scenarios/series.toml`. | a few cents |
| `fathom verify-arming` | Prove each treatment arm's injection reaches a live spawn. `fathom run` does this itself before spending. | a little |
| `fathom run <bank>` | Run the matrix. Resumable; checks the credential, the bank and the arms before the first spawn. | yes |
| `fathom stop <bank>` | Ask the run holding a bank's lock to stop after the trial in flight. | nothing |
| `fathom void <bank> …` | Append a row that excludes one recorded trial; the next resume buys it again. | nothing |
| `fathom report <bank>` | Render `report/scorecard-<bank>.md` from the ledger. | nothing |
| `fathom index [--write]` | Check, or re-render, `docs/reports/LEDGER-INDEX.md`: each ledger's hash and completed trials per arm. | nothing |
| `fathom reconcile` | Check every fact the data root records twice (ledger index, config hashes, arm names). Exit 13 on a disagreement. | nothing |

Cost rails on `fathom run`: `--max-spawn-usd` caps each spawn (default $5), `--max-run-usd`
stops the invocation between trials once it has spent that much, `--limit N` caps new trials,
and `--tasks ID[,ID…]` runs a subset. A bank whose arms sit in a subdirectory needs
`--scenarios-dir`: the run reads `<dir>/*.toml` non-recursively, and without the flag it uses
the arms in `scenarios/`. `fathom <command> --help` lists every flag.

## How it works

```
taskbank → scenario (resolve + config_hash) → Runner (claude-cli adapter) → StrategyExecutor
        → grading (verifier) → append-only ledger → scorecard report
```

- A **bank** holds tasks: a fixture repository, an instruction, and a `verify.py` that scores
  the final workspace as named true/false criteria.
- An **arm** pins one way of attempting a task: model, effort, tool allowlist, injected
  context, settings or plugins, and execution strategy (one session, a session with a gate and
  fix loop, a reprompt control, or a multi-PR series driven by an external engine). Its
  resolved configuration is hashed into `config_hash`, which makes runs resumable and keeps
  changed arms from mixing with old results.
- Each **trial** spawns a headless `claude` CLI in a fresh workspace, with a temporary config
  directory holding only the credential and default-deny permissions. The agent, and the gate
  commands a gated arm runs, get no `FATHOM_*` variable, not the directory fathom was started
  in (`PWD`, `OLDPWD`), and no variable whose value names the data root, so their environment
  does not tell them the arm or where the data root is. The files an arm injects or mounts
  are passed to each spawn as copies of its own, so the command line does not name the data
  root either. An agent that goes looking can still find the data root, through the process
  tree for one; the authoring guide (`arming.md`, section 10) lists these routes and what a
  bank author can do about them.
- **Scoring is blind**: the verifier sees only a copy of the final workspace, and cost data is
  joined after scoring.
- Every result is appended to the **ledger** in your data root. Scorecards are regenerated
  from it and never edited.

## Invariants

Four properties every change must keep. The first three have an ADR under
[`docs/adr/`](docs/adr/).

- **Blindness** (ADR-0003): verifiers see only the final workspace, with arm identity absent
  from their input, argv, environment and working directory (an empty temporary one, not the
  data root), and no variable in their environment names the data root; cost joins after
  scoring.
- **Append-only ledger** (ADR-0002): no code rewrites a ledger line; reports regenerate from
  the ledger; an invalid run is archived, never deleted.
- **Spawn isolation** (ADR-0004): a credential-only temporary `CLAUDE_CONFIG_DIR`, headless
  default-deny permissions, explicit allow and disallow lists, never `bypassPermissions`. The
  spawn environment, and a gate command's, carries no `FATHOM_*` variable, not the launch
  directory (`PWD`, `OLDPWD`), and no variable naming the data root. A trial spawn's command
  line names its own staged copies of the arm's `[context]` and `[plugins]` files, not the
  files in the data root.
- **Standard-library core**: every module under `src/fathom/` and every test imports only the
  standard library.

## Claude Code plugin

The repository is also a Claude Code plugin: the `fathom-eval` skill (which ships the
authoring guide), slash commands for smoke, plan, run, report and reconcile, and a read-only
MCP server (`plan`, `report`, `smoke`).

```sh
claude plugin marketplace add grimaldost/fathom
claude plugin install fathom@fathom
export FATHOM_HOME=/path/to/my-evals
```

The plugin runs the engine it ships, pointed at your data root with `--home`. `FATHOM_HOME`
selects the data root; without it, the plugin walks up from the current directory to the
nearest `fathom.toml` with `[data_root]`. It refuses an unmarked directory, the plugin's own
tree and a directory inside a plugin cache, because a cache refresh would delete the ledger
with it. Details: [`README-plugin.md`](README-plugin.md).

## Documentation

| Document | What it covers |
|---|---|
| [`skills/fathom-eval/reference/authoring.md`](skills/fathom-eval/reference/authoring.md) | Building a bank and its arms, end to end; it continues in `arming.md` and `bank-design.md` beside it. |
| [`examples/`](examples/) | The example data root, explained file by file. |
| [`README-plugin.md`](README-plugin.md) | The plugin, its commands and its MCP server. |
| [`CLAUDE.md`](CLAUDE.md) | Guide for agents working on the engine: architecture, invariants, the data-root contract. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Setup, the gates, hooks, releases. |
| [`docs/README.md`](docs/README.md) | Map of the design specs, ADRs and development method. |

## Repository layout

| Path | What it is |
|---|---|
| `src/fathom/` | The engine: CLI, ledger, bank and scenario loaders, adapter, strategies, grading, report. Standard library only. |
| `tests/` | The test suite, runnable with `uv run pytest` or file by file with plain `python`. |
| `examples/` | The example data root. |
| `docs/` | Specs, ADRs and the development method. |
| `skills/`, `commands/`, `mcp/`, `.claude-plugin/` | The Claude Code plugin. |
| `tools/` | Repository tooling: git hooks, the changelog check, the naive-fix check, the ledger-index shim, the fresh-agent acceptance test. |
| `assets/` | The visual identity; see [`assets/README.md`](assets/README.md). |

## License

[MIT](LICENSE).
