# Changelog

All notable changes to fathom. Format: Keep a Changelog; versioning: SemVer.
This changelog starts at 0.8.0, the first release of fathom as a standalone engine. Earlier
versions are not part of this repository's history. Tags start at 0.8.0.

## [Unreleased]

### Added

- **Every model a spawn's output names, on its run row.** `RunRecord` gains an additive
  `models_seen` field: each distinct `model` value in the spawn's output, in the order first
  seen, taken from the init event, each assistant message (a subagent's included) and the
  result. `model_id` still holds the init event's model, so a run whose subagent ran on
  another model now records both instead of one. It is provenance only: it does not enter
  `config_hash`, its preimage or the resume key, and it changes no scorecard. Rows written
  before it load with an empty list and are never rewritten; series-strategy runs, which
  are built from the engine's spawn events rather than a CLI stream, carry an empty list.
  Run rows written from now on carry the key, so a reader that checks a row against a fixed
  set of keys sees one more.

- **The authoring guide covers a mounted plugin's MCP servers and an answer key beside the
  verifier.** `arming.md`, section 10, says where a plugin declares its MCP servers (under
  `mcpServers` in `.claude-plugin/plugin.json`, in a `.mcp.json` at the plugin's root, or in
  both, with the manifest's entry used when both name a server), that the init event spells a
  server `plugin:<plugin>:<server>` while its tools are named
  `mcp__plugin_<plugin>_<server>__<tool>`, so an allowlist entry `mcp__<server>` permits none
  of them, and that a server entry Claude Code drops leaves nothing the arming check can see,
  so `claude plugin validate` is the check for it. A `.mcp.json` in the task's fixture is the
  workspace's own and belongs to the task. `bank-design.md`, section 9, shows a `truth.json`
  kept beside `verify.py` for set-equality and byte-identity criteria, outside the workspace
  because only `fixtures/` is staged, and its checklist asks that numeric oracle values be
  computed again against the final instruction text and that criteria score structured
  fields, not free-text heuristics. `tests/test_answer_key.py` holds the engine to the two
  facts the answer key relies on: staging copies only `fixtures/`, and the verifier finds the
  key through its own path.

### Changed

- **The authoring guide is three files, each with a line budget.** The guide, one file of
  1280 lines, now starts at `skills/fathom-eval/reference/authoring.md` (the data root, the
  bank and its tasks, fixtures, the verifier, `fathom validate`, running an analysis and
  reading the scorecard) and continues in `arming.md` (arms, their tools and treatments,
  `config_hash` and the resume key, series arms) and `bank-design.md` (making a bank
  discriminate, the checklist before the first paid run). Sections were moved whole and keep
  their numbers, so a section number names the same text it did before; a citation of a
  section outside `authoring.md` now names its file (`arming.md`, section 10), in the guide,
  the skill, the READMEs, `CLAUDE.md`, ADR-0003, the backlog and the `validate.py`
  docstrings. Each file states a line budget in its header (800, 450 and 175 lines), so an
  addition past it has to displace something, and a test holds each file to its budget and
  checks that every cited section is in the file the citation names. The skill links all
  three files. A citation kept outside this repository, in a data root's notes for example,
  that names `authoring.md` and a section that moved must now name the section's new file;
  the number is unchanged.

### Fixed

- **No crash on a character outside the locale's code page.** On Windows, Python encodes
  output sent to a pipe or a file in the locale's code page (cp1252, for example), so a path,
  task name or reply holding a character outside it ended `fathom` or `fathom smoke` with a
  UnicodeEncodeError. Both now write stdout and stderr as UTF-8 on every platform, replacing
  what cannot be encoded. A program that reads their output through a pipe on Windows and
  decodes it in the locale's code page now misreads each non-ASCII character and must decode
  it as UTF-8. The plugin's MCP server did that; it now reads the engine's output as UTF-8,
  and a test compares what it reads with what the engine wrote.

- **A kept stream is named by when its spawn started.** The file `fathom run` keeps
  for a trial's agent stream (`<tag>--a<attempt>--<ms>.ndjson`) carried the time the stream
  was written, which is the end of the spawn, so the files of a trial's retries and of
  trials that overlapped sorted by their ends. The `<ms>` part is now the wall-clock time
  just before the spawn began. The name keeps its shape, so `fathom report` finds the
  files as before; the adapter takes an optional `wall_clock` for tests. A tool of your own
  that reads `<ms>` as the time a stream ended now reads the time its spawn started.

## [0.9.0] - 2026-10-07

A minor release, pre-1.0: it adds ledger fields, scorecard sections, a fresh-agent acceptance
test and several run and report options, and it tightens three checks, so a data root or
caller that relied on what they used to accept needs a change. The release serves
measurement you can trust and read back: every ledger row says when it was written and every
run row which arm produced it; the scorecard shows how many criteria each arm met and says
when a bank no longer separates the arms; spawns no longer carry the user's own instruction
files from above their workspace (FATH-B83), so an arm is bare when it is meant to be.

What changes behaviour for an existing data root or caller:

- A `task.toml` whose `tags` key is not a table of strings no longer loads: `fathom run` and
  `fathom validate` exit 1, and `fathom report` warns and renders without the bank's task
  metadata.
- `fathom validate` and the check before `fathom run` spends have a fourth property, gate
  commands that name paths that exist; a missing path under `${task_dir}`, a missing absolute
  script and an unfilled `${NAME}` exit 12 before any spend, so a data root whose gates carry
  such a path is refused until it is fixed.
- Spawns get a settings layer that excludes the instruction files above their workspace and
  turn the account's claude.ai connectors off; runs measured on Windows before this change had
  the user's instructions in every arm, so they are not comparable with new runs of the same
  arms. `fathom smoke` gains a live check of it.
- Every scorecard section gains a Hard-Criteria Fraction table and, when every arm passes
  nearly every task, a saturation banner; anything that compares scorecards line by line sees
  them.
- Every ledger row gains `written_at` and run rows gain `scenario`; a byte comparison of
  appended rows across runs must set `written_at` aside. Old rows load unchanged.
- The plan's `arms:` line shows each arm's `config_hash` prefix, and `_is_pass()` is replaced
  by the public `fathom.report.is_pass()`.
- The plugin's `fastmcp` floor moves from 2.0 to 2.11.3.

### Added

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

- **The plan prints the expected spend beside the ceiling.** When the bank's ledger holds
  completed trials, `fathom run --dry-run` (and the live run's plan) prints one more line
  after `planned:`, for example `expected: ~$0.80 for 4 planned trials (median per trial from
  3 completed trials in this ledger: single-session $0.20 n=3); an estimate, not a cap`. A
  trial's cost is the sum of `cost_usd_est` over its run rows; the median is taken per
  strategy, and per strategy and model once that model has at least 5 trials. Trials with no
  run rows, with a run whose `cost_source` is `none` (a missing cost is not free), errored
  trials and voided trials are left out, and a planned strategy with no history is named
  rather than priced. The line is information only: there is no gate, the `planned:` line is
  unchanged, no exit code differs, and an empty ledger prints nothing. The spend rails still
  act on observed spend.

- **A finished plan prices one more repeat.** When every requested trial is already
  completed, `fathom run` (with or without `--dry-run`) prints two lines after `planned:`
  and before `nothing to do` or `[dry-run] no spawns`. `one more repeat:` gives the ceiling
  of one more trial per arm and task, the number of trials, and the `--repeats` value that
  plans them (the highest completed repeat index among those cells, plus two); it reads
  `at least one more repeat` when the cells hold different numbers of repeats.
  `completed in the ledger for these arms:` counts every completed trial for the planned
  arms and tasks at the current dataset version, across all repeats, the count a scorecard
  uses. There is no new flag, and a plan that still has trials to buy prints neither line.

- **A progress line per trial and a closing summary on `fathom run`.** After each trial,
  `fathom run` prints `trial done: i/N arm/task r<k> <status> [$spent]`, flushed so it reaches
  a pipe or a log as it happens; `i` counts the planned trials started, `status` is
  `completed`, `errored` or `infrastructure`, and the amount is this invocation's spend so
  far. Every exit after the trial loop has begun (done, an infrastructure error or fixture
  drift, the run budget, a stop request) then prints one `run summary:` line: the absolute
  ledger path, the trials completed and errored by this invocation, the trials skipped as
  already done, the trials not started, the amount spent this invocation, and a `resume:`
  command. `run_matrix` takes an optional `resume_cmd`; `fathom run` builds it from the bank,
  `--repeats` and the `--tasks-dir`, `--scenarios-dir`, `--ledger-dir`, `--tasks`,
  `--include-holdout`, `--max-spawn-usd` and `--max-run-usd` flags it was given, with
  `--home` first when that was given. A trial stopped by an infrastructure error has no
  ledger row, so it counts as not started. A dry run, a plan with nothing to buy and the gates
  before the first trial print neither line, so their output is unchanged.

- **A dependent arm is never bought against an incomplete comparator.** An arm file may set
  a top-level `comparator = "bare"`. `fathom run` then checks, before the plan and on
  `--dry-run` too, that the comparator names exactly one loaded arm, not the arm itself, with
  no cycle, and exits 1 otherwise. It orders each comparator ahead of the arms that depend on
  it (a set of arms without the key keeps its order and its plan output byte for byte), and
  prints one `depends:  nudge on bare (a cell runs only after bare completed the same task
  and repeat)` line per dependent arm after `arms:`. Before each trial of a dependent arm it
  checks that the comparator has a completed trial for the same task and repeat, in the
  ledger or from this invocation; when it has none, the run prints a flushed `blocked:
  nudge/add r0 — comparator bare has no completed trial for this cell; nothing spent` line,
  starts no spawn, writes no ledger row and goes on. Blocked cells leave the exit code at 0,
  and the run summary counts them as `blocked N (comparator incomplete)`, a field present
  only when an arm declares the key. `comparator` is run-ordering metadata: it enters neither
  `config_hash` nor the preimage, so adding it to an arm that already has trials keeps the
  arm's history.

- **`fathom run --interleave` orders the plan repeat by repeat.** By default the plan is
  ordered arm by arm (each arm's tasks, then its repeats), so a run cut short holds every
  repeat of the first arm and none of the last, and `--limit` cuts whole arms off the end.
  With `--interleave` the plan runs repeat 0 of every arm and task, then repeat 1, and so on,
  with the arms in the order they already run in (each comparator ahead of its dependents).
  `--limit` then counts from the start of that order, so `--limit` of arms x tasks buys
  repeat 0 of every arm, and a run stopped by `--limit`, `fathom stop` or a spend rail has
  still compared the arms. The flag changes the order only: the same trials are bought, and
  the same resume keys are written with and without it. The plan prints `order:    interleaved
  (repeat, then arm, then task); --limit keeps the first N of this order` and a `first:` line
  with the first planned cells; without the flag no new line is printed and the order and
  output are unchanged byte for byte. The resume command at the end of the run summary keeps
  the flag when it was given. `run_matrix` takes `interleave=False`. The `--limit` and
  `--tasks` help and the skill, command and authoring-guide text now say what `--limit` cuts
  with and without the flag. Making repeat-major the default is a separate decision and is not
  made here.

- **`fathom report <bank> --dataset-version V` renders an older `dataset_version`.** The
  scorecard showed only the version of the last trial recorded and warned about the rest, so an
  older task definition's results could not be read back without editing the ledger. With the
  flag, the report keeps that version's rows and names the versions it left out. A version
  other than the current one is written to `report/scorecard-<bank>--<V>.md`, with `V` cleaned
  as a raw-stream tag is (anything but a letter, digit, `-`, `_` or `.` becomes `_`), so it
  never overwrites the current scorecard. That file opens with a line saying it is a historical
  view, which version it shows and which is current, and that its calibration and turn caps
  come from the current `tasks/` tree. A version the ledger holds no trial for raises an error
  naming the versions it does hold, and the command exits 1 and writes nothing. Without the
  flag, or with the current version, the output is byte-identical. `report.render` takes the
  same `dataset_version` argument.

- **`fathom report <bank> --per-trial` prints each trial's economy.** The Economy section sums
  tokens, turns and USD over an arm, so one costly trial could not be told from the rest.
  With the flag, the scorecard is written exactly as before and a markdown table follows on
  stdout, one line per (arm, task, repeat): status, run rows, estimated USD, input and output
  tokens, turns and wall-clock seconds, each summed over the trial's run rows. A `*` after the
  USD marks a trial with a run whose `cost_source` is `none`, whose cost the figure leaves
  out. Trials are keyed by `config_hash`, not by arm name, so two hashes under one name stay
  apart, labelled with a hash prefix. Voids and the `--dataset-version` scope are those of the
  scorecard, and the two flags combine. `report.per_trial_rows` and `report.render_per_trial`
  are the same view as functions.

- **A reference page for the ledger row format: `docs/ledger-contract.md`.** It covers the
  append-only JSONL rows: every record kind (`trial`, `run`, `grading`, `void`), every named
  field with its meaning and stability promise, the resume key, the trial-to-run join, how an
  experiment's cost is summed, which trials enter a pass-rate denominator, the pass rule (via
  `is_pass`), and how voids apply. A field once named is kept, so a reader accepts rows
  written before the field existed.

- **`fathom.report.is_pass()`, the pass rule as a public function.** `None` gives `False`;
  a dict passes when it is non-empty and every value is truthy; any other value passes on
  its truthiness. The docstring states the rule and that it will not change. It replaces
  the private `_is_pass()`, which is gone: code that imported it imports `is_pass` instead.

- **Scorecard saturation banner.** When a section has at least two arms with completed trials
  and every one of them passes at least K of the section's N tasks, a line follows the Pass
  Rates table saying so and pointing at Economy and Efficiency, or at a harder bank. K is
  ceil(0.9 x N), set by the module constant `_SATURATION_SHARE`, and the line prints K and N.
  An arm passes a task when at least half of its completed trials on that task have every
  criterion true; infra and errored trials do not count. With one task (N = 1) the banner
  prints when every arm passes it, so a one-task holdout section that every arm passes now
  carries it, and the golden scorecard gains that one line. A single-arm ledger and a section
  where some arm falls short of K print no banner.

- **Bank-declared task tags, grouped in the scorecard.** A `task.toml` may carry an optional
  `[tags]` table of string values (`size = "small"`, say), parsed into `Task.tags`; a value that
  is not a string, or a `tags` entry that is not a table, fails the load and names the task.
  When any task in a scorecard section declares tags, the section gains a `### By tag: <key>`
  table for each key, after Verdicts: one row per tag value plus `(untagged)`, one column per
  arm, each cell passes/completed trials and the rate. A bank that declares no tags renders the
  same scorecard as before. Tags are task metadata and no scenario field reads them, so they
  never change a `config_hash`; they do not change `dataset_version` either. The authoring
  guide documents the table in sections 5 and 14.

- **MCP calls per trial for arms that mount a plugin.** An arm can mount an MCP server whose
  every call is denied or never made, and its pass rate then describes the arm without its
  treatment. When an arm's trial rows carry a `config_preimage` with a `plugins` key, each
  scorecard section gains a `### Arm Health: MCP calls` table after Arm Health: per arm, the
  completed trials with a kept stream, and per such trial the `mcp__*` calls to a server the
  spawn reported that returned without an error, as min/median/max. Streams are read from
  `FATHOM_STREAM_DIR` when it is set, else from the data root's `.fathom/streams/<bank>/`, and
  matched to a trial by the name the run gave its stream file. An arm with no stream found
  reads `no streams kept`; a count that includes a stream with no closing `result` event is
  marked partial; an arm whose trials with streams made no such call is flagged
  `all calls denied or absent`. Rows with no `config_preimage` are left out, and a note names
  their arms. A cell run more than once sums the streams of every run, since they share a
  name. A ledger with no such arm renders the same scorecard as before. `report.render` takes
  `streams_dir`, and `fathom.streams` gains `read_stream_file` and `stream_completed`.

- **Bank-declared contrasts in the scorecard.** A bank's `bank.toml` may carry an optional
  `[contrasts]` table: `alpha` (default 0.05) and one `[[contrasts.pair]]` per comparison, with
  `treatment`, `control` and an optional `criterion` (default: the all-criteria pass). When it
  does, each scorecard section gains a `### Contrasts` table after Hard-Criteria Fraction, one
  row per pair in p order: each arm's passes over completed trials on the criterion with the
  rate and a Wilson 95% interval, a one-sided Fisher exact p for the treatment passing more
  often than the control (`calibration.fisher_one_sided`), the pair's Holm step-down threshold
  over the section's pairs, and whether it is below. A pair with an arm that has no completed
  trial in the section reads `N/A` and is left out of the family; a pair naming an arm the
  ledger does not hold gets a `Not compared` line. A note under the table says that small N
  makes a contrast directional. An `alpha` outside (0, 1) or a malformed pair warns instead of
  failing the report. `load_bank` ignores the table and nothing hashes `bank.toml`, so
  declaring contrasts changes no trial or resume key, and a bank without them renders the same
  scorecard as before.

- **Worked recipe: A/B a guardrail across model tiers.**
  `skills/fathom-eval/reference/recipe-guardrail-tiers.md`, linked from the skill, walks a copy
  of the example data root through a 2 x 2 design: one scenario file per (arm, model) cell
  under `scenarios/tiers/` (bare and guardrail, on a smaller and a larger tier), the guardrail
  injected from a real file, the comparison declared as `bank.toml` contrasts, a dry run read
  by hash prefix and expected spend, the paid command, blind verification, manipulation checks
  and the order to read the scorecard. A test, `tests/test_recipe_guardrail_tiers.py`, writes
  the recipe's files into a temporary copy and runs each `fathom` line of it (the paid run
  with `--dry-run`), so the recipe cannot drift from the command line.

### Changed

- **The plan's `arms:` line shows each arm's `config_hash` prefix.** `fathom run` (with or
  without `--dry-run`) prints each arm name followed by the first 12 characters of its
  `config_hash` in brackets, for example `bare [0123456789ab]`, so the plan shows which arms
  fork (different prefixes) and which pool (the same prefix). The prefix has the length the
  report's warnings use. Anything that reads the `arms:` line needs the new form.

- **Validation refuses a gate command that names a missing path.** A gate command whose script
  does not exist still runs, finds nothing and counts for nothing, so a gated arm ran as an
  ungated one and nothing said so: validation checked only that a task's own gate could start,
  and an arm's `[gate] extra` not at all. `fathom validate` and the check `fathom run` makes
  before it spends now have a fourth property, `gate commands name paths that exist`. It
  splits the task's `[gate] run` and the `[gate] extra` of every `gated-session` or
  `gated-review` arm into words as the gate's shell reads them, and takes a word as a path when
  it holds `/` or `\`, ends in a script suffix such as `.py` or `.sh`, or holds a `${...}`;
  options, the word after `-c` or `-m`, the target of an output redirection and URLs are not
  paths. An arm's `${task_dir}` and `${workspace}` are filled in for each task as the arm fills
  them, and a relative path resolves against the staged fixture, read before the verifier or
  the gate runs on it. A missing path under `${task_dir}`, a missing absolute path the gate
  runs (a command word, or a word with a script suffix such as `/opt/gates/probe.py`), and a
  `${NAME}` that nothing fills (any placeholder in the task's own gate, or a misspelt
  `${taskdir}` in an extra) fail, so both commands exit 12 before any spend. Any other missing
  absolute word is a warning, because it may be a pattern rather than a path (`grep -q
  "/health" app.py`), and so is a missing path relative to the workspace, because the task may
  ask the agent to create it; warnings block only under `--strict`. A word holding a shell
  variable, a glob, a leading `~` or pattern syntax (`^`, `{`, `}`, `,` or `|`, as in the sed
  address `/start/,/end/p` or an awk program) is not checked, so its errors lean toward missing
  a broken gate rather than failing a working one. The working gates it still fails are a
  command that creates an absolute path and then runs it, a pattern that reads as an absolute
  script path (`grep -q "/app/main.py" log.txt`) and, on POSIX, a `${NAME}` the shell would
  fill (written `$NAME`, it passes). Each finding
  names the word, the command and the arm (for example `arm nudge [gate] extra`), and a
  missing path also the path it resolved to. A bank with no gate command and no gated arm gets
  no new line. `fathom validate` reads the arms in `scenarios/` or `--scenarios-dir`, and
  `fathom run` the arms it is about to run; `validate_bank` takes `scenarios=()`. A data root
  whose arms carry such a path is refused until the path is fixed; `--skip-bank-validation`
  still spends anyway.

- **Every scorecard has a Hard-Criteria Fraction table.** The pass rate counts a trial only
  when every criterion is true, so two arms could tie on it while one met more criteria than
  the other, and `[verify] hard_criteria` was read only for banks that ship `scores.toml`.
  Each section of the scorecard now has a `### Hard-Criteria Fraction` table after
  Per-Criterion Pass Rates: per arm, criteria true over criteria present, summed over its
  completed trials, with infra and errored trials left out. A task that declares
  `[verify] hard_criteria` counts only those; a task that declares none counts every
  criterion its verifier returned. The last column says which applied: `hard_criteria`,
  `all criteria (no hard_criteria declared)` or `mixed`. The figure is a point estimate with
  no interval, because criteria within one trial tend to pass or fail together (ADR-0009).
  The calibration sections are unchanged; anything that compares scorecards line by line
  sees the new table in every section. A bank directory that cannot be loaded warns, and its
  tasks then count every criterion. A historical view (`--dataset-version`) names hard
  criteria among the task metadata it takes from the current `tasks/` tree.

- **A `task.toml` whose `tags` key is not a table of strings no longer loads.** `tags` was
  not read before, so a task could carry, say, `tags = ["a"]` and load. It is now the
  optional `[tags]` table described under Added, and any other shape fails the bank's load
  with the task named: `fathom run` and `fathom validate` exit 1, and `fathom report` warns
  and renders without the bank's task metadata (no tag tables, every criterion counted in the
  Hard-Criteria Fraction, no calibration section for a bank that ships `scores.toml`).
  Rewrite such a value as a table of strings (`[tags]` then `area = "a"`), or rename the key.

### Fixed

- **Spawns no longer read the user's own CLAUDE.md from above their workspace (FATH-B83).**
  Claude Code reads `CLAUDE.md`, `CLAUDE.local.md` and `.claude/CLAUDE.md` in every directory
  above its working directory, whatever `CLAUDE_CONFIG_DIR` says. fathom stages workspaces in
  the temporary directory, which on Windows lies inside the user's profile, so the profile's
  `.claude/CLAUDE.md`, the user's global instructions, reached every trial, arming probe and
  smoke spawn, in every arm. Each spawn now gets a settings layer (`--settings`, in its own
  configuration directory) whose `claudeMdExcludes` lists the instruction files above its
  workspace. The workspace's own files still reach it, and the arm's `settings.json` and
  `config_hash` are unchanged. The account's claude.ai connectors, which reached some spawns
  and not others, are turned off (`ENABLE_CLAUDEAI_MCP_SERVERS=false`). `fathom smoke` gains a
  live check: a spawn must follow a canary `CLAUDE.md` in its workspace and ignore one placed
  in a directory above it. Runs measured on Windows before this change had the user's
  instructions in every arm. Within one run every arm had the same file, but no arm was bare.
  A series arm's engine starts its own spawns, and isolating those is the engine's job.
- **The MCP server's tool results no longer carry a warning about its own environment.** The
  server runs in the temporary environment `uv run --with fastmcp` makes and passed its
  `VIRTUAL_ENV` to the engine it starts, so every `plan`, `report` and `smoke` result's
  `stderr` said that `VIRTUAL_ENV` did not match the plugin's project environment and would be
  ignored. The engine now starts without it.

- **The authoring guide says where the naive-fix check is.** It called
  `tools/check_naive_refs.py` part of the engine repository and asked for an engine clone, so
  an agent working from the installed plugin concluded it could not run the check. The
  plugin's directory is a copy of the repository and ships the tool; the guide now says so.

- **A relative path option that misses now names the data root's path.** `--tasks-dir`,
  `--scenarios-dir` and `--ledger-dir` are relative to where the command was started. Given
  `--scenarios-dir scenarios` from outside the data root, the command said only that no
  scenarios were found in a directory that did not exist. When the path is missing under the
  working directory but present under the data root, the command now prints a note on stderr
  naming the data-root path, and the `no scenarios found` and `could not load bank` errors add
  `(did you mean <path>?)`. Absolute paths, paths that exist, paths missing in both places and
  omitted options behave as before.

- **The MCP server reports fathom's version, and starts without a banner.** Its handshake
  carried the version of the framework serving it, so a client read the framework's release
  as fathom's, and the framework printed its start-up banner to stderr on every launch. The
  server now reports the version in `.claude-plugin/plugin.json`, which `fathom reconcile`
  keeps equal to `pyproject.toml`'s, and starts with the banner off. Both arguments need
  `fastmcp` 2.11.3 or later, so the floor in the plugin manifest moves from 2.0 to 2.11.3,
  the oldest release that accepts them and installs against current dependencies. CI runs
  the MCP schema tests a second time pinned at the floor; the tests now also check the
  reported version and that stderr carries no banner.

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
