# Authoring a fathom bank

This is the complete guide to building an evaluation with fathom: a data root, a task bank, the
verifier that scores each task, the arms that attempt it, and the commands that check, plan, run
and report it. It assumes nothing beyond a fresh copy of the engine.

The parsers are the source of truth, and everything below is written against them:

| What | Parser |
|---|---|
| `bank.toml`, `task.toml`, `fixtures/` staging | [`src/fathom/taskbank.py`](../../../src/fathom/taskbank.py) |
| scenario (arm) TOML, `config_hash` | [`src/fathom/scenario.py`](../../../src/fathom/scenario.py) |
| the verifier contract and the result view | [`src/fathom/grading/verifier.py`](../../../src/fathom/grading/verifier.py) |
| `fathom validate` | [`src/fathom/validate.py`](../../../src/fathom/validate.py) |
| commands, flags, exit codes, the run loop | [`src/fathom/cli.py`](../../../src/fathom/cli.py) |
| the naive-fix check | [`tools/check_naive_refs.py`](../../../tools/check_naive_refs.py) |

A working example of everything described here is in
[`examples/data-root/`](../../../examples/data-root/), walked through file by file in its
[README](../../../examples/data-root/README.md).

## 1. Terms

- **Data root** — the directory that holds your evaluation data: banks, arms, the ledger and
  your write-ups. Marked by a `fathom.toml` with a `[data_root]` table. It is yours and
  separate from the engine; keep it in its own git repository.
- **Bank** — a set of tasks under `tasks/<bank>/`, versioned as one unit.
- **Task** — a starting repository (`fixtures/`), an instruction, and a verifier (`verify.py`)
  that scores the final state as a set of named true/false criteria.
- **Arm** (scenario) — one way of attempting a task: model, effort, tool allowlist, execution
  strategy, and any treatment (injected context, settings, plugins, environment). One TOML
  file under `scenarios/`.
- **Trial** — one attempt of one task by one arm, identified by its repeat number.
- **Analysis** — the matrix of arms × tasks × repeats run against one bank.
- **Ledger** — `ledger/<bank>.jsonl`, the append-only record of every trial. Committed.
- **Scorecard** — `report/scorecard-<bank>.md`, rendered from the ledger. Regenerable, not
  committed.
- **Hash** — a sha256 fingerprint of some exact bytes: the same bytes always give the same
  hash, and any change to them gives a different one. Some command output calls it a
  **digest**; the two words mean the same thing. fathom uses hashes to notice change without
  keeping copies: `config_hash` identifies an arm (section 11), `inject_sha` an injected
  file's content (section 10), `tree_sha` a mounted plugin directory (section 10),
  `fixture_sha` a task's `fixtures/` tree (section 6), and the ledger index stamps each
  ledger with its hash, taken with CRLF read as LF (section 13).

## 2. Create a data root

Install the engine once, as a command-line tool:

```sh
uv tool install git+https://github.com/grimaldost/fathom@v0.8.0
```

or work from a clone: `uv run --project <clone> fathom …` runs the clone's engine from any
directory, including from inside a data root. Every example below is written as `fathom …`.
Keep the engine's environment outside the data root. fathom withholds the data root from the
environment of the agents, gates and verifiers it starts (sections 7 and 10), but it cannot
withhold the path of its own interpreter, which a verifier and the agent code it runs share.

Create the data root:

```sh
fathom init my-evals        # or `fathom init` for the current directory
```

`fathom init [DIR]` creates the directory if needed, then:

| Path | Purpose |
|---|---|
| `fathom.toml` | The marker: a `[data_root]` table with `schema = 1`, and a commented-out `[[reconcile.known]]` template for the accepted reconcile discrepancies you may declare later (section 13). |
| `.gitignore` | Two entries, each under a comment: `.fathom/` (run locks, stop requests, kept spawn streams) and `report/` (rendered scorecards, which regenerate from the ledger). |
| `.gitattributes` | `* text=auto eol=lf`, which gives every file git sees as text LF line endings on every platform, then the same rule named explicitly for `*.md`, `*.toml`, `*.py`, `*.json` and `*.jsonl`. |
| `tasks/` | Empty. Banks, one directory per bank. |
| `scenarios/` | Empty. Arms, one TOML file per arm. |
| `ledger/` | Empty. One append-only `<bank>.jsonl` per bank. Commit it. |
| `docs/reports/` | Empty. Your write-ups of each analysis, and the generated `LEDGER-INDEX.md`. |

Apart from their comments, the three files it writes are:

```toml
# fathom.toml
[data_root]
schema = 1
```

```gitignore
# .gitignore
.fathom/
report/
```

```gitattributes
# .gitattributes
* text=auto eol=lf
*.md text eol=lf
*.toml text eol=lf
*.py text eol=lf
*.json text eol=lf
*.jsonl text eol=lf
```

`DIR` defaults to the `--home` value if one is given, else the current directory;
`FATHOM_HOME` is not used, and an empty `DIR` or `--home` is an error rather than the current
directory. `fathom init` never overwrites a file that already exists: it lists each path as
`created` or `kept`, so running it again on a data root only adds what is missing. It then
prints a note for each of these: an existing `.gitignore` that does not list `.fathom/` or
`report/`, an existing `.gitattributes` with no `*` rule carrying `eol=lf`, and a directory
inside another data root. Then come the next steps, and last either how commands will find
the new root or, when `FATHOM_HOME` names a different directory, a note that it takes
precedence.

It refuses, before writing anything:

- an engine checkout, or a directory inside one (keep your data outside the engine, where a
  commit to the engine cannot pick it up);
- a path that exists and is not a directory;
- an existing `fathom.toml` that cannot be read (not UTF-8, not valid TOML), that has no
  `[data_root]` table (add the two lines above, then run `fathom init` again), or whose
  `schema` is not 1.

The LF pin matters: injected context and settings files and every file of a mounted plugin are
hashed by their bytes into each arm's `config_hash` (section 11), whatever their extension, so a
checkout that converted them to CRLF would give those arms new hashes and plan again trials
already bought. Ledgers do not depend on the pin: the ledger index reads CRLF as LF before it
hashes a ledger, so a checkout's line endings do not change a ledger's stamp. An existing
`.gitattributes` is left alone; add the line
`* text=auto eol=lf` at its top yourself, unless a `.gitattributes` higher in the repository
already has it.

Then `git init` the directory and commit it.

### The marker and its schema

A directory is a data root when its `fathom.toml` has a `[data_root]` table. `schema` is the
layout version of the data root, and this fathom reads schema 1 only:

- `schema` must be present and be the integer `1`. A table without it, or with a string
  (`schema = "1"`), a float, a boolean or a number below 1, is refused with an error that
  says what to write.
- A later schema (`schema = 2`) was written for a newer fathom; the error asks you to upgrade
  fathom to use that data root.
- A marker fathom does not read is an error wherever it is met: named by `--home` or
  `FATHOM_HOME`, or found on the way up from the current directory. The search stops there
  rather than walking past it to another data root further up, because an engine that read a
  newer layout with older rules would read and write it wrongly.
- A `fathom.toml` without a `[data_root]` table is not a marker; the search walks past it.

### How fathom finds the data root

Every command that reads or writes data resolves one data root, in this order:

1. the global option `fathom --home DIR <command>`;
2. the `FATHOM_HOME` environment variable;
3. the nearest directory at or above the current directory whose `fathom.toml` has a
   `[data_root]` table;
4. otherwise the current directory, with a warning on stderr, but only when it already looks
   like a data root without a marker (it has `tasks/` or `ledger/`). Anywhere else the command
   stops with an error that says how to create a data root (`fathom init`) or point at one
   (`--home`, `FATHOM_HOME`).

A directory named by `--home` or `FATHOM_HOME` must carry the marker, and a relative value is
taken relative to the current directory. An empty `FATHOM_HOME` counts as unset; an empty
`--home` is an error, since that is what a script's unset variable looks like. A `fathom.toml`
that exists but cannot be read (not UTF-8, not valid TOML) stops the search with an error
instead of being passed over. Save it as UTF-8: Windows PowerShell 5.1 writes UTF-16 with `>`
and `Out-File` by default.

