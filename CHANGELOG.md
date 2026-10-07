# Changelog

All notable changes to fathom. Format: Keep a Changelog; versioning: SemVer.
This changelog starts at 0.8.0, the first release of fathom as a standalone engine. Earlier
versions are not part of this repository's history. Tags start at 0.8.0.

## [Unreleased]

### Added

- **Write time on every ledger row, and the arm name on run rows.** `append_record` now adds
  `written_at`, the UTC time the row was written (ISO 8601, to the second, the format a void
  row's `voided_at` already uses), beside `engine_version`, unless the record names one.
  `RunRecord` gains an additive `scenario` field, which the run loop fills with the arm's
  name, so a run row says which arm produced it without a join through `config_hash`. Both
  are provenance only: neither enters `config_hash`, its preimage or the resume key, and
  neither changes a scorecard. Rows written before them load as they did, with `scenario`
  empty, and are never rewritten. `written_at` is the one field that differs between two
  otherwise identical runs, so a byte comparison of appended rows across runs must set it
  aside.

- **A fresh-agent acceptance test for the plugin.** `tools/agent_acceptance.py` starts
  headless Claude Code sessions whose prompt is a user's goal in plain words, with no fathom
  command, flag, skill or tool name and no appended system prompt, and checks whether each
  session can use fathom from what the installed plugin shows it: reading an existing data
  root (on a clone of it), building and running a measurement from an empty directory, and
  finding the tool without being told its name. Each session is judged on what it could see
  (the init event), what it did (its tool calls, by fathom surface, counted only by the lines
  fathom printed) and what is true afterwards (the workspace, the calls that reached a
  `claude` stub, the real data root's state with its ignored files, a reconcile the harness
  runs). By default a subject runs under a configuration directory that holds only the
  credential, with the installed plugin loaded from where it is installed and the
  account's claude.ai connectors off, in a workspace whose path says nothing about the test
  and with no instruction file in any directory above it, with this checkout's virtual
  environment, the data root's agent instruction files and the parent session's variables
  withheld; a no-spend scenario's ledgers and a measuring one's spend are watched while it
  runs. The scenarios are data in `tools/agent_acceptance_scenarios.toml`, and
  `docs/agent-acceptance.md` covers the cost, the safety rails and how to read the verdict.
  It is run by hand; the test suite covers it offline and never spawns `claude`.

### Changed

- **The `fathom run --dry-run` plan now shows each arm's config_hash prefix.** The arms line
  prints each arm name with its config_hash's first 12 characters in brackets (e.g., `bare
  [aaaaaaaaaa]`), so the plan can distinguish arms that fork from those that pool: a fork shows
  a different prefix, a pool shows the same one. This prefix matches what the `report` command
  uses in its warnings.

### Fixed

- **A relative path option that misses now names the data root's path.** `--tasks-dir`,
  `--scenarios-dir` and `--ledger-dir` are relative to where the command was started. Given
  `--scenarios-dir scenarios` from outside the data root, the command said only that no
  scenarios were found in a directory that did not exist. When the path is missing under the
  working directory but present under the data root, the command now prints a note on stderr
  naming the data-root path, and the `no scenarios found` and `could not load bank` errors add
  `(did you mean <path>?)`. Absolute paths, paths that exist, paths missing in both places and
  omitted options behave as before.

- **The MCP server's tool results no longer carry a warning about its own environment.** The
  server runs in the temporary environment `uv run --with fastmcp` makes and passed its
  `VIRTUAL_ENV` to the engine it starts, so every `plan`, `report` and `smoke` result's
  `stderr` said that `VIRTUAL_ENV` did not match the plugin's project environment and would be
  ignored. The engine now starts without it.
- **The authoring guide says where the naive-fix check is.** It called
  `tools/check_naive_refs.py` part of the engine repository and asked for an engine clone, so
  an agent working from the installed plugin concluded it could not run the check. The
  plugin's directory is a copy of the repository and ships the tool; the guide now says so.

## [0.8.0] - 2026-09-26

The first release of fathom as a standalone engine: the `fathom` package and command, and the
Claude Code plugin (commands, skill and MCP server). It ships no banks, arms or ledgers. Your
evaluation data lives in a **data root** of your own, a directory that holds `tasks/`,
`scenarios/`, `ledger/` and `docs/reports/` and is marked by a `fathom.toml` with a
`[data_root]` table (`schema = 1`). `examples/data-root/` is a small complete one to copy
from, and `skills/fathom-eval/reference/authoring.md` is the guide to building a bank.

### Getting started

1. **Install the engine:** `uv tool install git+https://github.com/grimaldost/fathom@v0.8.0`,
   or clone the repository and use `uv run fathom`. A data root needs no `pyproject.toml`.
2. **Create a data root:** `fathom init DIR`. It creates only what is missing and never
   overwrites a file.
3. **Point fathom at it:** set `FATHOM_HOME`, pass `fathom --home DIR`, or run commands from
   inside the data root.
4. **Build a bank and its arms** under `tasks/` and `scenarios/`, following the authoring
   guide, then plan with `fathom run <bank> --dry-run` before any paid run.

### How fathom finds the data root

Every command that reads or writes data resolves one data root, in this order:

1. `fathom --home DIR <command>`;
2. the `FATHOM_HOME` environment variable;
3. the nearest directory at or above the working directory whose `fathom.toml` has a
   `[data_root]` table;
4. the working directory, with a warning on stderr, when it has `tasks/` or `ledger/` but no
   marker.

Otherwise the command stops with an error that says how to create a data root
(`fathom init`) or point at one (`--home`, `FATHOM_HOME`). A relative `--home` or
`FATHOM_HOME` is taken relative to the working directory. A directory named by `--home` or
`FATHOM_HOME` must carry the marker; an unmarked one is an error, not a fall-through. A
`fathom.toml` that is not UTF-8 or not valid TOML stops the search instead of being walked
past; a UTF-8 byte-order mark is accepted, and a UTF-16 or UTF-32 file (what Windows
PowerShell 5.1 writes with `>`) is refused by name.

The marker's `schema` is the layout version of the data root, and this release reads schema 1
only. It must be present and be the integer 1: a marker without it, or with a string, a
float, a boolean or a number below 1, is refused with an error that says what to write, and a
later schema asks you to upgrade fathom. The refusal applies wherever a marker is met, so the search
stops at such a marker instead of walking past it to a data root further up.

Default paths are the data root's own. Paths you pass (`--tasks-dir`, `--scenarios-dir`,
`--ledger-dir`, a relative `FATHOM_STREAM_DIR`) are relative to the directory the command was
started in. The command then runs with the data root as its working directory, so hashes,
resume keys, locks, streams and scorecards are the same wherever you start it. `fathom run`
prints a `data root:` line.

