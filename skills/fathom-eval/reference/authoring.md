# Authoring a fathom bank

<!-- Line budget: 800 lines. The guide is three files; an addition that would take this
file past its budget displaces something first (tests/test_authoring_guide.py). -->

This is the complete guide to building an evaluation with fathom: a data root, a task bank, the
verifier that scores each task, the arms that attempt it, and the commands that check, plan, run
and report it. It assumes nothing beyond a fresh copy of the engine.

The guide is in three files. Its sections are numbered across them and keep their numbers
wherever they sit. A bare section number is a section of the file it appears in; a section in
another file is cited with that file's name, as in "`arming.md`, section 10".

| File | Sections |
|---|---|
| `authoring.md` (this file) | 1 to 8: terms, the data root, the bank, its tasks and fixtures, the verifier, reference solutions and `fathom validate`. 13 and 14: running an analysis, reading the scorecard. |
| [`arming.md`](arming.md) | 10 to 12: arms, their tools and treatments, `config_hash` and the resume key, series arms. |
| [`bank-design.md`](bank-design.md) | 9 and 15: making a bank discriminate, the checklist before the first paid run. |

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
  keeping copies: `config_hash` identifies an arm (`arming.md`, section 11), `inject_sha` an
  injected file's content (`arming.md`, section 10), `tree_sha` a mounted plugin directory
  (`arming.md`, section 10), `fixture_sha` a task's `fixtures/` tree (section 6), and the
  ledger index stamps each ledger with its hash, taken with CRLF read as LF (section 13).

## 2. Create a data root

Install the engine once, as a command-line tool:

```sh
uv tool install git+https://github.com/grimaldost/fathom@v0.10.0
```

or work from a clone: `uv run --project <clone> fathom …` runs the clone's engine from any
directory, including from inside a data root. Every example below is written as `fathom …`.
Keep the engine's environment outside the data root. fathom withholds the data root from the
environment of the agents, gates and verifiers it starts (section 7, and `arming.md`,
section 10), but it cannot withhold the path of its own interpreter, which a verifier and the
agent code it runs share.

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
hashed by their bytes into each arm's `config_hash` (`arming.md`, section 11), whatever their
extension, so a checkout that converted them to CRLF would give those arms new hashes and plan
again trials already bought. Ledgers do not depend on the pin: the ledger index reads CRLF as
LF before it hashes a ledger, so a checkout's line endings do not change a ledger's stamp. An
existing `.gitattributes` is left alone; add the line
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
  scores.toml               # optional; calibration banks only (bank-design.md, section 9)
  <task-id>/
    task.toml               # the task (section 5)
    verify.py               # the blind verifier (section 7)
    fixtures/               # the starting repository (section 6)
    solution/               # optional; a reference solution overlay (section 8)
    refs/naive/             # optional; the naive-fix overlay (bank-design.md, section 9)
    series.toml, prompts/   # only for tasks run by a series arm (arming.md, section 12)
    …                       # anything else the verifier reads from its own directory
```

A task is any subdirectory of the bank that contains a `task.toml`; other subdirectories are
ignored. Arms live apart from the bank, under `scenarios/` (`arming.md`, section 10).

The bank itself needs only `bank.toml`. Each task needs:

- **Required:** `task.toml`, and the verifier its `[verify] entry` names (`verify.py` by
  convention). `fixtures/` too, unless the agent is meant to start from an empty repository:
  a missing `fixtures/` gives an empty one.
- **Recommended:** `solution/`. Without it `fathom validate` cannot show that the task can be
  solved (section 8).
- **Optional:** `refs/naive/` with a `[naive]` table (`bank-design.md`, section 9);
  `series.toml` and `prompts/`, only when a series arm runs the task (`arming.md`,
  section 12); any support files the verifier reads.

## 4. `bank.toml`

```toml
name = "example"          # required; must equal the bank's directory name
dataset_version = "1"     # required; a string, part of the resume key
holdout = []              # required; an array of task ids, may be empty

