# CLAUDE.md — fathom engine

fathom measures whether an AI coding tool is worth using: it runs real coding tasks under
different configurations and execution strategies (**arms**), scores each result **blind to
which arm produced it**, and joins quality with cost (tokens, turns, wall-clock, USD) into
scorecards that accumulate over time.

This repository is the **engine**: the package under `src/fathom/`, its command line, and its
Claude Code plugin (`.claude-plugin/`, `commands/`, `skills/`, `mcp/`). It holds no task banks,
arms, ledgers or analysis write-ups. Those belong to a **data root**, a separate directory the
user owns (section "The data-root contract"). The only data here is synthetic: the example
data root under `examples/data-root/` and the fixtures under `tests/fixtures/`.

**To build a bank or arms rather than change the engine**, follow
[`skills/fathom-eval/reference/authoring.md`](skills/fathom-eval/reference/authoring.md) and
work in a data root outside this repository (`fathom init ../my-evals`). The rest of this
file is about developing the engine: the gate rules below, including keeping `fathom smoke`
manual, are for engine changes. Before a paid run on a bank, smoke is required (authoring
guide, section 13).

## Gates

The gate list is in [`CONTRIBUTING.md`](CONTRIBUTING.md#gates), with the reason for each
step. It is the only copy and matches `.github/workflows/ci.yml`; read it there, and change
both together. Every gate is free except `fathom smoke`, which makes tiny real spawns, needs a
working `claude` login and stays manual. Never run a non-dry-run `fathom run` or
`fathom verify-arming` as a check: both spend money.

The two `fathom reconcile` gates are the ones a shell's `FATHOM_HOME` can affect, so both are
written to ignore it: the engine-root run clears it (`FATHOM_HOME= uv run fathom reconcile`;
fathom reads an empty value as unset), and the example run names its root
(`uv run fathom --home examples/data-root reconcile`). `FATHOM_HOME` comes before the working
directory, so a developer who keeps it set for their own data root would otherwise reconcile
that root instead of the engine's version sites. Run any other engine command that should see
the engine checkout, not your data, the same way. The test suite clears the variable itself
(`tests/conftest.py`).

## Standard-library core

Every module under `src/fathom/` and every `tests/test_*.py` imports only the standard
library, so each test file also runs as `python tests/test_<name>.py` without uv. uv manages
development tooling (ruff, pytest, pre-commit) only. A third-party dependency in the core needs
an ADR. The MCP server under `mcp/` is the exception: it uses `fastmcp`, which the plugin
supplies at launch, and its tests run separately.

## Invariants

A change must keep all four. The first three have an ADR under `docs/adr/`; the build spec's
enforcement table (`docs/specs/2026-06-10-fathom-v1-build.md`) says how each is checked.

- **Blindness** (ADR-0003). Nothing a verifier sees identifies the arm, and nothing the agent
  under test is handed tells it the arm or where the data root is (which holds every task's
  reference solution and verifier), since what the agent learns it can write into the
  workspace the verifier scores.
  - *The verifier* (`src/fathom/grading/verifier.py`) receives only the result-view path in
    `argv[1]`, an environment reduced to system variables with the data root withheld, and
    an empty temporary working directory rather than the data root. Judges see A/B-labelled
    outputs only. Cost data joins after scoring.
  - *The environment.* A trial's agent, the series engine and gate commands receive no
    `FATHOM_*` variable, not the launch directory (`PWD`, `OLDPWD`), and no variable whose
    value names the data root. `without_harness_vars` in `src/fathom/adapters/claude_cli.py`
    strips the names and then calls `withhold_hidden_dirs`, which drops any variable naming a
    directory registered with `hidden_from_children` and removes PATH entries inside one;
    `_running_in` in `cli.py` registers the data root and any path option for the length of
    a command. `env_for_agent_code` adds the billing and routing strip; `make_spawn_env`
    builds on that for the adapter and the series engine alike, and gate commands in
    `strategies/gated_session.py` and `validate.py` get it as it is. `FATHOM_HOME`, the
    launch directory and a virtual environment inside the data root can name it;
    `FATHOM_STREAM_TAG` carries the arm's name. A scenario's `[env]` is applied after the
    reduction.
  - *The command line.* A trial's argv names per-spawn copies of the arm's `[context]` and
    `[plugins]` files (`stage_arm_files`, `ClaudeCliRunner(stage_files=True)`), not the
    declared paths. The arming probe (`armingprobe.py`) and `fathom smoke` spawn the same
    way.
  - *Gates.* Gate commands run through `run_shell_bounded`, which stops the shell's process
    tree on a timeout. The fix prompt quotes each gate command as written, placeholders not
    filled in, and the gate's output through `mask_gate_text`: the task directory becomes
    `${task_dir}` and each registered directory `<withheld>`, in every spelling, relative to
    the workspace included. Whatever a gate command creates in the workspace is removed when
    it exits (`_remove_new_entries`), so a test runner's cache does not mark the trial as one
    a gate ran in.
  - *New child processes.* Any new child process that runs code fathom does not control
    starts from `env_for_agent_code`, or at least `without_harness_vars`; the authoring
    guide's section 10 says what is left to the bank author.
  - *Routes that stay open* are documented in the guide, not closed: fathom's own process
    (its working directory is the data root while a command runs, and `--home` puts the path
    on its command line); agent code a gate runs, which sees the expanded `${task_dir}` and
    can write what it finds into the workspace; agent code run inside a verifier's process,
    which can walk up from the verifier's own file (section 7 of the guide asks for a child
    process), and the verifier's interpreter, which lies in the data root when fathom runs
    from a virtual environment there; `[settings]` hook commands and `[env]` values, which
    pass as written; a process a timed-out gate detached, which the stop does not reach; and
    files a series engine's own checks leave in the workspace. The backlog's "Later" group
    (FATH-B70 to FATH-B73) holds the planned fixes.
