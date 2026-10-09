# Example data root

A complete, minimal fathom data root: one bank (`example`) with one task (`add`), two arms
(`bare` and `nudge`), a ledger with a few trials, the generated ledger index, and a status
page. The ledger rows are synthetic: they were written by the engine's own scenario and
ledger code with made-up usage figures, and nothing was measured. The engine's tests and CI
run against this directory.

The full authoring guide starts at
[`skills/fathom-eval/reference/authoring.md`](../../skills/fathom-eval/reference/authoring.md)
and continues in [`arming.md`](../../skills/fathom-eval/reference/arming.md) and
[`bank-design.md`](../../skills/fathom-eval/reference/bank-design.md). The sections cited
below are its sections, which are numbered across the three files; one outside
`authoring.md` is cited with its file's name.

## Layout

```
data-root/
  fathom.toml                        the data-root marker, and two accepted findings
  .gitignore                         keeps runtime state and rendered scorecards out of git
  .gitattributes                     LF line endings for every text file
  tasks/example/
    bank.toml                        the bank manifest
    add/
      task.toml                      the task: instruction, limits, verifier entry
      fixtures/calc.py               the starting repository
      solution/calc.py               the reference solution overlay
      verify.py                      the blind verifier
  scenarios/
    bare.toml                        the control arm
    nudge.toml                       a treatment arm
    assets/nudge.md                  the text the treatment arm injects
  ledger/example.jsonl               the append-only record of every trial
  docs/reports/LEDGER-INDEX.md       generated stamp of each ledger
  docs/STATUS.md                     the index of analyses
  report/                            rendered scorecards (ignored by .gitignore)
```

## File by file

### `fathom.toml`

The marker that makes this directory a data root: a `[data_root]` table with `schema = 1`,
which must be the integer 1 (a missing or different value is refused). fathom finds a data
root through `--home`, `FATHOM_HOME`, or by walking up from the current directory to the
nearest `fathom.toml` that has this table (authoring guide, section 2).

The file also holds two `[[reconcile.known]]` entries. The ledger contains a trial from an
arm called `nudge-draft` whose scenario file was never committed, so `fathom reconcile`
reports it under the `scenario-known` check. The first entry accepts that discrepancy and
says why. The same trial is the only one in its arm x task cell, one fewer than the bank's
plan declares, so the `replication` check warns about the cell (`short:nudge-draft/add`); the
second entry accepts that warning. If either finding ever stopped occurring, its entry would
fail the reconcile as a stale exception.

### `.gitignore` and `.gitattributes`

The two files `fathom init` writes into every new data root, with the same content. The
`.gitignore` lists `.fathom/` (run locks, stop requests and kept spawn streams) and `report/`
(scorecards, which regenerate from the ledger). The `.gitattributes` starts with
`* text=auto eol=lf`, so every text file keeps LF line endings on every platform, and then
names `*.md`, `*.toml`, `*.py`, `*.json` and `*.jsonl` explicitly. This matters here because
the injected `scenarios/assets/nudge.md` is hashed by its bytes into the `nudge` arm's
`config_hash`: a checkout that rewrote its line endings would give the arm a new hash, and
its recorded trials would stop counting as done (section 2). The ledger index does not depend
on it, since it reads CRLF as LF before hashing a ledger.

### `tasks/example/bank.toml`

`name` equals the directory name, as it must: the ledger file is named after it.
`dataset_version = "1"` is part of every trial's resume key; changing the task in a way that
could change its outcome means bumping it. `holdout = []` seals no task. The optional
`[plan] repeats_per_cell = 2` is the study's replication plan: each arm x task cell needs two
completed trials before a contrast from it counts as replicated. It is not hashed and changes
nothing a run buys. See section 4.

### `tasks/example/add/task.toml`

The instruction the arms receive, a turn budget of 10 per spawn, and `verify.py` as the
verifier. Its `[limits] trial_timeout_s` is accepted and ignored; the spawn timeout comes from
the arm. The task declares no `[gate]`, so `fathom validate` reports the gate property as
unverifiable, and a gated strategy would run it as a single spawn. See section 5.

### `tasks/example/add/fixtures/calc.py`

The starting state: `add()` raises `NotImplementedError`. Before each trial fathom copies
`fixtures/` into a fresh temporary git repository, and the agent works there. fathom also
fingerprints this tree and stops a run if a trial changes it (section 6).

### `tasks/example/add/solution/calc.py`

The reference solution, as an overlay over the fixture. `fathom validate` copies it over a
staged fixture and requires the verifier to pass on the result. No arm ever sees it
(section 8).

### `tasks/example/add/verify.py`