**Check `FATHOM_HOME` before working in a new data root.** It comes before the directory
search, so a value left set from other work wins over the directory you are in. When
it names another valid data root, that is not an error: every command reads and writes the
other root without complaint. Look at it (`echo $FATHOM_HOME`; in PowerShell,
`$env:FATHOM_HOME`), then unset it (`unset FATHOM_HOME`; in PowerShell,
`Remove-Item Env:FATHOM_HOME`) or set it to the new root. `fathom init` prints a note when
`FATHOM_HOME` names a different directory. To see which root a command uses, read its output:
`fathom run` prints `data root: <path>` before its plan (dry runs included), and
`fathom reconcile` and `fathom index` name the root they checked.

Default data paths (`tasks/`, `scenarios/`, `ledger/`, `report/`, `docs/reports/`, `.fathom/`)
resolve against that root. Explicit path options — `--tasks-dir`, `--scenarios-dir`,
`--ledger-dir` — keep the usual command-line meaning and resolve against the **current
directory**. From the data root's top directory the two agree. From anywhere else, pass those
options as absolute paths:

```sh
fathom --home ~/my-evals run example --dry-run --scenarios-dir ~/my-evals/scenarios/example
```

Working from the data root's top directory needs none of this: step 3 finds the root, and
relative path options mean what they appear to.

## 3. Bank layout

```
tasks/<bank>/
  bank.toml                 # the manifest (section 4)
  scores.toml               # optional; calibration banks only (section 9)
  <task-id>/
    task.toml               # the task (section 5)
    verify.py               # the blind verifier (section 7)
    fixtures/               # the starting repository (section 6)
    solution/               # optional; a reference solution overlay (section 8)
    refs/naive/             # optional; the naive-fix overlay (section 9)
    series.toml, prompts/   # only for tasks run by a series arm (section 12)
    …                       # anything else the verifier reads from its own directory
```

A task is any subdirectory of the bank that contains a `task.toml`; other subdirectories are
ignored. Arms live apart from the bank, under `scenarios/` (section 10).

The bank itself needs only `bank.toml`. Each task needs:

- **Required:** `task.toml`, and the verifier its `[verify] entry` names (`verify.py` by
  convention). `fixtures/` too, unless the agent is meant to start from an empty repository:
  a missing `fixtures/` gives an empty one.
- **Recommended:** `solution/`. Without it `fathom validate` cannot show that the task can be
  solved (section 8).
- **Optional:** `refs/naive/` with a `[naive]` table (section 9); `series.toml` and
  `prompts/`, only when a series arm runs the task (section 12); any support files the
  verifier reads.

## 4. `bank.toml`

```toml
name = "example"          # required; must equal the bank's directory name
dataset_version = "1"     # required; a string, part of the resume key
holdout = []              # required; an array of task ids, may be empty
```

- **`name`** names the ledger file (`ledger/<name>.jsonl`) and the run lock. `fathom report
  <bank>` and `fathom stop <bank>` take the directory name, so keep the two identical.
- **`dataset_version`** is part of every trial's resume key (section 11). Bump it on any change
  that could change a trial's outcome: a task's instruction, its fixtures, its verifier, its
  `[limits]` or `[gate]`, or adding and removing criteria. Trials recorded under the old version
  stay in the ledger and no longer count as done, so the next run buys the new version fresh.
  Forgetting to bump means a changed task resumes against results measured on the old one.
  Comments and whitespace do not count as changes.
- **`holdout`** lists sealed tasks (ADR-0005). `fathom run` leaves them out unless given
  `--include-holdout`, which marks those trials `holdout` in the ledger; the scorecard reports
  them in a separate section. `--tasks` cannot name a holdout without `--include-holdout`. Once
  spent, a holdout is ordinary development data. Every holdout id must name a task in the bank.

Loading fails on a missing field, a scalar `holdout`, a holdout id that names no task, or two
task directories that declare the same `id`.

## 5. `task.toml`

```toml
id = "add"                                 # required; unique within the bank
instruction = """
Implement add() in calc.py so that it returns the sum of its two arguments.
"""                                        # required; the prompt every arm receives

[limits]                                   # required table (its keys are optional)
max_turns = 10                             # turns per spawn; default 30

[verify]                                   # required table
entry = "verify.py"                        # required; path relative to the task directory
timeout_s = 60                             # optional; bounds the verifier subprocess (default 60)
# hard_criteria = ["correctness"]          # optional; calibration banks only (section 9)

# [gate]                                   # optional; the task's own deterministic check
# run = "python -m unittest -q"            # used by the gated strategies and `fathom validate`

# [naive]                                  # optional; read by tools/check_naive_refs.py (section 9)
# must_pass = ["correctness"]
# must_fail = ["handles_overflow"]
```

| Key | Read by | Notes |
|---|---|---|
| `id` | everything | Keep it equal to the task's directory name. |
| `instruction` | every strategy | The only thing every arm receives. State the requirement completely; do not rely on the verifier's criterion names being visible. |
| `[limits] max_turns` | single-session, gated-*, reprompt | Passed to each spawn as `--max-turns`. A spawn that reaches it is truncated, and the scorecard's Arm Health table flags the arm. Set it from what a pilot actually used. |
| `[limits] trial_timeout_s` | nothing | Accepted and ignored. The spawn timeout is the arm's `[limits] trial_timeout_s` (section 10). |
| `[verify] entry` | run, validate, naive check | Run as `python <entry> <result view>` (section 7). |
| `[verify] timeout_s` | run, validate, naive check | Raise it for a verifier that shells out to a heavy harness (a full test-suite collection, say); a timeout scores the trial as errored. |
| `[verify] hard_criteria` | calibration views | Ignored by other banks. |
| `[gate] run` | gated-session, gated-review, validate | A shell command run in the workspace; exit 0 is green. The gated strategies stop it, with every process still under it, after 120 seconds, a fixed limit with no setting, and count that as red; `fathom validate` allows it 300 seconds. Keep a gate well inside 120 seconds. In a trial, whatever the command creates in the workspace is removed when it exits, so an arm's `[gate] extra` command cannot use it (section 10, "Tools and default-deny"). It runs without any variable that names the data root, so it cannot find its tools through a virtual environment kept there. |
| `[naive]` | `tools/check_naive_refs.py` | Section 9. |
| `[context] size`, `pair` | calibration views | Section 9. |

`[limits]`, `[verify]` and `[gate]` are read as open tables: unknown keys are kept and ignored.

## 6. `fixtures/`

Before each trial fathom copies `fixtures/` into a fresh temporary directory, runs
`git init -b main` there, sets `core.autocrlf=false`, and commits everything as one initial
commit. That directory is the agent's working directory, and its final state is what the
verifier scores. A `.git` directory inside `fixtures/` is skipped; an empty or missing
`fixtures/` gives an empty repository.

- **Keep it self-contained.** Everything the instruction, the `[gate]` command and the verifier
  need must be in the fixture or be reachable from the verifier's own directory. The agent sees
  only the workspace.
- **Fixture integrity.** Before the first spawn fathom fingerprints every task's `fixtures/`
  tree (paths and bytes, ignoring `.git`, `__pycache__` and `*.pyc`). It checks the tree again
  before and after every trial, and stops the matrix if it changed: a trial that wrote into
  the task directory would otherwise become the starting point of every later trial. The
  fingerprint is recorded on each trial row as `fixture_sha`.
- **Names the verifier never sees.** The result view (section 7) drops some names, so do not
  give fixture content these names: at the workspace root, `.git`, `tracker.jsonl`, `outputs`,
  `logs`, `series.toml` and `prompts`; at any depth, `plans`, `journal` and `.remember`, files
  and directories alike. They are process artifacts that some tools write and that would
  identify the arm. The lists are `_EXCLUDED_ROOT_NAMES` and `_SCAFFOLDING_DIR_NAMES` in
  `src/fathom/grading/verifier.py`, and nothing else is dropped: a `.git` below the root, for
  one, is copied. If an arm under test writes a working directory of its own into the
  workspace under any other name (a memory store, say), the result view keeps it, and its
  presence alone can tell a reader which arm ran. Keep such a directory outside the
  workspace, and write the verifier so it does not depend on it.
- **The root `.gitignore`.** A series engine appends a block that starts with the line
  `# PR automation` to the root `.gitignore`, or creates the file. The result view cuts the
  file from that text on and ends it at its last non-blank line with one line break, in every
  arm, and leaves the file out when nothing is left (`_gitignore_for_view`). So a fixture may
  ship a `.gitignore`, but it must not contain that text, and the verifier sees it without
  trailing blank lines.