### Added

- **`fathom --home DIR`** and **`FATHOM_HOME`** for every data command, and resolution from
  any directory inside a data root.
- **`fathom init [DIR]`** creates a data root. It writes `fathom.toml` (`[data_root]` with
  `schema = 1`, and a commented-out `[[reconcile.known]]` template), a `.gitignore` listing
  `.fathom/` and `report/`, and a `.gitattributes` whose first rule, `* text=auto eol=lf`,
  pins LF line endings for every text file, followed by explicit rules for `*.md`, `*.toml`,
  `*.py`, `*.json` and `*.jsonl`; it creates `tasks/`, `scenarios/`, `ledger/` and
  `docs/reports/`. Injected files and mounted plugin trees are hashed by their bytes into
  `config_hash`, so a checkout that rewrote line endings would give those arms new hashes and
  re-plan trials already run. `DIR` defaults to `--home`, else the working directory;
  `FATHOM_HOME` is not used. It never overwrites a file and lists each path as created or
  kept: a `fathom.toml` without the table, or with a schema other than 1, is refused with what
  to write, and an existing `.gitignore` or `.gitattributes` that lacks the lines above is
  reported. It refuses an engine checkout or a directory inside one, and prints the next
  steps.
- **`fathom index [--write]`** checks the data root's ledger index
  (`docs/reports/LEDGER-INDEX.md`) against its ledgers, or re-renders it.
  `python -m fathom.ledgerindex [--write] [--root DIR]` does the same. Exit 0 when current or
  written, 1 when stale, 2 when there is no data root to check. A stale index is reported by
  kind: a ledger whose digest changed, a ledger with no row, a row with no ledger, no index
  over existing ledgers, or only the rendering. A root with no ledgers and no index is
  current.