- **Append-only ledger** (ADR-0002). No code rewrites or deletes a ledger line; reports
  regenerate from the ledger; an invalid run is archived, never deleted. New row fields are
  additive, and readers tolerate rows written before a field existed. The resume key is
  `(bank, dataset_version, task_id, config_hash, repeat)`, and only `status == "completed"`
  counts as done (`src/fathom/ledger.py`).
- **Spawn isolation** (ADR-0004). A credential-only temporary `CLAUDE_CONFIG_DIR`, headless
  default-deny, explicit allow and disallow lists, never `bypassPermissions` or
  `--dangerously-skip-permissions` (`src/fathom/adapters/claude_cli.py`). Every model call goes
  through a `Runner` adapter (ADR-0001); the one sanctioned exception is the series-engine
  subprocess in `src/fathom/strategies/series.py`.
- **Standard-library core**, with `typing.Protocol` at the seams (`Runner`,
  `StrategyExecutor`). A convention rather than a CI gate.

The other ADRs: 0001 (a vendor-neutral `Runner`), 0005 (sealed holdout tasks), 0006 (whole
plugin mounts via `--plugin-dir`), 0007 to 0009 (model-tier calibration design and its
statistic).

## Architecture

```
taskbank → scenario (resolve + config_hash) → Runner (claude-cli adapter) → StrategyExecutor
        → grading (verifier) → append-only ledger → report
```