## 7. The verifier

`verify.py` is the blind acceptance check. It decides what a trial achieved, and it must be
unable to tell which arm produced the result (ADR-0003).

**The contract:**

1. It reads **only** `sys.argv[1]`: the path to the result view, a copy of the final workspace.
2. It prints a JSON object mapping criterion names to booleans, `{"criterion": true, …}`, on
   stdout.
3. It exits `0` if and only if the task's correctness gate holds.
4. It never tries to learn which arm ran. Nothing in argv or the environment carries arm
   identity, and the verifier must not look for it elsewhere (a git log, engine artifacts,
   timing).

**The result view.** fathom copies the workspace into a temporary directory without the
names listed in section 6: `.git`, `tracker.jsonl`, `outputs`, `logs`, `series.toml` and
`prompts` at the root, and `plans`, `journal` and `.remember` at any depth. The root
`.gitignore` loses a series engine's block, as section 6 describes. A fixture file or
directory under one of those names never reaches the verifier, so do not use them for
anything the verifier must read. The copy is deleted after the verifier exits. Scoring a copy means the verifier may modify it freely,
for example to restore the original tests before running them.

**The environment.** The verifier runs as `<fathom's Python> verify.py <result view>`, with an
environment reduced to a fixed list of system variables (`PATH`, `HOME`, `TEMP`, `SYSTEMROOT`,
`PYTHONUTF8` and similar), none of which names the data root (`PATH` loses its entries
there, as it does for a spawn, section 10), and with an empty temporary directory of its own
as the working directory, not the data root; fathom removes that directory afterwards. Two
consequences:

- Import only the standard library, because the interpreter is the one fathom is installed in.
  To exercise a project that has third-party dependencies, shell out to a separate environment
  (for example `uv run` inside the result view) and raise `[verify] timeout_s`.
- Do not rely on the working directory: it is empty, and a relative path finds nothing.
  Build every path from `argv[1]`, or from `Path(__file__).parent` for support files kept
  beside the verifier (an original copy of the tests, reference data). The task directory is
  bank data, not arm identity, so reading it is allowed.

**Run the agent's code in a child process.** The empty working directory removes only the
accidental route into the data root. The verifier's own file is still in it, and so are
`.fathom/streams/`, whose files are named after the arms, the ledger, and every task's
`solution/`. Code that walks up from `__file__` or `sys.argv[0]` finds them all. The
verifier itself must not look (rule 4), but code imported into its process shares its
`__file__`, `sys.argv` and variables, so agent code imported that way can look. Run the
code under test in a child process started in the result view instead, as the example
below does:

```python
subprocess.run([sys.executable, "-c", check], cwd=view, capture_output=True, text=True)
```

The child's working directory is the result view, and its `sys.argv` names no file. To run
the project's tests, start the test runner the same way, with `cwd` set to the result view.
One route stays: the child runs under fathom's interpreter, and when fathom runs from a
virtual environment inside the data root, `sys.executable` lies there. Install fathom
outside the data root (section 2) to close it.

**How the output is read.** The whole of stdout is parsed as JSON first; if that fails, the
last line that parses as a JSON object is used, so output printed earlier (by a debugging
line, or by agent code run without capturing its output) does not spoil the result. Put the
criteria line last.

| Verifier behaviour | Outcome | Effect on the trial |
|---|---|---|
| exit 0, JSON object found | `pass` | completed; criteria recorded |
| nonzero exit, JSON object found | `fail` | completed; criteria recorded |
| crash, timeout, or no JSON object | `error` | errored: not scored, re-run on the next resume |

**How the criteria are scored.** The ledger stores the criteria. The scorecard counts a
completed trial as a pass when **every** criterion is true, and reports each criterion
separately in the Per-Criterion Pass Rates table. The exit code is what `fathom validate`
requires of the reference solution. The simplest consistent design exits 0 exactly when every
criterion is true. If the exit code gates on something narrower (a preservation check that
already holds on the fixture, with the measured behaviour in other criteria), make sure the
reference solution still sets every criterion true.

**Designing criteria.**

- One property per criterion, named for what it checks (`errors_raise`, `no_bare_except`),
  stable across versions of the bank.
- Include at least one criterion the untouched fixture fails; `fathom validate` requires it.
- Separate the easy part of the task from the part that distinguishes a careful attempt, so the
  per-criterion table can show where arms differ (section 9).
- Emit every criterion on every run, true or false; a criterion missing from some trials makes
  the per-criterion table incomparable.

A complete verifier (the one in the example data root):