The verifier. It reads only `sys.argv[1]`, the path to a copy of the final workspace; runs
`calc.py` in a child process started in that copy, so the agent's code shares neither the
verifier's file path nor its `argv`, both of which lie in the data root; prints one criterion,
`{"correctness": true|false}`; and exits 0 exactly when that criterion is true. It imports
only the standard library, because it runs under the Python that fathom runs under, and
nothing it receives says which arm produced the workspace (section 7). It is the same file
as the complete verifier shown in section 7.

A real task usually emits several criteria, some that a first attempt meets and at least one
that only a careful attempt does, so the per-criterion table can show where arms differ
(`bank-design.md`, section 9). This task has one criterion and would ceiling quickly; it
exists to show the shape.

### `scenarios/bare.toml`

The control arm: one `single-session` spawn of `claude-haiku-4-5` at `effort = "low"`, with
the tools `Read`, `Write`, `Edit`, `Glob` and `Grep` allowed. Spawns are default-deny, so the
allowlist is the agent's whole toolset. The report uses the arm named `bare` as its anchor.
See `arming.md`, section 10.

### `scenarios/nudge.toml` and `scenarios/assets/nudge.md`

The treatment arm. It is `bare.toml` with a different name and a `[context]` table that
appends `assets/nudge.md` to the spawn's system prompt. The sha256 of that file's content
enters the arm's `config_hash`, so editing the note would start a new history for the arm;
the rows in the ledger would stop counting as done. Before a paid run, `fathom run` makes one
cheap spawn to prove the note actually reaches the spawn (`arming.md`, section 10).

### `ledger/example.jsonl`

Ten rows, one `run` row (a spawn's economy) and one `trial` row (the verifier's criteria and
the trial's status) per trial:

| Arm | Repeat | `correctness` |
|---|---|---|
| `bare` | 0 | true |
| `bare` | 1 | false |
| `nudge` | 0 | true |
| `nudge` | 1 | true |
| `nudge-draft` | 0 | true |

Each row carries its `config_hash`, the exact text that was hashed to produce it
(`config_preimage`), the bank's `dataset_version`, and the fixture fingerprint. These rows predate the
`engine_version` field, and ledger rows are never rewritten, so they do not carry it. Rows
written by a current engine do.

Because the `bare` and `nudge` hashes match the committed scenario files, the four trials
count as done: `fathom run example --dry-run` plans nothing at the default two repeats, and
plans two new trials with `--repeats 3`.

### `docs/reports/LEDGER-INDEX.md`

Generated from the ledgers by `fathom index --write`: the sha256 of each ledger and its
completed trials per arm. `fathom reconcile` fails when it and the ledgers
disagree. Never edit it by hand.

### `docs/STATUS.md`

The index of analyses run against this data root, one row per bank. In a real data root each
row points to a write-up under `docs/reports/`.

### `report/`

Where `fathom report example` writes `scorecard-example.md`. It is regenerated from the ledger
at any time and is not committed.

### Compared with a fresh `fathom init`

Everything `fathom init` creates is already here: `fathom.toml`, `.gitignore`,
`.gitattributes`, `tasks/`, `scenarios/`, `ledger/` and `docs/reports/`. In a copy of this
directory outside the engine repository, `fathom init` would list each of them as `kept` and
write nothing. Inside the engine repository it refuses, as it refuses any directory inside an
engine checkout. The one difference from a fresh data root is the content of `fathom.toml`,
which carries this directory's own comments and its `[[reconcile.known]]` entries where
`fathom init` writes a commented-out template.

## Try it

Everything below is free: nothing spawns a model. Run it from this directory with
`FATHOM_HOME` unset (a set `FATHOM_HOME` takes precedence over the directory you are in), or
from anywhere with `--home` pointing here, which works either way. From an engine clone,
prefix each command with `uv run --project <clone>`.

```sh
fathom validate example           # 2 pass, 1 unverifiable (no gate); exit 0
fathom run example --dry-run      # arms bare, nudge; 0 trials planned (4 already done)
fathom report example             # writes report/scorecard-example.md
fathom index                      # the ledger index is current
fathom reconcile                  # OK, with the two nudge-draft findings excused
```

`fathom validate` needs `git` on PATH to stage the fixture. When `FATHOM_STREAM_DIR` is unset
it also prints a `note:` line, not a warning, and no action is needed: it says that a real
`fathom run` keeps both arms' spawn streams (each arm grants tools) under
`.fathom/streams/example/` in the data root.

To start your own data root from this one, copy the directory, rename the bank, and delete
the ledger, the ledger index, the status row and the `[[reconcile.known]]` entries, which all
describe this directory's history rather than yours. `fathom init` is the cleaner start.