- **`fathom reconcile`** checks that the facts a data root derives twice agree, and opens with
  `reconciling the <data root|engine checkout> at <path>`. Accepted discrepancies live in the
  data root's `fathom.toml` as `[[reconcile.known]]` tables with `check`, `subject`, `key` and
  `reason`. The summary counts checks run and skipped:
  `RECONCILE: OK (N check(s) run, N skipped, N disagreement(s), N excused, N stale
  exception(s))`. `version-sites` runs only in an engine checkout and prints `[SKIPPED]` in a
  data root. Exit 13 covers a disagreement, a malformed exception list, an unknown `--check`
  name and a directory that is neither a marked data root nor an engine checkout.
- **`fathom report`** exits 1 with the path it looked for when the bank has no ledger.
- **`fathom smoke`** ships its canary plugin in the package, so an installed engine can run
  it. The engine-boundary check reads the data root's `scenarios/series.toml`; a data root
  without a series arm runs `fathom smoke --no-engine-boundary`, and the other checks run
  either way.
- **Run locks and kept streams** live at absolute paths under the data root's `.fathom/`.
- **`fathom --version`** prints the installed version, or says the package is not installed.
- **`engine_version` on ledger rows**, the installed fathom version (`"unknown"` when the
  package is not installed). It is provenance only: not part of `config_hash`, the config
  preimage or the resume key, and ignored by every reader.
- **The plugin's MCP server and slash commands** run the engine the plugin ships,
  `uv run --no-dev --frozen --project <plugin root> python -m fathom --home <data root> ...`,
  from the data root directory, with the data root found by the same resolver as the command
  line (`FATHOM_HOME`, else walking up from the working directory). `--no-dev` keeps the
  development tools out of the plugin's environment, and `--frozen` uses the shipped lock
  file without rewriting it. They refuse an unmarked root, a plugin cache directory and the
  plugin's own tree.
- **An example data root** under `examples/data-root/`: bank `example`, task `add`, arms
  `bare` and `nudge`, a ledger and its index. Its README lists free commands to run
  against it.

### Changed

- **Scorecards render as in 0.7.x, with one sentence changed.** A calibration scorecard that
  writes a routing substrate now points at the schema's docstring
  (`routing_substrate` in `src/fathom/calibration.py`) instead of a bank README, and names
  the substrate file relative to the data root. Every other line renders as before; tests pin
  the calibration headings.
- **The engine's own gates ignore a developer's `FATHOM_HOME`.** `FATHOM_HOME` comes before
  the working directory, so with it set, `fathom reconcile` at the engine root checked the
  developer's data root instead of the engine's version sites. The engine-root reconcile now
  runs with the variable cleared, and the example data root is checked with
  `fathom --home examples/data-root reconcile`, which takes precedence over it.
  `CONTRIBUTING.md` lists the gates.
- **The result view drops fewer names.** At any depth it now drops only `plans`, `journal`
  and `.remember`, with the engine-output names (`tracker.jsonl`, `outputs`, `logs`,
  `series.toml`, `prompts`) at the workspace root. Earlier versions also dropped three
  further store directory names. A directory that an arm writes into the workspace under any
  other name now reaches the verifier, and its presence alone can tell which arm ran; keep
  such directories out of the workspace (authoring guide, section 6).
- **`fathom validate` prints a note about spawn streams, not a warning.** When
  `FATHOM_STREAM_DIR` is unset and the scenarios directory holds arms that declare a
  `[context]` inject or a tool grant, it used to print a `WARNING` line. It now prints a
  `note:` line that names those arms, says that `fathom run` keeps their streams under the
  data root's `.fathom/streams/<bank>/`, and says that no action is needed.