# [contrasts]             # optional; arm comparisons the scorecard tests (section 14)
# alpha = 0.05            # optional; the level Holm's step-down shares among the pairs
#
# [[contrasts.pair]]      # one table per comparison
# treatment = "nudge"     # arm names, as the ledger records them
# control = "bare"
# criterion = "correctness"  # optional; without it the pair compares the all-criteria pass
```

- **`name`** names the ledger file (`ledger/<name>.jsonl`) and the run lock. `fathom report
  <bank>` and `fathom stop <bank>` take the directory name, so keep the two identical.
- **`dataset_version`** is part of every trial's resume key (`arming.md`, section 11). Bump it
  on any change that could change a trial's outcome: a task's instruction, its fixtures, its
  verifier, its `[limits]` or `[gate]`, or adding and removing criteria. Trials recorded under
  the old version stay in the ledger and no longer count as done, so the next run buys the new
  version fresh. Forgetting to bump means a changed task resumes against results measured on
  the old one. Comments and whitespace do not count as changes.
- **`holdout`** lists sealed tasks (ADR-0005). `fathom run` leaves them out unless given
  `--include-holdout`, which marks those trials `holdout` in the ledger; the scorecard reports
  them in a separate section. `--tasks` cannot name a holdout without `--include-holdout`. Once
  spent, a holdout is ordinary development data. Every holdout id must name a task in the bank.
- **`[contrasts]`** (optional) lists the arm comparisons the scorecard tests (section 14). Each
  `[[contrasts.pair]]` names a `treatment` arm and a `control` arm, and optionally a
  `criterion`; without one, the pair compares the all-criteria pass. `alpha` (default 0.05) is
  the level Holm's step-down shares among a section's pairs. Only `fathom report` reads the
  table and nothing hashes `bank.toml`, so adding or changing it changes no trial and needs no
  `dataset_version` bump. An `alpha` that is not a number between 0 and 1 warns and renders no
  contrasts; a pair without a string `treatment` and `control` warns and is skipped.

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
# hard_criteria = ["correctness"]          # optional; section 14, bank-design.md section 9

# [gate]                                   # optional; the task's own deterministic check
# run = "python -m unittest -q"            # used by the gated strategies and `fathom validate`

# [naive]                                  # optional; read by tools/check_naive_refs.py (bank-design.md, section 9)
# must_pass = ["correctness"]
# must_fail = ["handles_overflow"]

# [tags]                                   # optional; your own labels, string values only
# size = "small"                           # the scorecard groups pass rates by each key
# kind = "bugfix"
```

| Key | Read by | Notes |
|---|---|---|
| `id` | everything | Keep it equal to the task's directory name. |
| `instruction` | every strategy | The only thing every arm receives. State the requirement completely; do not rely on the verifier's criterion names being visible. |
| `[limits] max_turns` | single-session, gated-*, reprompt | Passed to each spawn as `--max-turns`. A spawn that reaches it is truncated, and the scorecard's Arm Health table flags the arm. Set it from what a pilot actually used. |
| `[limits] trial_timeout_s` | nothing | Accepted and ignored. The spawn timeout is the arm's `[limits] trial_timeout_s` (`arming.md`, section 10). |
| `[verify] entry` | run, validate, naive check | Run as `python <entry> <result view>` (section 7). |
| `[verify] timeout_s` | run, validate, naive check | Raise it for a verifier that shells out to a heavy harness (a full test-suite collection, say); a timeout scores the trial as errored. |
| `[verify] hard_criteria` | scorecard, calibration views | The criteria the scorecard's Hard-Criteria Fraction counts for this task; a task without it counts every criterion (section 14). The calibration views read only the tasks that declare it (`bank-design.md`, section 9). |
| `[gate] run` | gated-session, gated-review, validate | A shell command run in the workspace; exit 0 is green. The gated strategies stop it, with every process still under it, after 120 seconds, a fixed limit with no setting, and count that as red; `fathom validate` allows it 300 seconds. Keep a gate well inside 120 seconds. In a trial, whatever the command creates in the workspace is removed when it exits, so an arm's `[gate] extra` command cannot use it (`arming.md`, section 10, "Tools and default-deny"). It runs without any variable that names the data root, so it cannot find its tools through a virtual environment kept there. |
| `[naive]` | `tools/check_naive_refs.py` | `bank-design.md`, section 9. |
| `[tags]` | scorecard | Labels you give the task, as `key = "value"` pairs. When any task of a section declares tags, the scorecard adds a "By tag" table for each key (section 14). A value that is not a string, or a `tags` entry that is not a table, fails the bank load and names the task. Tags are not part of any arm, so they never change a `config_hash`; they do not change `dataset_version` either, so bump it yourself if relabelling should start a new history (section 4). |
| `[context] size`, `pair` | calibration views | `bank-design.md`, section 9. |

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
there, as it does for a spawn, `arming.md`, section 10), and with an empty temporary directory
of its own as the working directory, not the data root; fathom removes that directory
afterwards. Two consequences:

