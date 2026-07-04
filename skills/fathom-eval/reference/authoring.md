# Authoring a fathom bank / scenario / task

The parsers are the source of truth: `src/fathom/scenario.py` (scenarios) and
`src/fathom/taskbank.py` (banks and tasks). Everything below is as-built against
them. All files are **flat TOML** (a scenario is not wrapped in a `[scenario]`
table — the old design-spec example showing one is stale).

## Bank layout

```
tasks/<bank>/
  bank.toml                 # the manifest
  <task-id>/
    task.toml               # the task definition
    verify.py               # the blind verifier (reads only the result-view)
    fixtures/               # staged into a fresh git workspace as the task's starting state
    original/               # optional, harness-side: stash for the regression-test swap
```

Scenarios (arms) live separately, under `scenarios/` (or a bank-specific subdir
like `scenarios/skill-pyeng/` — which then requires `--scenarios-dir`).

## `bank.toml`

```toml
name = "skill-pyeng-v1"       # required
dataset_version = "1"          # required — bump on ANY task/fixture/verifier change (see below)
holdout = ["some-task-id"]     # required — array (may be empty []); each id must exist in the bank
```

## `task.toml`

```toml
id = "modernize-timeflow"                 # required, unique within the bank
instruction = "…what the agent is asked to do…"   # required

[limits]                                  # required table
trial_timeout_s = 600                     # wall-clock ceiling for the trial
max_turns = 40                            # plumbed to the spawn — set high enough or the run truncates

[verify]                                  # required table
entry = "verify.py"                       # required — the verifier script, run with the result-view path as argv[1]
timeout_s = 120                           # optional — verifier's own timeout
hard_criteria = ["messages_quoted"]       # optional — the capability-gated criteria to read in the scorecard

[gate]                                    # optional — the deterministic oracle the gated-* strategies run
run = "python -m pytest -q"               # the gate command; nonzero exit = red gate
```

`limits`, `verify`, and `gate` are parsed as opaque tables, so extra keys are
allowed and consumed downstream; the keys above are the ones the CLI and
strategies actually read. Only `verify.entry` is enforced as required within
`[verify]`.

## Scenario (arm) TOML

```toml
name = "pyeng-skill"          # required — arm name; "bare" is the pairwise anchor in the report
adapter = "claude-cli"        # required
model = "claude-opus-4-8"     # required
strategy = "single-session"   # required — single-session | gated-session | gated-review | reprompt-session | series
effort = "high"               # required — low | medium | high | xhigh

[tools]
source = "none"               # "none" | "repo"  (default "none")
allowed = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)"]   # empty under default-deny == UNARMED
# disallowed = [...]          # optional belt-and-braces
# repo = "C:/…/convoy"        # required when source = "repo" (the series engine)

[context]                     # optional treatment arm — appends this file's body to the spawn's
                              # system prompt (via --append-system-prompt-file)
inject = "assets/python-engineering.md"   # path relative to THIS scenario file; its CONTENT sha256 enters config_hash

[plugins]                     # optional treatment arm — mount plugin dirs into the spawn
mount = ["C:/…/some-plugin"]  # paths relative to this scenario file; each dir's tree_sha enters config_hash

[env]                         # optional — non-secret env overrides for the spawn (never a credential)
SOME_MODE = "fast"            # values support ${workspace} and ${VARNAME}, substituted at spawn time

[gate]                        # optional — scenario-level oracle strengthening (runs AFTER the task gate)
extra = ["python probe.py"]   # each command's text enters config_hash (the script's contents do not)

[limits]
trial_timeout_s = 600         # optional per-scenario override
```

Only `name`, `adapter`, `model`, `strategy`, `effort` are required; every table
is optional and defaults to empty. **An empty `allowed` under headless
default-deny means the agent has no tools — the arm is UNARMED, not evaluated.**

## `verify.py` — the blind verifier

- Reads **only** `argv[1]`, the path to a stripped result-view of the final
  workspace. **No scenario identity in argv or env** (blindness, ADR-0003).
- Emits a flat `{criterion: bool}` JSON object to **stdout**.
- Exits `0` **iff** the correctness gate holds (a nonzero exit fails the trial's
  correctness gate regardless of the JSON).

```python
import json, pathlib, sys

workspace = pathlib.Path(sys.argv[1])
src = (workspace / "timeflow.py").read_text(encoding="utf-8")
criteria = {
    "uses_zoneinfo": "zoneinfo" in src,
    "no_naive_datetime": "datetime.now()" not in src,
}
print(json.dumps(criteria))
sys.exit(0 if all(criteria.values()) else 1)
```

## Resume mechanics — `dataset_version` and `config_hash`

The resume key is `(bank, dataset_version, task_id, config_hash, repeat)`, and
only `status == "completed"` trials count as done. Two ways to accidentally fork
longitudinal history and re-spend "done" trials:

- **`dataset_version`** — bump it on **any** change to a task's instruction,
  fixtures, or verifier. It is in the resume key; forgetting to bump means a
  changed task resumes against stale results.
- **`config_hash`** — a SHA-256 over the resolved scenario. It includes the
  `[context].inject` file's **content sha256**, each mounted plugin's `tree_sha`
  (a hash over every file under the dir), the tool repo's git SHA, and the
  `[gate].extra` command text. So **editing an inject brief, a mounted plugin
  file, or bumping the engine repo forks the hash** and re-spends resumed trials.
  Absent optional tables and empty lists deliberately do **not** shift the hash,
  so adding the schema never breaks existing ledgers.

When you must change a probe script's *contents* (which do not enter the hash),
version the scenario `name` instead so the change is visible in the resume key.