- **A gate command leaves nothing in the workspace.** The gated strategies run each gate
  command in the workspace the verifier scores, and a test runner's cache or compiled
  bytecode left there marked the trial as one a gate ran in. Whatever a gate command creates
  in the workspace is now removed when that command exits; files that existed before it
  stay as it left them, and so does what the agent writes between gates. One gate command
  can therefore no longer use another's output: an arm's `[gate] extra` probe cannot import
  something the task's `[gate] run` built, and a gate that needs a build does it in the same
  command.
- **`${task_dir}` and `${workspace}` in a `[gate] extra` command are each substituted as one
  shell word.** A placeholder outside quotes gets double quotes of its own, and one inside
  quotes is escaped for them, so a data root or temporary directory whose path holds a space
  no longer splits the command. The command text in `config_hash` is unchanged.
- **Scorecard headings.** The context calibration section is now headed
  `## Context Size Calibration`, and its pair table
  `### Context size: per-pair small→large right-tier shift`; both headings used to join the
  two words with a hyphen. Anything that finds these sections by their heading text needs the
  new spelling.

### Removed

- **The unused routing study module** (`fathom.routing`) and its tests. No command, report or
  gate called it.

### Fixed

- **Spawned agents no longer receive fathom's own variables or its launch directory.** A
  trial's agent inherited fathom's environment: `FATHOM_HOME` told it where the data root was,
  which holds every task's reference solution and verifier, `FATHOM_STREAM_TAG` carried its
  arm's name, and `PWD` and `OLDPWD` could name the data root the command was started in.
  Every variable whose name starts with `FATHOM_` (compared without regard to case), and
  `PWD` and `OLDPWD`, are now removed from each spawn's environment, for the single-session
  adapter and the series engine alike, as the blindness invariant (ADR-0003) requires. A
  scenario's `[env]` table is applied after the strip and may still set such a name as a
  declared treatment; `${FATHOM_HOME}` or `${PWD}` in a template substitutes as empty.
- **Nor any variable that names the data root by its value.** Stripping by name misses a
  variable such as `VIRTUAL_ENV` or `PATH` that holds the data root's path. While a command
  runs, the data root, and the directories given with `--tasks-dir`, `--scenarios-dir` or
  `--ledger-dir`, are withheld from every agent, series engine, gate and verifier fathom
  starts: a variable whose value names one of them is dropped (`VIRTUAL_ENV`, when fathom
  runs from a virtual environment inside the data root), and `PATH` loses its entries inside
  one and keeps the rest. A directory that is, or holds, the home or the temporary directory
  is not withheld, since every process needs those. `${NAME}` in an `[env]` template reads
  the reduced environment, so a withheld value substitutes as empty.
- **Gate commands no longer receive them either.** The gated strategies ran the task's
  `[gate] run` and the arm's `[gate] extra` commands with fathom's whole environment, and a
  gate's output goes back to the agent in the fix prompt, so a gate that printed its
  environment handed the agent the arm's name and paths under the data root. Gate commands
  now run with the environment a spawn gets, less its config directory
  (`env_for_agent_code`): no `FATHOM_*` variable, no `PWD` or `OLDPWD`, no variable that
  names the data root, with `PATH` keeping only its entries outside it, and none of the API
  credential and routing variables a spawn is denied. A gate that found its tools only
  through a virtual environment inside the data root now fails; install what a gate needs
  outside the data root. `fathom validate` runs a task's gate the same way, so it shows such
  a failure before a run does.
- **A gate that runs past its time limit is stopped with every process under it.** The
  timeout stopped only the shell: on Windows the run then waited for the gate's hung
  children, and elsewhere they ran on and could write into the workspace the verifier was
  about to score. The shell's whole process tree is now stopped, in the gated strategies
  (after 120 seconds) and in `fathom validate` (after 300); a process that detached itself
  from that tree is not reached.