| Module | Role |
|---|---|
| `cli.py` | Argument parsing, every command, the run loop (`run_matrix`), the plan's cost ceiling. |
| `home.py` | Finding the data root (`--home`, `FATHOM_HOME`, walking up, the working directory) and `fathom init`. Standard library only, and loaded by path by the MCP server. |
| `taskbank.py` | Loading `bank.toml` and `task.toml`; staging `fixtures/` into a git workspace; fixture fingerprints. |
| `scenario.py` | Parsing arm TOML, resolving it, and computing `config_hash` and its preimage. |
| `adapters/` | The `Runner` protocol and the `claude` CLI adapter: isolation (the spawn environment, and the directories withheld from every child), per-spawn copies of an arm's files, command line, stream parsing, retries, classifying auth and usage-limit failures as infrastructure. |
| `strategies/` | `single-session`, `gated-session` / `gated-review`, `reprompt-session`, `series`. The set of names is `KNOWN_STRATEGIES`. |
| `grading/verifier.py` | The result view and the verifier subprocess. `grading/judge.py` is a pairwise judge that `fathom run` does not call. |
| `validate.py` | The bank-validation checks behind `fathom validate` and the pre-spend gate. |
| `arming.py`, `armingprobe.py` | Proving on a live spawn that each declared treatment reached it. |
| `ledger.py`, `ledgerindex.py` | Ledger records and appends; the generated `docs/reports/LEDGER-INDEX.md`. |
| `reconcile.py` | Checks that compare two derivations of one fact, and accepted exceptions. |
| `report.py`, `calibration.py` | The scorecard, and the optional calibration views. |
| `smoke.py`, `canary_plugin/` | The real-spawn smoke gate and the plugin it mounts. |
| `runlock.py` | The per-bank run lock and stop requests. |
| `streams.py` | Reading the CLI's stream-json output after the fact. |

Design detail: `docs/specs/2026-06-10-fathom-v1-design.md` (architecture) and
`docs/specs/2026-06-10-fathom-v1-build.md` (build spec). The series arm's boundary is
`docs/specs/2026-07-03-series-engine-contract.md`. The docs map is `docs/README.md`.

## The authoring guide

[`skills/fathom-eval/reference/authoring.md`](skills/fathom-eval/reference/authoring.md) is the
one guide for building banks and arms, written so an agent with only a fresh copy of this
repository can build a working bank. It ships with the plugin, and `README.md` links to it. It
describes as-built behaviour of `taskbank.py`, `scenario.py`, `grading/verifier.py`,
`validate.py`, `cli.py` and `tools/check_naive_refs.py`. A change to any of those that alters a
field, a default, a flag, an exit code or what enters `config_hash` updates the guide in the
same change. `examples/data-root/` is its worked example; keep the two consistent.

## The data-root contract

- **What a data root is.** A directory whose `fathom.toml` has a `[data_root]` table
  (`schema = 1`), holding `tasks/<bank>/`, `scenarios/*.toml`, `ledger/<bank>.jsonl`,
  `docs/reports/` (with `LEDGER-INDEX.md`), `docs/STATUS.md`, and `.fathom/` (runtime state,
  ignored by git). `fathom.toml` may also hold `[[reconcile.known]]` entries (string fields
  `check`, `subject`, `key`, `reason`). The engine ships no exceptions of its own. A data root
  needs no `pyproject.toml`.
- **The marker's schema.** `schema` is the data root's layout version, and this engine reads
  1 only (`home.SCHEMA`, `home.check_schema`). It must be present and be the integer 1: a
  missing value, a string, a float, a boolean or a number below 1 is refused with what to
  write, and a larger number asks the user to upgrade fathom. The refusal applies wherever a marker is met, including on the
  walk up, which stops there instead of passing to a data root further up. A `fathom.toml`
  without `[data_root]` is not a marker. Raising `SCHEMA` makes the engine refuse every
  existing data root until it is migrated, so it is a breaking change.
- **Finding it.** Every command that reads or writes data resolves one data root
  (`home.py`): `fathom --home DIR`, then `FATHOM_HOME`, then the nearest directory at or above
  the working directory whose `fathom.toml` has `[data_root]`, then the working directory
  itself with a warning when it has `tasks/` or `ledger/` but no marker. A directory named by
  `--home` or `FATHOM_HOME` must carry the marker. Otherwise the command stops with an error
  that names `fathom init`, `--home` and `FATHOM_HOME`.
- **Paths.** Default data paths resolve against the data root. Explicit path options
  (`--tasks-dir`, `--scenarios-dir`, `--ledger-dir`, …) keep their usual meaning, relative to
  the working directory. Running inside the data root behaves as if the root were the working
  directory.