- Import only the standard library, because the interpreter is the one fathom is installed in.
  To exercise a project that has third-party dependencies, shell out to a separate environment
  (for example `uv run` inside the result view) and raise `[verify] timeout_s`.
- Do not rely on the working directory: it is empty, and a relative path finds nothing.
  Build every path from `argv[1]`, or from `Path(__file__).parent` for support files kept
  beside the verifier (an original copy of the tests, reference data, an answer key as in
  `bank-design.md`, section 9). The task directory is bank data, not arm identity, so reading
  it is allowed.

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
  per-criterion table can show where arms differ (`bank-design.md`, section 9).
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
with the environment a trial gives it (`arming.md`, section 10, "Tools and default-deny"). A
gate that finds its tools only through a virtual environment inside the data root therefore
fails here, as it would in a run.

| Property | pass | fail | otherwise |
|---|---|---|---|
| The verifier fails on the unmodified fixture | at least one criterion is false | the verifier errored, emitted no criteria, or every criterion is already true | — |
| The verifier passes on the reference solution | outcome `pass` (exit 0) | any other outcome | `unverifiable` when there is no `solution/` |
| The task gate runs on the fixture | the gate exits 0 | exit 127 or 9009 (the command was not found) | `warn` for any other nonzero exit; `unverifiable` when there is no `[gate] run` |
| The gate commands name paths that exist | every path a gate command names exists | a missing path under `${task_dir}`; a missing absolute path the gate runs (a command word, or a word with a script suffix); a `${NAME}` that is not filled in | `warn` for any other missing absolute word and for a missing path relative to the workspace; no line when neither the task nor a gated arm has a gate command |

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
`${task_dir}` and `${workspace}` are filled in for each task as the arm fills them
(`arming.md`, section 10, "Treatments"), and a relative path resolves against the staged
fixture, which is the gate's working directory. The check reads the fixture before the
verifier or the gate has run on it.

- **fail**: a missing path under `${task_dir}`, or a missing absolute path that the gate runs:
  the command word (the first word, or the first after `&&`, `||`, `;`, `|` or `!`), or a word
  with a script suffix such as `.py` or `.sh`. The agent cannot create either, so the gate
  could never have run it. Also a `${NAME}` that nothing fills: an
  arm's `[gate] extra` takes `${task_dir}` and `${workspace}` only, and the task's own `[gate]
  run` takes none, so a misspelt `${taskdir}` or a `${task_dir}` in the task's gate fails. To
  use an environment variable, write it the shell's way (`$NAME` or `%NAME%`).
- **warn**: any other missing absolute word, which may be a pattern rather than a path
  (`grep -q "/health" app.py`, `grep -rn "/usr/local/secret" src`); and a missing path
  relative to the workspace, or under `${workspace}`, which the task may ask the agent to
  create. Confirm which, as with a red gate.

The check errs toward missing a broken gate rather than refusing a working one. A word holding a
shell variable (`$NAME`, `%NAME%`), a glob or a leading `~` is left to the shell and not
checked, and so is a word holding pattern syntax (`^`, `{`, `}`, `,` or `|`), such as the sed
address `/start/,/end/p` or the awk program `'/^def /{n++}'`. A command that changes directory
(`cd sub && python run.py`) is still resolved against the workspace, so such a path can warn
but never fails. Three kinds of working gate do fail it: a command that creates an absolute
path and then runs it (create such a file in the workspace, with a relative path); a pattern
that reads as an absolute script path, such as `grep -q "/app/main.py" log.txt` (drop the
leading `/` or match on less of it); and, on POSIX, a `${NAME}` that `/bin/sh` would fill
(write it `$NAME`). A gate that passes this check can still be red for other reasons; the
third property and a pilot cover those.