- **The spawn's command line no longer names files in the data root.** Each spawn of a trial
  gets its own copies of the arm's `[context]` file and `[plugins]` directories, made in a
  temporary directory before the spawn and removed after it, and the command line names the
  copies. A plugin copy leaves out `.git`, `.venv`, `__pycache__`, `.in_use` and
  `.orphaned_at`, the names `tree_sha` skips, copies symbolic links as what they point to, and
  sits in a directory named `plugin`, so a mount directory named after its arm does not reach
  the agent. `config_hash` and resume keys do not change. A copy that fails stops the matrix
  as an infrastructure error (exit 10). A plugin that relied on a `.venv` or `.git` of its
  own, or on a path leading out of its directory, now behaves differently in a trial, and what
  a plugin writes into its own tree no longer outlasts the spawn.
- **The arming check and `fathom smoke` spawn as a trial does.** The arming probe (the
  pre-flight in `fathom run`, and `fathom verify-arming`) and smoke's injection and
  plugin-mount spawns now pass per-spawn copies of the `[context]` file and the `[plugins]`
  directories, as a trial's spawn does, so a plugin that does not work from its copy fails
  the arming check before any trial is bought. Because the command line names the copy, the
  context check compares the file's content with the declared body instead of comparing
  paths, and a mount is matched by its manifest name, its declared path or its copy's path.
  When a plugin check fails and the mount holds a name the copy leaves out (`.git`, `.venv`,
  `.in_use`, `.orphaned_at`), the failure says so.
- **The fix prompt no longer shows the task directory's path.** A gated arm's fix spawn was
  shown the gate commands with `${task_dir}` replaced by the task directory's absolute path,
  which lies inside the data root, so an agent whose tools could read outside the workspace
  could open the task's verifier and reference solution. The fix prompt now quotes each gate
  command as written, with `${task_dir}` and `${workspace}` left as placeholders, and the
  gate's output, in the fix prompt and in the trial row's `[gate] extra` excerpt, has every
  spelling of the task directory's path replaced by `${task_dir}`, and then every spelling
  of the data root's path, or of a directory given with a path option, replaced by
  `<withheld>`. The spellings include a path relative to the workspace that climbs out of it
  (`../../...`, which pytest prints when it is shorter) and, on Windows, the short (8.3)
  form. The shown commands are masked the same way. What follows a masked directory in a
  path stays (`<withheld>/ledger/...`), and a path relative to another directory is not
  masked; the authoring guide (section 10, "Tools and default-deny") asks gates to print
  results only.
  Agent code that a gate runs still sees the expanded path, and the process tree can name
  the data root; the same section describes both.
- **The verifier no longer runs in the data root.** `verify.py` inherited fathom's working
  directory, which is the data root while a command runs, and the data root's
  `.fathom/streams/` holds files named after the arms. The verifier now starts in an empty
  temporary directory of its own, removed afterwards with the result view. A verifier that
  builds its paths from `argv[1]` or its own file, as the authoring guide asks, is unaffected.
  This removes only the accidental route through the working directory. The verifier's own
  file still lies in the data root, so code that runs in its process can walk up to the
  streams, the ledger and each task's `solution/`. The authoring guide (section 7) now asks
  verifiers to run the agent's code in a child process started in the result view, and the
  example data root's verifier, which the guide shows in full, now does so.
- **A series trial's `.gitignore` no longer tells it apart.** The result view left out a
  root `.gitignore` that held the block a series engine appends (from a `# PR automation`
  line on), so in a series trial the verifier saw no `.gitignore` where every other arm saw
  the fixture's. The view now cuts the block and keeps the fixture's lines, ends the file at
  its last non-blank line with one line break in every arm, and leaves the file out only
  when nothing else is in it.
- **The plan's ceiling for a series trial counts review spawns.** It priced each PR as one
  implementation spawn and `max_fix_attempts` fix spawns, and left out the reviews the engine
  runs under a blocking `[review]` gate, each with its own cap ($5 by default). When the
  template sets `[review] blocking = true`, each PR is now also priced at
  `1 + max_fix_attempts` review spawns, and the plan's arithmetic line names them
  (`N PRs x (1 impl + F fix + R review) spawns`). A non-blocking or absent review adds
  nothing.
- **The plugin's MCP server starts with `uv run --no-project`.** Without it, uv resolved a
  `pyproject.toml` in the directory Claude Code was opened in, usually the user's own project,
  and built that project's environment before starting the server. The server needs only
  `fastmcp`.