- **`fathom init [DIR]`** (`home.init`, `home.init_problem`, `home.init_notes`) writes
  `fathom.toml` (`[data_root]`, `schema = 1`, and a commented-out `[[reconcile.known]]`
  template), a `.gitignore` (`.fathom/`, `report/`) and a `.gitattributes` whose first rule is
  `* text=auto eol=lf`, followed by explicit LF rules for `*.md`, `*.toml`, `*.py`, `*.json` and
  `*.jsonl`; it creates `tasks/`, `scenarios/`, `ledger/` and `docs/reports/` empty. Injected
  files and mounted plugin trees are hashed by their bytes into `config_hash`, so line endings
  must not change under a checkout. The ledger index does not depend on it: it hashes each
  ledger with CRLF read as LF (`ledgerindex.canonical_bytes`). It never overwrites a file; it
  notes an existing `.gitignore` or `.gitattributes` that lacks those lines. It refuses,
  before writing anything, an engine checkout or a directory inside one, and an existing
  `fathom.toml` that is unreadable, has no `[data_root]`, or has a schema other than 1.
- **Provenance.** Every new ledger row records `engine_version` (from
  `importlib.metadata`) and `written_at` (UTC, set in `append_record`), and a run row records
  `scenario`, the arm's name. None is part of `config_hash`, the preimage or the resume key;
  readers ignore them; old rows are never rewritten. `written_at` is the one field that
  differs between otherwise identical runs, so a comparison of rows across runs sets it aside.
- **The engine checkout is not a data root.** It carries no marker. `fathom reconcile` run at
  the engine root checks the version sites (`pyproject.toml`, `.claude-plugin/plugin.json`, the
  newest `CHANGELOG.md` heading); at a data root that check is skipped. Anywhere else reconcile
  refuses with exit 13 rather than passing with nothing to compare.
- **The plugin.** The MCP server and the slash commands run the engine the plugin ships, from
  the data root directory, as `uv run --no-dev --frozen --project <plugin root> python -m
  fathom --home <data root> …` (`mcp/_resolve.py`, `fathom_command`). `--no-dev` keeps the
  development tools out of the plugin's environment, `--frozen` keeps uv from rewriting the
  shipped lock file, and the module form avoids console-script executables that some
  application-control policies block. `FATHOM_HOME`, or walking up from the working directory,
  selects the data root with the engine's own resolver (`home.resolve`, loaded by path). The
  server also requires the marker (no unmarked fallback) and refuses the plugin's own tree and
  any plugin cache directory (a cache refresh would delete its ledger).
- **The ledger index** (`docs/reports/LEDGER-INDEX.md`) is checked or re-rendered with
  `fathom index [--write]`, or `python -m fathom.ledgerindex [--root DIR] [--write]`: exit 1
  when stale, 2 when there is neither a data root nor an engine checkout to check.
  `tools/ledger_index.py` runs the same module from a checkout without installing it.
- **The smoke canary plugin** ships inside the package (`src/fathom/canary_plugin/`), so an
  installed copy can run `fathom smoke` with nothing else.
- **The example.** `examples/data-root/` is a data root the tests and CI run against. Its
  ledger rows record the hashes the engine computes for its arms; a pre-commit test resolves
  the arms again and compares. Changing an arm's hashed content there, or its ledger,
  requires regenerating both together.

## Conventions

- The engine runs on Windows and POSIX, and CI runs both: build paths with `pathlib`, and
  terminate whole process trees where you spawn.
- This repository is public. Nothing specific to one user's evaluations goes into it: no bank,
  arm or campaign names, no results, trial counts, spend or dates of particular runs, no
  pointers to anyone's reports or status pages, no personal paths or machine names. State a
  design rationale as the rule and its reason. Examples use neutral names (`example`, `add`,
  `bare`, `nudge`).
- Tests use synthetic data only. Never copy a real bank, arm, ledger or report in.
- Never edit a ledger by hand.
- Write in English, in a plain, understated register: conventional names, no rhetorical
  flourish. Commit messages follow conventional-commit subjects and carry no AI-attribution
  trailer; leave GPG or SSH signing as configured.
- `CHANGELOG.md` moves with any change to a harness path (see `CONTRIBUTING.md`).