```python
"""Verifier for the example task: reads only argv[1], the scored result view."""

import json
import subprocess
import sys
from pathlib import Path

# Run in a child process started in the result view, so the agent's code shares neither
# this file's path nor its argv, both of which lie in the data root.
CHECK = "import calc; print(calc.add(2, 3) == 5 and calc.add(-1, 1) == 0)"


def correct(view: Path) -> bool:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", CHECK],
            cwd=view,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False
    lines = proc.stdout.splitlines()
    return proc.returncode == 0 and lines[-1:] == ["True"]


def main() -> int:
    criteria = {"correctness": correct(Path(sys.argv[1]))}
    print(json.dumps(criteria))
    return 0 if criteria["correctness"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

## 8. Reference solutions and `fathom validate`

A reference solution is an overlay: `<task>/solution/` holds only the files a correct attempt
changes or adds, laid out as in the workspace. fathom copies it over a freshly staged fixture
and runs the verifier on the result. It is used only for validation; no arm ever sees it.

`fathom validate <bank> [--tasks-dir DIR] [--scenarios-dir DIR] [--strict]` checks four
properties for each task. It is free: it stages fixtures and runs the verifier and the gate
locally, and spawns nothing. The verifier and the gate run as they do in a trial: the verifier
in its reduced environment and empty working directory (section 7), the gate in the workspace
with the environment a trial gives it (section 10, "Tools and default-deny"). A gate that finds
its tools only through a virtual environment inside the data root therefore fails here, as it
would in a run.

| Property | pass | fail | otherwise |
|---|---|---|---|
| The verifier fails on the unmodified fixture | at least one criterion is false | the verifier errored, emitted no criteria, or every criterion is already true | — |
| The verifier passes on the reference solution | outcome `pass` (exit 0) | any other outcome | `unverifiable` when there is no `solution/` |
| The task gate runs on the fixture | the gate exits 0 | exit 127 or 9009 (the command was not found) | `warn` for any other nonzero exit; `unverifiable` when there is no `[gate] run` |
| The gate commands name paths that exist | every path a gate command names exists | a missing path under `${task_dir}` or an absolute one; a `${NAME}` that is not filled in | `warn` for a missing path relative to the workspace; no line when neither the task nor a gated arm has a gate command |

The first property reads the criteria, not the exit code: it asks whether an arm has something
left to do. A red gate on the fixture is reported as `warn` rather than `fail`, because a task
whose visible tests describe the requested feature starts red on purpose; confirm which case
yours is. `unverifiable` is not a pass. It is reported on its own and blocks only under
`--strict`.

The fourth property reads the task's `[gate] run` and the `[gate] extra` of every arm that runs
it (`gated-session`, `gated-review`): the arms in `scenarios/` or `--scenarios-dir` for `fathom
validate`, and the arms about to run for `fathom run`. A gate command whose script is missing
still runs, finds nothing and counts for nothing, so the gated arm runs as an ungated one; this
check finds that before the spend. Each command is split into words as the shell that runs it
reads them (`/bin/sh`, or `cmd.exe` on Windows). A word is a path when it holds `/` or `\`,
ends in a script suffix such as `.py` or `.sh`, or holds a `${...}`; options, the word after
`-c` or `-m`, the target of an output redirection and URLs are not paths. An arm's
`${task_dir}` and `${workspace}` are filled in for each task as the arm fills them (section 10,
"Treatments"), and a relative path resolves against the staged fixture, which is the gate's
working directory. The check reads the fixture before the verifier or the gate has run on it.

- **fail**: a missing path under `${task_dir}`, or a missing absolute path. The agent cannot
  create either, so the gate could never have run it. Also a `${NAME}` that nothing fills: an
  arm's `[gate] extra` takes `${task_dir}` and `${workspace}` only, and the task's own `[gate]
  run` takes none, so a misspelt `${taskdir}` or a `${task_dir}` in the task's gate fails. To
  use an environment variable, write it the shell's way (`$NAME` or `%NAME%`).
- **warn**: a missing path relative to the workspace, or under `${workspace}`. The task may ask
  the agent to create it, so confirm which, as with a red gate.

The check errs toward missing a broken gate rather than refusing a working one. A word holding a
shell variable (`$NAME`, `%NAME%`), a glob or a leading `~` is left to the shell and not
checked, and a command that changes directory (`cd sub && python run.py`) is still resolved
against the workspace, so such a path can warn but never fails. Two kinds of working gate do
fail it: a command that creates an absolute path and then uses it (create such a file in the
workspace, with a relative path), and, on POSIX, a `${NAME}` that `/bin/sh` would fill (write
it `$NAME`). A gate that passes this check can still be red for other reasons; the third
property and a pilot cover those.

It may also print a `note:` line naming the arms that declare injected context or a tool list
(nearly every arm) and saying that `fathom run` will keep their spawn streams under the data
root's `.fathom/streams/<bank>/`. That concerns the run (section 10, "Streams"), not the bank,
and needs no action.

`fathom validate` exits `0` when nothing blocks and `12` otherwise. `fathom run` applies the
same check (without `--strict`) before it spends, and refuses with exit 12 on a failure;
`--skip-bank-validation` turns that off for a bank you validated in the same session.

## 9. Making a bank discriminate

A bank is only useful if arms can score differently on it. The common failure is a
**ceiling**: every arm passes every criterion, and the analysis reports no difference because
the tasks could not show one. A ceiling costs the full price of the matrix and looks exactly
like a finding that the treatment does not help.

What helps:

- **Criteria that are not all easy.** Pair the criteria a first attempt will meet with at
  least one that only a careful attempt meets: an edge case, a second caller that also needs
  the fix, behaviour that must be preserved. Read the Per-Criterion Pass Rates table, not only
  the headline pass rate.
- **Scale.** Differences between arms tend to come from how much material the agent has to
  work through and from the turn budget, more than from how clever a task is. A small fixture
  can ceiling even with deliberate decoys where a larger one separates the arms.
- **A turn budget from evidence.** Set `max_turns` from what a pilot used. A trial that reaches
  the cap was cut short, and its arm's pass rate is a lower bound.
- **A pilot before the matrix.** `fathom run <bank> --tasks ID[,ID…] --repeats 1` buys a small
  screen. Check that the control arm fails some criterion before paying for repeats.
- **A holdout.** Keep one or more tasks in `holdout` to confirm a result on tasks the bank was
  not tuned against.

### The naive-fix check

`fathom validate` shows that each task leaves work to do and can be solved. It does not show
that any criterion is hard: a bank can pass it and still ceiling because the first fix an agent
tries meets every criterion. `tools/check_naive_refs.py` checks that gap for tasks that opt in.

The check is optional: neither `fathom validate` nor `fathom run` requires it. Skip it only
for a task that exists to demonstrate or test the setup. For any task whose results will
inform a decision, write the naive fix down; it is the cheapest evidence that the task can
separate a careful attempt from a quick one.

A task opts in by describing the fix a first attempt would reach for, in `task.toml`:

```toml
[naive]
must_pass = ["correctness"]         # criteria the naive fix should meet
must_fail = ["handles_overflow"]    # criteria it must NOT meet; the trap
# control = true                    # a control task: may leave must_fail empty (needs must_pass)
```

and shipping that fix as an overlay in `<task>/refs/naive/`, laid out like `solution/`. The
tool copies the overlay over a staged fixture, runs the verifier, and reports for each task:

| Status | Meaning |
|---|---|
| `PASS` | the naive fix meets every `must_pass` criterion and none of the `must_fail` ones |
| `FAIL` | the naive fix meets a `must_fail` criterion (the task is not a trap; rework it before spending), misses a `must_pass` criterion (the overlay is too weak to stand for the easy path), the verifier errored, or `[naive]` names a criterion the verifier does not emit |
| `CONTROL` | a declared control: the obvious fix meets `must_pass` by design; never counted as discriminating |
| `UNVERIFIABLE` | no usable `[naive]` table, or no `refs/naive/` directory; blocks only under `--strict` |

It exits `0` when nothing blocks and `3` otherwise, and spends nothing. The tool is not in the
installed Python package, but it is in the engine repository and so in the installed plugin,
whose directory is a copy of the repository: run it from either with a Python 3.12 interpreter.
From the data root:

```sh
python <engine clone or plugin directory>/tools/check_naive_refs.py <bank> [--tasks-dir tasks] [--strict]
```

`--tasks-dir` defaults to `tasks` under the current directory.

A pass is a statement about consistency: the overlay and its contract are written by the same
author and no agent runs. It bounds one easy path, not every easy path. Report it as "the naive
overlays meet their declared contract", not as "the tasks discriminate". Only the control arm's
measured failures show that.

### What no check covers

No check can tell that tasks are simply too easy for every arm. The turn budget, the scale of
the material and a pilot's results remain the author's judgement.

### Optional: calibration banks

A bank that ships `tasks/<bank>/scores.toml` and `[verify] hard_criteria` on its tasks gets
extra calibration sections on its scorecard (model-tier routing; ADR-0007 to ADR-0009). Other
banks are unaffected.

```toml
# tasks/<bank>/scores.toml
[scores]
add = 18        # 0-100 per task; predicted tier: 0-25 weak, 26-55 mid, 56-100 strong
```

`scores.toml` may also hold one positive control (`[control]` with `task`, `weak_arm`,
`strong_arm`, `alpha`, `min_repeats`) and the routing tables `[reduced]`, `[genre]` and
`[analysis]`. A task's `[context]` table (`size = "small" | "large"`, `pair = "<name>"`)
switches the calibration heading from model tier to context size and groups matched pairs;
only the exact values `small` and `large` are grouped. The calibration views read the bank at
`tasks/<bank>/` in the data root, so a bank kept under another `--tasks-dir` renders without
them.

## 10. Arms (scenario TOML)

An arm is one flat TOML file (no `[scenario]` table around it). `fathom run` reads every
`*.toml` in the scenarios directory, **non-recursively**: `scenarios/` by default, or the
directory given with `--scenarios-dir`. Every arm in that directory runs against every task.
A data root with one bank can keep its arms directly in `scenarios/`, as the example data root
does. To keep one bank's arms apart from another's, give each bank its own subdirectory and
always pass it:

```sh
fathom run example --scenarios-dir scenarios/example
```

Without the flag the run silently uses whatever arms sit in `scenarios/`. The plan prints the
arm names before anything spawns; read them.

Name the control arm `bare`. The report treats `bare` as the anchor for pairwise comparisons
and for the deltas it prints beside series arms.

```toml
name = "nudge"                 # required; the arm's name in the ledger and the scorecard
adapter = "claude-cli"         # required; the only adapter
model = "claude-haiku-4-5"     # required; passed to `claude --model`
strategy = "single-session"    # required; see the strategy table
effort = "low"                 # required; passed to `claude --effort` unchanged
# comparator = "bare"          # optional; buy a cell only after bare completed it ("Comparator")

[tools]
source = "none"                # "none" (default) or "repo" (series arms)
allowed = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)"]
# disallowed = ["WebFetch"]    # optional; refused even when allowed would permit it
# repo = "/abs/path/to/engine" # series arms only (section 12)

[context]                      # optional treatment: text appended to the system prompt
inject = "assets/nudge.md"     # relative to this file

# [settings]                   # optional treatment: a settings.json for the spawn
# inject = "assets/hooks.json"

# [plugins]                    # optional treatment: plugin directories to mount
# mount = ["assets/some-plugin"]

# [env]                        # optional: non-secret environment variables for the spawn
# SOME_MODE = "strict"

# [gate]                       # optional: extra gate commands for the gated strategies
# extra = ["python ${task_dir}/probe.py ${workspace}"]
#                              # a fix spawn is shown this command as written, placeholders
#                              # and all (see "Tools and default-deny")