It may also print a `note:` line naming the arms that declare injected context or a tool list
(nearly every arm) and saying that `fathom run` will keep their spawn streams under the data
root's `.fathom/streams/<bank>/`. That concerns the run (`arming.md`, section 10, "Streams"),
not the bank, and needs no action.

`fathom validate` exits `0` when nothing blocks and `12` otherwise. `fathom run` applies the
same check (without `--strict`) before it spends, and refuses with exit 12 on a failure;
`--skip-bank-validation` turns that off for a bank you validated in the same session.

## 13. Running an analysis

In order, from the data root (or with `--home`):

```sh
fathom validate <bank> [--strict]                       # free: can the bank discriminate?
fathom run <bank> --dry-run [--repeats K] [--scenarios-dir DIR]
                                                        # free: arms, trial count, USD ceiling
fathom smoke [--no-engine-boundary]                     # a few cents: spawn isolation on real spawns
fathom verify-arming [--scenarios-dir DIR]              # optional, a little: are the treatments armed?
fathom run <bank> --repeats K [--scenarios-dir DIR]     # paid; resumable
fathom report <bank> [--dataset-version V] [--per-trial] # free: report/scorecard-<bank>.md
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
  priced as in `arming.md`, section 12). It spawns nothing and takes no lock. The ceiling is
  a worst case, not an estimate. When the bank's ledger already holds completed trials, an
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
  arm, with each comparator ahead of the arms that depend on it (`arming.md`, section 10),
  so `--limit` cuts whole arms off the end. With `--interleave` the plan is ordered repeat by repeat
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
  field. When the run appended rows to the data root's own ledger and the data root keeps
  a ledger index that those rows left stale, the summary adds `ledger index is now stale:
  refresh it with fathom index --write` (`fathom --home ROOT index --write` when the run
  was given `--home`) before `resume:`, so `resume:` stays the last field. It adds nothing
  when the run appended no rows, when the index is current, when the root keeps no index,
  or when `--ledger-dir` sent the rows to a side ledger. A dry run, and a plan with nothing
  to buy, print neither line.
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

- Render the scorecard with `fathom report <bank>`. It shows the bank's current
  `dataset_version`, the last one a trial was recorded under, and warns which older versions it
  left out. To read an older version, add `--dataset-version V`: the scorecard goes to
  `report/scorecard-<bank>--<V>.md` (any character other than a letter, digit, `-`, `_` or `.`
  becomes `_`), so it never overwrites the current one. The version must be one the ledger
  holds, or the command exits 1 and lists the versions it does. Task metadata (calibration,
  turn caps) is read from the current `tasks/` tree, so an older version's calibration section
  describes today's tasks; the file opens with a note saying so.
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
- **Saturated banner** — a line after the Pass Rates table, printed only when the section has
  at least two arms with completed trials and every one of them passes at least K of the
  section's N tasks, with K = ceil(0.9 x N). An arm passes a task when at least half of its
  completed trials on that task have every criterion true. The line names K and N. It means
  the pass rate cannot separate the arms on this bank: compare them on Economy and Efficiency,
  or make the bank harder (`bank-design.md`, section 9). With one task (N = 1) it prints
  when every arm passes that task, which is often the case in a holdout section.
- **Verdicts** — the same numbers in a sentence, with the number of distinct tasks behind them.
- **By tag: `<key>`** — appears only when a task in the section declares `[tags]` (section 5),
  once per tag key, in key order. One row per tag value, with a final `(untagged)` row for the
  tasks that do not declare that key, and one column per arm showing passes/completed trials
  and the rate, counted as in Pass Rates. A dash means the arm has no completed trial on those
  tasks. It is a point estimate with no interval, and a tag value that covers one task is that
  task's own result, so read small groups as anecdotes.
- **Per-Criterion Pass Rates** — each criterion's rate per arm. This is where arms usually
  differ; lead with it.
- **Hard-Criteria Fraction** — per arm, criteria true over criteria present, summed over its
  completed trials, with infra and errored trials left out. A task that declares
  `[verify] hard_criteria` counts only those; a task that declares none counts every
  criterion its verifier returned. The last column says which: `hard_criteria`,
  `all criteria (no hard_criteria declared)` or `mixed`. Two arms with the same pass rate
  can differ here, since a trial that misses one criterion still counts the ones it met. It
  is a point estimate with no interval: criteria within a trial tend to pass or fail
  together (ADR-0009).
- **Contrasts** — appears only when `bank.toml` declares `[contrasts]` (section 4). One row
  per pair: each arm's passes over completed trials on the pair's criterion (the all-criteria
  pass when it names none; on a criterion, the trials whose verifier returned it), with the
  rate and a Wilson 95% interval; a one-sided Fisher exact p for the treatment passing more
  often than the control; and Holm's step-down over the section's pairs. In ascending p order
  the thresholds are alpha/m, alpha/(m-1), and so on up to alpha, and `Below threshold` reads
  `yes` while a pair's p and every smaller p are at or under their thresholds. Rows are in p
  order. A pair with an arm that has no completed trial in the section shows `N/A` and is left
  out of the family; a pair naming an arm the ledger does not hold gets a `Not compared` line
  instead of a row. Trials pool tasks and repeats, which are correlated, and N per cell is
  small, so read a contrast as directional.
- **Pairwise vs Bare Anchor** — appears only when the ledger holds pairwise grading rows. The
  pairwise judge is not part of `fathom run`, so it is normally absent.
- **Economy** — per arm: total tokens, turns, wall-clock, spawns per trial and estimated USD,
  with min/median/max per trial. Where the ranges overlap, the arms are not separated at this
  number of trials.
- **Arm Health** — appears when trials reached `max_turns`. Such an arm's pass rate is a lower
  bound; raise the budget before comparing it.
- **Arm Health: MCP calls** — appears only when an arm mounts a plugin (`[plugins] mount`,
  recorded in its trial rows' `config_preimage`). One row per such arm: how many of its
  completed trials have a kept stream (`arming.md`, section 10, "Streams"), and per such
  trial the `mcp__*` calls to a server the spawn reported that returned without an error, as
  min/median/max. Streams are read from `FATHOM_STREAM_DIR` when it is set, else from the
  data root's `.fathom/streams/<bank>/`. `no streams kept` means none was found for any of the
  arm's trials: an arm with neither a tool grant nor a `[context]` inject keeps none unless
  `FATHOM_STREAM_DIR` is set. `(k partial)` counts trials with a stream that has no closing
  `result` event (the spawn was cut off); their counts are lower bounds. The flag
  `all calls denied or absent` means every trial with a stream made no such call: the
  plugin's tools were denied or never used, so the arm's numbers describe the arm without its
  treatment. Check the allowlist (`arming.md`, section 10) before reading anything else
  about that arm.
  Trial rows written before fathom recorded `config_preimage` are left out, and a line names
  their arms. A cell run more than once (a resumed error, a voided trial) keeps every run's
  streams under one name, so its count sums them all.
- **Efficiency** — per-trial means, quality per 100k tokens, and a Pareto mark: `★` when no
  other arm is at least as good on both quality and tokens and better on one, `★?` when that
  holds on the means but the per-trial token ranges overlap.
- **Calibration** — only for calibration banks (`bank-design.md`, section 9).

With few trials, treat every difference as directional. The scorecard says so beside each
verdict.

A scorecard written with `--dataset-version` for a version other than the current one opens
with a line naming that version and the current one. Quote it only with that line; its numbers
describe the older task definition, not the bank as it stands.

The Economy section sums an arm over all its trials. For one trial at a time, add
`--per-trial`: the scorecard is written as before, and a table follows on stdout with a line
per (arm, task, repeat) giving its status, run rows, estimated USD, input and output tokens,
turns and wall-clock seconds, each summed over that trial's run rows. A `*` after the USD
means a run of the trial reported no cost (`cost_source` `none`), so the figure leaves it out.
The table keys trials by config hash, not by arm name: when one name carries more than one
hash, each line is labelled `name (hash prefix)` so the two do not pool. The flag combines
with `--dataset-version`. To keep the table, redirect the output of `fathom report`; the
scorecard file holds none of it.