[limits]
trial_timeout_s = 300          # optional; wall-clock seconds per spawn (default 1800)
```

Only the five keys commented `required` must be set; `comparator` and every table are
optional. The top-level keys sit at the top of the file, before any table. A file that wraps
them in a table has no top-level keys at all:

```toml
# Wrong: under [scenario], `name` is scenario.name, and the file has no top-level `name`.
[scenario]
name = "nudge"
```

What `fathom run` does with a faulty arm file:

- A file that is not valid TOML, or lacks one of the five keys, is skipped with a warning,
  and the run goes on with the other arms. For a missing key the warning quotes only the
  key: `warning: skipping scenario nudge.toml: 'name'`. With no arm left the run stops with
  `no scenarios found`.
- Tables and keys the parser does not know are ignored without a warning. A misspelled
  treatment table (`[contxt]` for `[context]`) leaves the arm without its treatment, so it
  runs as the control would, under its own name. Check the spelling of every table.
- An unknown `strategy` stops the run (including `--dry-run`) before anything spawns.
- So does a `comparator` that names no loaded arm, names the arm itself, or forms a cycle
  ("Comparator", below).

### Tools and default-deny

Every spawn runs `claude -p` headless with no permission mode: tools not on the allowlist are
refused, and fathom never passes `bypassPermissions` or `--dangerously-skip-permissions`
(ADR-0004). So:

- **An empty `allowed` list means the agent has no tools.** It cannot read or write the
  workspace; the arm is unarmed and measures nothing. `fathom run` warns about it.
- Entries are Claude Code permission rules: a tool name (`Read`), a tool with a specifier
  (`Bash(python:*)`, `Bash(git diff:*)`), or an MCP server prefix (`mcp__<server>`).
- Give the control and treatment arms the same allowlist unless the tools are the treatment.
- The order of `allowed` enters `config_hash`; reordering it forks the arm's history.

Each spawn also gets a temporary `CLAUDE_CONFIG_DIR` holding only a copy of the credential
file, so no personal instructions, settings, history or plugins reach any arm. The spawn's
environment is the host's with these removed:

- the variables that would send it to another account or backend;
- every `FATHOM_*` variable, and `PWD` and `OLDPWD`, which name the directory fathom was
  started in;
- every variable whose value names a withheld directory. While a command runs, fathom
  withholds the data root, and the directories given with `--tasks-dir`, `--scenarios-dir`
  and `--ledger-dir`, from every child it starts. A variable that names one of them anywhere
  in its value is dropped (`VIRTUAL_ENV`, when fathom runs from a virtual environment inside
  the data root), and `PATH` keeps its other entries but loses those inside one. A directory
  that is, or holds, the home or the temporary directory is not withheld, because every
  process needs those; a data root placed there is not withheld at all.

Those are what would otherwise tell the agent where the data root is (the directory that
holds every task's reference solution and verifier) and which arm it is running: during a
run, `FATHOM_STREAM_TAG` names the bank, the arm, the task and the repeat. The series
engine's process gets the same environment. Nor does the spawn's command line name a file
in the data root: each spawn of a trial gets its own copies of the arm's `[context]` file
and `[plugins]` directories ("Treatments", below). Whatever an arm receives beyond the task,
it declares in its own file.

A gated arm's gate commands run in the workspace with the spawn's environment, less its config
directory: everything listed above is removed from it too, the API credentials included. A gate
that finds its tools only through a virtual environment inside the data root therefore fails;
install the tools a gate needs outside the data root. A gate that runs past its time limit is
stopped together with every process still under it; a process that detached itself from the
gate's process tree can outlive the stop, so a gate should not start background processes.
Each gate command runs on its own, and whatever it creates in the workspace is removed when it
exits, because the workspace is what the verifier scores and a test runner's cache or compiled
bytecode would mark the trial as one a gate ran in. Files that existed before the command stay
as it left them, and so does whatever the agent writes between gates. One gate command
therefore cannot use another's output: an arm's `[gate] extra` probe cannot import something
the task's `[gate] run` built. A gate that needs a build step does it in the same command.

A fix spawn is shown each gate command as written, with `${task_dir}` and `${workspace}` left
as placeholders, and the tail of the failing command's output. In both, every spelling of
the task directory's path is replaced by `${task_dir}`, and then every spelling of a withheld
directory's path, the data root's included, by `<withheld>`. The spellings include a path
relative to the workspace that climbs out of it (`../../…`, which a test runner prints when
it is shorter) and, on Windows, the short (8.3) form. The same masking applies to the
`[gate] extra` output that the trial row records.

That is the extent of what fathom enforces. What remains is up to the bank and arm author:

- **Other paths in gate output.** Masking replaces a withheld directory's own path, not what
  follows it: a gate that prints a file's path in the data root shows it as
  `<withheld>/ledger/example.jsonl`, so the layout below the data root still reaches the fix
  spawn. A relative path is masked only when it is relative to the workspace; one relative
  to another directory (a probe that prints paths relative to its own file, say) passes as
  printed. Write gates that print test results and nothing else.
- **Hook commands and `[env]` values.** A `[settings]` file is copied into the spawn's
  config directory as written, and its hook commands run as written; `[env]` values are set
  as written. fathom rewrites no path in either and masks nothing. The agent can read both:
  its environment names the config directory that holds the settings file, and a running
  hook's command line is in the process table. So keep a hook's script outside the data
  root, or write the hook inline in its command, and write no path in the data root into an
  `[env]` value. `${NAME}` in an `[env]` template reads the reduced environment, so it
  cannot pass on a withheld value.
- **Agent code that a gate runs.** A gate that runs tests or a probe runs code the agent
  wrote, with the gate's whole view: the expanded `${task_dir}` in the command line and in a
  probe's `sys.argv` and `__file__`, and read and write access to everything in the task
  directory, the verifier and `solution/` included (fathom checks only `fixtures/` for changes
  between trials). Masking covers only the output fathom captures. A file that code writes
  into the workspace reaches the next fix or review spawn unmasked. So keep the agent's code
  out of a probe's own process: a probe that has to exercise that code can run it in a child
  process started in the workspace, for example
  `subprocess.run([sys.executable, "-c", code], cwd=workspace)`, so that it does not share
  the probe's `sys.argv`, `__file__` or variables. The task's own `[gate] run` takes no
  placeholder, so its command line names no task directory.
- **The process tree.** A process can read the command lines of other processes that run as
  the same user, and on most systems their working directories and starting environments.
  While a command runs, fathom's working directory is the data root; its command line
  carries the data root's path when `--home` is given (the plugin always gives it), and its
  interpreter's path when fathom runs from a virtual environment inside the data root; and
  its starting environment holds `FATHOM_HOME` if that was set. A gate's command line holds
  the expanded `${task_dir}`. An agent with a tool that runs arbitrary code
  (`Bash(python:*)` is one), and any agent code a gate runs, can read all of these. fathom
  keeps them out of the environment it passes down, not out of the process table.
- **What an agent can reach on disk.** The environment does not name the data root, but an
  agent whose tools can read outside the workspace can still look for it. The allowlist is
  what bounds that: keep file tools and shell commands scoped to the work.

The last three routes need an agent, or its code, that goes looking. fathom closes the routes
that would hand the arm or the data root to an agent that does not ask; it does not contain an
agent that searches for them. The kept streams ("Streams", below) record each spawn's tool
calls, so read them when a result looks better than the arm should manage.

### Strategies

| `strategy` | Spawns per trial | What it does |
|---|---|---|
| `single-session` | 1 | The instruction, once. The usual control. |
| `gated-session` | 1 + up to 2 fixes | After the implementation spawn, runs the task's `[gate] run` and then the arm's `[gate] extra` commands in the workspace (each stopped after a fixed 120 seconds and then counted red; the first red stops the list). What each command creates in the workspace is removed when it exits. On red, a fix spawn receives the gate commands (all of them, joined with `&&`, as written, placeholders not filled in) and the last 3000 characters of the failing command's output, with the task directory's and the data root's paths masked; up to 2 fix rounds. The trial detail records the first and final gate colour. |
| `gated-review` | as gated-session, + 1 or 2 | As gated-session; once the gate is green, a review spawn replies `VERDICT: APPROVE` or `VERDICT: REQUEST_CHANGES`, and a request gets one more fix spawn. |
| `reprompt-session` | 2 | The instruction, then one generic "re-examine and fix" prompt, always. It matches the gated arms' extra spawn without any gate information, so it separates the value of the gate from the value of a second attempt. |
| `series` | many | Drives an external multi-PR engine (section 12). |

The gated strategies need a gate. With neither a task `[gate] run` nor an arm `[gate] extra`,
`gated-session` is a single spawn and `gated-review` is the implementation plus its review
pass. The verifier scores every trial the same way whatever the gate said; a red gate is a
measured result, not an error.

### Treatments

Each treatment table adds one thing to an arm's spawns. Paths are relative to the scenario
file. A declared file or directory that is missing or empty makes `fathom run` warn, because
the arm would run as the control.

During a trial, each spawn is given its own copies of the `[context]` file and of each
`[plugins]` directory, made in a temporary directory just before the spawn and removed after
it, and the command line names the copies, so it names no path in the data root.
`config_hash` is taken over their content, so the copies change no hash. A copy that fails
stops the matrix as an infrastructure error (exit 10) and records nothing for that trial. The
arming check (below) and `fathom smoke` spawn from copies made the same way.

- **`[context] inject`** — a text file appended to the spawn's system prompt with
  `--append-system-prompt-file`. The usual way to measure a skill body, a guideline or a short
  instruction. Its content's sha256 enters `config_hash`.
- **`[settings] inject`** — a JSON file copied as `settings.json` into the spawn's temporary
  config directory, so user-scope hooks (a `PreToolUse` hook, say) are active for the arm.
  Hooks shipped inside a plugin do not fire in headless `claude -p`; user-scope hooks do. Its
  content's sha256 enters `config_hash`. The file is copied as written, and its hook commands
  run as written, so keep the scripts they run outside the data root (see "Tools and
  default-deny" above).
- **`[plugins] mount`** — plugin directories mounted with `--plugin-dir`. Each needs a
  `.claude-plugin/plugin.json` with `name` and `version`. Each mount's `tree_sha`, a hash over
  every file under the directory (tracked by git or not, skipping `.git`, `.venv`,
  `__pycache__`, `.in_use` and `.orphaned_at`), enters `config_hash`, so keep a mounted
  directory free of scratch files. A trial's spawn mounts a copy of the directory without those
  same names, in a directory named `plugin` rather than the mount's own name, which is often
  the arm's; the plugin keeps the name its manifest gives it. A mounted plugin must be
  self-contained: it cannot rely on a `.venv` or `.git` of its own, or on a path that leads out
  of its own directory. Symbolic links are copied as what they point to, and a link that points
  nowhere is left out. What the plugin writes into its own tree is gone when the spawn ends,
  and a large directory is copied again for every spawn. The arming check (below) mounts a
  copy too, so a plugin that does not load from its copy, or whose MCP server does not start
  from it, fails there before any trial is bought.
- **`[env]`** — name/value pairs set in the spawn's environment. Values may use
  `${workspace}` (the trial workspace) and `${NAME}` (the value of `NAME` in the reduced
  environment, empty when unset, so `"/extra/bin:${PATH}"` prepends). The templates, not the
  substituted values, enter `config_hash`. They are applied after the environment is reduced
  (see "Tools and default-deny" above): an arm may set a `FATHOM_*` name of its own as a
  declared treatment, but `${FATHOM_HOME}`, `${PWD}` and any variable withheld because it
  named the data root substitute as empty, so no template can forward the host's value. A
  value is set as written, so write no path in the data root into one. Never put a
  credential here.
- **`[gate] extra`** — shell commands the gated strategies run after the task's own gate, with
  the same red/green meaning. Each command is a template: `${task_dir}` (the task's
  directory, so a probe script can live there) and `${workspace}` (the trial workspace) are
  filled in at run time, each as one quoted shell word with forward slashes. A placeholder
  outside quotes gets double quotes of its own, and one inside quotes is escaped for them, so
  `python ${task_dir}/probe.py` and `python "${task_dir}/probe.py"` run the same probe, and a
  path with a space in it does not split the command. Only the command that runs is
  expanded, and the agent sees it unexpanded: on a red gate the fix spawn is shown the
  command as written, placeholders and all, and the gate's output with every spelling of the
  task directory replaced by `${task_dir}` and of the data root by `<withheld>` (see "Tools
  and default-deny" above). Agent code that the probe runs does see the expanded path. Each
  command runs on its own, and what it creates in the workspace is removed when it exits. The
  template text enters `config_hash`; the content of a script it runs does not, so rename the
  arm when you change such a script. The task's own `[gate] run` takes no placeholders. Other
  strategies ignore `[gate]`.

**Proving a treatment reached the spawn.** Before it spends, `fathom run` makes one cheap real
spawn per arm that declares `[context]`, `[settings]`, `[plugins]` or `[env]`, and checks each
declared treatment live, spawning from per-spawn copies of the `[context]` file and the
`[plugins]` directories as a trial does: the command line passes a context file whose content
matches the declared, non-empty one; the settings file is in the spawn's config with the right
hash, and a `SessionStart` or `UserPromptSubmit` hook it declares actually fired; each mounted
plugin appears in the session's plugin list, and any MCP server it provides is healthy and
permitted by the allowlist; each `[env]` variable is set with no unsubstituted `${…}`. An arm
that cannot be proven armed stops the run with exit 11.
`fathom verify-arming [--scenarios-dir DIR]` runs the same check on its own; it costs a
little. `--skip-arming-check` turns it off for arms verified in the same session.

**Streams.** For any arm with a `[context]` inject or a tool grant, `fathom run` keeps each
spawn's raw stream-json output under the data root's `.fathom/streams/<bank>/`, named after the
trial. They are the only record of what the agent did (which tools it called, whether a skill
activated). A series arm's agents are spawned by its engine, not by fathom (section 12), so
none of their streams is kept. Set `FATHOM_STREAM_DIR` to keep them somewhere else (a relative value is taken
from the directory the command starts in). Streams are written only by `fathom run`.
When `FATHOM_STREAM_DIR` is unset, `fathom validate` prints a `note:` line naming such arms
and the directory `fathom run` will use; it needs no action.

### `[limits]`

`trial_timeout_s` is the wall-clock limit for each spawn, 1800 seconds when unset. For a
series arm it is the limit for the whole engine run, and there is no limit when it is unset,
so always set it there.

### Comparator

A treatment arm is only worth buying where its control was bought too: a cell (one task and
repeat) that the control did not complete leaves the treatment's trial with nothing to be
compared against. An arm declares that dependency with a top-level key, before any table:

```toml
name = "nudge"
comparator = "bare"            # the arm this one is compared against
```

With it, `fathom run`:

- checks the declarations before the plan, `--dry-run` included. A `comparator` must name
  exactly one arm loaded from the same scenarios directory, not the arm itself, and the
  declarations must not form a cycle (`one` on `two` and `two` on `one`). Otherwise the run
  stops with exit 1 before anything spawns. A value that is not a string makes the file
  faulty, so the arm is skipped with a warning like any other faulty file.
- runs the comparator's trials before the dependent's. The arms otherwise keep the order they
  were loaded in (by file name); a comparator moves just ahead of the first arm that depends
  on it, and a set of arms with no `comparator` keeps its order.
- prints one line per dependent arm after the `arms:` line:
  `depends:  nudge on bare (a cell runs only after bare completed the same task and repeat)`.
- buys a cell of the dependent arm only when the comparator, as its file stands now (its
  current `config_hash`), has a completed trial for the same task and repeat at the bank's
  current `dataset_version`, recorded by an earlier run or earlier in this one. An errored
  comparator trial does not count. Otherwise the run prints
  `blocked: nudge/add r0 — comparator bare has no completed trial for this cell; nothing spent`,
  starts no spawn, writes no ledger row and goes on to the next trial. Blocked cells do not
  change the exit code; the run summary counts them (section 13). Run the same command again
  once the comparator's cell has completed, and the blocked cell is bought.

`comparator` is not part of `config_hash` (section 11), so adding it to, or removing it from,
an arm that already has trials keeps that arm's history.

## 11. `config_hash` and the resume key

Each trial is recorded under the key `(bank, dataset_version, task_id, config_hash, repeat)`.
A trial counts as done only when a row with that key has `status == "completed"`. Re-running
the same command therefore buys only what is missing, and a changed arm or task is bought
fresh instead of being mixed with old results.

What an edit does to trials already recorded:

| Edit | Effect |
|---|---|
| In an arm file: its name, model, effort, strategy, `[tools]` (including the order of `allowed`), `trial_timeout_s`; adding or removing a treatment table; an `[env]` template or a `[gate] extra` command | A new `config_hash`. The arm's old trials stop counting as done, and the next run buys the arm again from its first repeat. |
| The content of an injected context or settings file; any file inside a mounted plugin; a new commit in, or a move of, a series engine repository | The same: a new `config_hash`. |
| In a bank: an instruction, a fixture, a verifier, a limit, a gate, a criterion | Nothing automatic. Bump `dataset_version` (section 4) and every trial of the bank is bought again; without the bump, new trials mix with results measured on the old task. |
| Comments or formatting in an arm file; the arm file's name; moving an injected file to another path; the content of a script that a `[gate] extra` command runs; adding, changing or removing `comparator` | Nothing. For the script, rename the arm when you change it, so one history does not hold two versions. |

`config_hash` is the sha256 of a canonical JSON rendering (sorted keys) of the resolved arm.
That exact string, the text that was hashed, is called the **preimage** and is stored on every
row as `config_preimage`. It contains:

| Field | Source |
|---|---|
| `name`, `adapter`, `model`, `strategy`, `effort` | the scenario file |
| `limits.trial_timeout_s` | the scenario file (`null` when unset) |
| `model_id` | `null` for this adapter (the CLI reports the exact model at run time) |
| `tools` | `source`, `repo`, and `allowed` / `disallowed` when non-empty, in file order |
| `tool_repo_sha`, `tool_invocation_cmd` | for `source = "repo"`: the repo's git HEAD and the command that runs it, which contains the repo's absolute path |
| `context.inject_sha`, `settings.inject_sha` | the injected files' content sha256, when declared |
| `plugins` | `name`, `version` and `tree_sha` of each mount, when declared |
| `env` | the `[env]` templates, sorted by name, when declared |
| `gate.extra` | the `[gate] extra` command strings, when declared |

An absent table and an empty one produce the same hash, so adding an optional table to the
schema never changes existing arms.

`comparator` (section 10) is not in the preimage. It orders the run and decides which cells
are bought, and changes nothing an arm measures, so declaring it never re-buys an arm.

**Provenance.** Every row also records `engine_version`, the fathom version that wrote it,
`cli_version`, and `written_at`, the UTC time it was written (ISO 8601, to the second). A run
row also records `scenario`, the name of the arm that ran. None of these is part of
`config_hash`, its preimage or the resume key, so upgrading the engine does not re-buy
completed trials; `written_at` is the one field that differs between two otherwise identical
runs. Rows written before a field existed are never rewritten, and read as they always did.

**Keep every arm committed.** `fathom reconcile` holds each completed trial's arm name against
the scenario files in the data root (`scenario-known`) and each row's `config_hash` against the
hash of its own stored preimage, computed again (`config-hash-preimage`). An arm whose file was
never committed cannot be attributed later.

## 12. Series arms

A `series` arm hands the whole task to an external multi-PR engine that decomposes it,
implements each PR with its own agent spawns, gates and integrates them. fathom drives it as a
black box over a narrow contract, documented in
[`docs/specs/2026-07-03-series-engine-contract.md`](../../../docs/specs/2026-07-03-series-engine-contract.md);
[convoy](https://github.com/grimaldost/convoy) is the reference engine.

- The arm sets `strategy = "series"`, `[tools] source = "repo"` and `repo` to a checkout of the
  engine. A relative `repo` resolves against the data root, not the scenario file. The
  engine runs as `uv run --project <repo> convoy run <series.toml>`, with the repository's
  absolute path in that command.
- Each task a series arm runs ships a `series.toml` template and the prompt directory it names
  under `[paths] prompts`. Before each trial fathom copies the prompts outside the workspace,
  rewrites `[paths]` to absolute locations, pins `[governance]` model and effort to the arm's,
  sets a non-bypass permission mode and fixed per-spawn budgets (implementation $20, review $5,
  fix $3, or `--max-spawn-usd` for all three), and strips per-PR model, effort and budget
  overrides.
- The engine spawns its agents itself, so the arm's `[tools] allowed`, `[context]`,
  `[settings]`, `[plugins]` and `[env]` do not reach those spawns; the template's
  `[governance.tools]` sets their tools.
- The engine also runs the template's `[[checks]]` itself. fathom removes what a gated arm's
  gate commands create in the workspace, but nothing the engine's checks leave there, so a
  test runner's cache or compiled bytecode they write reaches the result view and can tell a
  series trial apart from the others. Write checks that create nothing in the workspace (for
  Python, `python -B`, and `-p no:cacheprovider` for pytest).
- The plan prices a series trial as `PRs × (1 implementation + max_fix_attempts fixes +
  reviews)` spawns, each at its cap, and prints that arithmetic. `max_fix_attempts` comes from
  the template's `[review]` (2 when unset). When `[review] blocking = true` the engine reviews
  each PR once and again after each fix, so `reviews` is `1 + max_fix_attempts`; otherwise it
  is 0. At the default caps a PR under a blocking review with 2 fix attempts is priced at
  $20 + 2 × $3 + 3 × $5 = $41.
- `fathom smoke` checks the engine boundary without spending tokens, by running the data
  root's `scenarios/series.toml` arm against a stub `claude`. Without that file the check fails;
  pass `--no-engine-boundary` when the data root has no series arm.

## 13. Running an analysis

In order, from the data root (or with `--home`):

```sh
fathom validate <bank> [--strict]                       # free: can the bank discriminate?
fathom run <bank> --dry-run [--repeats K] [--scenarios-dir DIR]
                                                        # free: arms, trial count, USD ceiling
fathom smoke [--no-engine-boundary]                     # a few cents: spawn isolation on real spawns
fathom verify-arming [--scenarios-dir DIR]              # optional, a little: are the treatments armed?
fathom run <bank> --repeats K [--scenarios-dir DIR]     # paid; resumable
fathom report <bank>                                    # free: report/scorecard-<bank>.md
fathom index --write                                    # free: re-render the ledger index
fathom reconcile                                        # free: do the derived records agree?
```

Building and checking a bank costs nothing: `validate`, `run --dry-run`, `report`, `index`
and `reconcile` never start a model. `fathom smoke` is the first step that spends, a few
cents. It tests the spawn environment on this machine (the login, isolation, the lock), not
the bank, so it belongs just before paid runs rather than in the authoring loop.

- **Plan first, and read the arm names.** `--dry-run` prints the data root, the arm names
  (each with a config_hash prefix to distinguish forks: arms that differ show different
  prefixes; arms that pool show the same one), the number of trials still to buy (and how
  many are already done), and a ceiling of `trials × the per-spawn cap` (series trials
  priced as in section 12). It spawns nothing and takes no lock. The ceiling is a worst
  case, not an estimate. When the bank's ledger already holds completed trials, an
  `expected:` line follows the `planned:` line with the estimate: the median cost per
  trial for each planned strategy (per strategy and model once a model has 5 trials), its
  trial count, and the planned trials priced at that median. Trials with no run rows, with
  a run whose cost was not reported, errored or voided are left out, a strategy with no
  history is named as unpriced, and an empty ledger prints nothing. It never gates a run:
  the rails stay on observed spend. A bank whose arms sit in a subdirectory needs `--scenarios-dir` on
  every `fathom run` and `fathom verify-arming`. Without it, the command takes every `*.toml`
  directly under `scenarios/` with no warning and runs those arms instead; only when there
  are none there does it stop, with `no scenarios found`.
- **A finished plan prices one more repeat.** When every requested trial is already done,
  the plan prints two lines after `planned:` and before `nothing to do` (or `[dry-run] no
  spawns`), with no new flag. `one more repeat:` gives the ceiling of one more trial per
  arm and task, the number of those trials, and the `--repeats` value that plans them (the
  highest completed repeat index among these cells, plus two). When the cells hold different
  numbers of repeats it says `at least one more repeat`, because that value also fills the
  lagging cells. `completed in the ledger for these arms:` counts every completed trial for
  these arms and tasks at the current dataset version, across all repeats, which is the
  count the scorecard uses. Nothing is printed while any trial is still planned.
- **Smoke before any paid run**, and again when resuming later. It proves on tiny real spawns
  that the credential works, that the temporary config holds only the credential, that a
  disallowed tool is refused, that stream parsing works, that a plugin mount reaches the CLI,
  that the run lock excludes a second run, and (unless skipped) the series engine boundary. It
  ends with `SMOKE RESULT: ALL PASS (n/n checks)`; a skipped check keeps it red.
- **Cost rails on `fathom run`.** `--max-spawn-usd USD` is the cap for each spawn (default
  $5; the older spelling `--max-budget-usd` still works); raising it loosens the only runaway
  guard, and the printed ceiling rises with it. `--max-run-usd USD` stops this invocation
  between trials once it has spent that much (exit 14). `--limit N` caps the number of new
  trials, counted from the start of the plan's order. By default the plan is ordered arm by
  arm, with each comparator ahead of the arms that depend on it (section 10), so `--limit`
  cuts whole arms off the end. With `--interleave` the plan is ordered repeat by repeat
  (repeat, then arm in that same order, then task), so `--limit` keeps whole repeats and
  `--limit` of arms × tasks runs repeat 0 of every arm. The flag changes the order only: the
  same trials are bought and the same resume keys are written. It prints an `order:` line and
  a `first:` line after `arms:`; without it neither is printed.
  `--tasks ID[,ID…]` restricts the run to named tasks, which is how to buy a screen.
- **Before the first spawn** `fathom run` checks that the credential has life left (exit 15),
  that the bank validates (exit 12) and that treatment arms are armed (exit 11); the
  `--skip-credential-check`, `--skip-bank-validation` and `--skip-arming-check` flags turn these
  off one at a time, for a re-run whose checks passed in the same session.
- **One run per bank at a time.** A run holds a lock under `.fathom/`; a second run on the same
  bank waits (`--lock-wait-s SECONDS` gives up with exit 10; `--no-lock` skips the lock, only
  for a run on another credential). `fathom stop <bank>` asks the holder to stop after the
  trial in flight, and the run then exits 16; `--now` also ends its process tree and discards
  that trial.
- **Progress and the closing summary.** A paid run prints one flushed line per trial,
  `trial done: i/N arm/task r<k> <status> [$spent]`, where `i` counts the planned trials
  started, `status` is `completed`, `errored` or `infrastructure`, and the amount is what
  this invocation has spent so far. When the run ends, at any exit once the trial loop
  has begun, it prints one `run summary:` line: the absolute ledger path,
  the trials completed and errored by this invocation, the trials skipped as already done,
  the trials not started, the amount spent this invocation, and the command that resumes
  it. The counts come from the rows this invocation appended, not from the whole ledger. A
  trial stopped by an infrastructure error has no row, so it counts as not started and a
  resume runs it. When an arm declares a `comparator`, a cell it blocks prints a `blocked:`
  line instead of a `trial done:` line, and the summary adds `blocked N (comparator
  incomplete)` after the errored count; without a `comparator` the summary has no such
  field. A dry run, and a plan with nothing to buy, print neither line.
- **Resuming.** Every nonzero exit leaves the ledger as the checkpoint. Run the same command
  again to continue; the `resume:` command in the summary is that command, with the bank,
  `--repeats`, and the path, `--tasks`, `--include-holdout` and cost-rail flags the run was
  given. An authentication or usage-limit failure stops the matrix with exit 10
  and records nothing for that trial.
- **Exit codes of `fathom run`:** 0 done (blocked cells included); 1 usage error (bank not
  loadable, no scenarios, unknown strategy, unknown `--tasks` id, a `comparator` that names
  no loaded arm, the arm itself or a cycle); 10 infrastructure (auth, usage limit, fixture drift,
  lock timeout, an arm's files that could not be copied for a spawn); 11 unarmed arm; 12 bank invalid; 14 run budget reached; 15 credential
  expiring; 16 stopped by `fathom stop`.
- **Removing a bad trial.** The ledger is append-only (ADR-0002): never edit it.
  `fathom void <bank> --scenario ARM --repeat N [--task-id ID] --reason "…" [--evidence "…"]`
  appends a row that excludes one recorded trial from every reader; the next resume buys it
  again. A whole run found invalid is moved to `ledger/archive/` and run again fresh.

After a run:

- Render the scorecard with `fathom report <bank>`.
- Re-render the ledger index with `fathom index --write` and commit it with the ledgers.
  `docs/reports/LEDGER-INDEX.md` stamps each ledger's sha256 and its completed trials per arm,
  so any document quoting a count can be checked against it. Without `--write`,
  `fathom index` only checks: exit 0 when current, 1 when stale, 2 when there is no data root
  to check.
- Run `fathom reconcile`. It compares facts the data root derives twice: the ledger index
  against the ledgers, each row's hash against its preimage, each completed trial's arm
  against the committed scenarios. It exits 13 on a disagreement. A discrepancy you accept (an
  arm whose file was lost, say) is declared in `fathom.toml`:

  ```toml
  [[reconcile.known]]
  check = "scenario-known"
  subject = "example"          # the bank
  key = "nudge-draft"          # the arm
  reason = "Why it is accepted, and where a reader can check."
  ```

  An accepted discrepancy that stops occurring fails the reconcile as a stale exception, so the
  list cannot grow silently.
- Write the result up under `docs/reports/` and list the analysis in `docs/STATUS.md`.
  `fathom report` warns when neither mentions the bank.

## 14. Reading the scorecard

`report/scorecard-<bank>.md` has a section for development tasks and, if any holdout was run,
one for holdout tasks. Each contains:

- **Pass Rates** — per arm: passes (completed trials with every criterion true), completed
  trials, the pass rate, a Wilson 95% interval, and infrastructure errors. Errored trials are
  excluded, neither pass nor fail. The interval pools repeats and tasks, which are correlated,
  so read it as a rough width.
- **Verdicts** — the same numbers in a sentence, with the number of distinct tasks behind them.
- **Per-Criterion Pass Rates** — each criterion's rate per arm. This is where arms usually
  differ; lead with it.
- **Pairwise vs Bare Anchor** — appears only when the ledger holds pairwise grading rows. The
  pairwise judge is not part of `fathom run`, so it is normally absent.
- **Economy** — per arm: total tokens, turns, wall-clock, spawns per trial and estimated USD,
  with min/median/max per trial. Where the ranges overlap, the arms are not separated at this
  number of trials.
- **Arm Health** — appears when trials reached `max_turns`. Such an arm's pass rate is a lower
  bound; raise the budget before comparing it.
- **Efficiency** — per-trial means, quality per 100k tokens, and a Pareto mark: `★` when no
  other arm is at least as good on both quality and tokens and better on one, `★?` when that
  holds on the means but the per-trial token ranges overlap.
- **Calibration** — only for calibration banks (section 9).

With few trials, treat every difference as directional. The scorecard says so beside each
verdict.

## 15. Checklist before the first paid run

- [ ] The data root has `fathom.toml` with `[data_root]` and `schema = 1`, and is a git
      repository.
- [ ] `FATHOM_HOME` is unset or names this data root, and the `data root:` line that
      `fathom run --dry-run` prints is this one (section 2).
- [ ] `bank.toml` `name` equals the bank's directory name; `dataset_version` is set.
- [ ] Every task has an instruction that states the requirement completely.
- [ ] Every verifier reads only `argv[1]`, prints the criteria last, emits every criterion on
      every run, imports only the standard library, and runs the agent's code in a child
      process started in the result view (section 7).
- [ ] No hook script a `[settings]` file runs, and no `[env]` value, names a path in the
      data root (section 10).
- [ ] Every task ships `solution/`, and `fathom validate <bank> --strict` passes (or its
      warnings are understood), with `--scenarios-dir` naming the arms you will run when
      they are not in `scenarios/`, so their `[gate] extra` paths are checked (section 8).
- [ ] Every task whose results will inform a decision declares `[naive]` with `refs/naive/`,
      and the naive-fix check passes. A task kept only to demonstrate or test the setup may
      skip this; nothing enforces it (section 9).
- [ ] The control arm is named `bare` and has the same allowlist as the treatment arms.
- [ ] No arm has an empty `allowed` list, unless it is a series arm.
- [ ] When the data root holds more than one bank, each bank's arms sit in their own
      directory, passed with `--scenarios-dir` (section 10).
- [ ] `fathom run --dry-run` shows the intended arms, trial count and ceiling.
- [ ] `fathom smoke` passes in this session.
- [ ] A small pilot shows the control arm failing some criterion.
