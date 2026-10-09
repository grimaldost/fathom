# Ledger row contract

The fathom ledger (`ledger/<bank>.jsonl`) is append-only: one JSONL object per line, one
line per trial, run, grading, or void event. This page is the reference for every field and
key that may appear on a row. It defines the row schema, the resume key, the pass rule, and
the semantics of each record kind.

Readers accept rows written before a field existed (append-only invariant, ADR-0002). Fields
are identified by name and are added to this page only once — they stay forever. When a new
field is added, existing readers that predate it will not break: they will see it, skip it
or default it as their design requires, and row-format agreement is maintained.

## Record kinds

Every row carries a `kind` discriminator that names its type. Four kinds are currently defined:
`trial`, `run`, `grading`, and `void`.

### Trial (`kind: "trial"`)

One trial of a task under a configuration. The trial records the configuration (config_hash,
dataset_version, bank, task_id, repeat), the identity fields needed for a second attempt
(cli_version, tool_git_sha, pin_level), and the outcome: whether the task completed or
errored, and the verifier's results if scoring succeeded.

**Resume key fields** (form the unique key a resume uses to avoid re-running the same cell):
`bank`, `dataset_version`, `task_id`, `config_hash`, `repeat`.

**Fields:**

- `bank` (str): The bank name this trial belongs to.
- `task_id` (str): The task id (from `tasks/<bank>/<id>/` or equivalent).
- `repeat` (int): Repeat count within (bank, config_hash, task); starts at 0.
- `status` (str): Outcome status: `"completed"` (ran successfully) or `"errored"` (trial
  failed, no verifier result).
- `dataset_version` (str): The dataset version this trial used (from `bank.toml`).
- `config_hash` (str): The SHA256 hex digest of the scenario's configuration and arm setup.
  Identical configurations produce identical hashes, so two runs with the same hash compete
  fairly; a hash change invalidates prior results (the resume key includes it).
- `tool_git_sha` (str): The SHA of the tool's repository at run time (e.g., the arm's tool
  repo). Provenance only; not part of the resume key or config_hash.
- `cli_version` (str): The version of the fathom CLI that recorded this trial.
  Provenance only; not part of the resume key or config_hash.
- `pin_level` (str): The pin strength: `"strong"` (single explicit model) or `"series"`
  (series engine chose a model per trial). Provenance only; not part of config_hash.
- `verifier_results` (dict or None): The verifier's outcome. `None` means no verification
  ran (trial errored before grading). When present, a dict of criterion name -> bool:
  each criterion that the verifier checked and its result. The trial passes when the dict
  is non-empty and all values are truthy (see `is_pass` rule in `report.py`).
- `detail` (str): An optional note on the trial's execution (e.g., strategy notes for
  defect-escape recovery). Empty string when absent.
- `config_preimage` (str): The exact configuration string that was hashed to produce
  `config_hash`. Stored for bit-exact validation without recomputing from the tree
  (which may have changed). Empty on all rows written before 0.4.0.

**Extra keys the run loop adds** (not dataclass fields; added by cli.py before append):

- `valid` (bool): `True` when the trial `status` is `"completed"`, `False` otherwise.
  A convenience derived from `status`.
- `verifier_stdout` (str): The first 64KB of the verifier process's stdout (capped for
  ledger size). Present only when verification ran and did not error.
- `verifier_stderr` (str): The first 64KB of the verifier process's stderr (capped for
  ledger size). Present only when verification ran and did not error.
- `scenario` (str): The name of the arm (scenario) that was evaluated. Used by reports to
  label trials; the arm identity stays `config_hash` for resume and comparison.
- `holdout` (bool): `True` if this task is in the bank's sealed holdout set, `False`
  otherwise. Holdout trials are development data once spent; reports render them separately.
- `fixture_sha` (str): The SHA256 hex digest of the task's fixture (as fingerprinted by
  `fixture_fingerprint`). Provenance only; used to detect fixture drift.
- `plan_repeats_per_cell` (int or null): The bank's declared `[plan] repeats_per_cell`
  (`bank.toml`) when the row was written; `null` when the bank declared none. Rows written
  before the field existed lack it.
- `plan_replication` (str): `"directional"` when the plan in force declared no
  `repeats_per_cell` or declared 1, `"replicated"` when it declared 2 or more. It describes
  the plan, not the cell: whether a cell holds enough completed trials is computed from the
  ledger (the scorecard and `fathom reconcile` do), and no reader lets this field override
  that. Neither key is part of `config_hash`, the preimage or the resume key.

**Provenance-only fields** (not part of config_hash, resume key, or scoring logic, but
added by the ledger module to every row):

- `engine_version` (str): The version of the installed fathom distribution that wrote this
  row, or `"unknown"` if running from a source tree without metadata. Invisible to readers
  (not a dataclass field).
- `written_at` (str): ISO-8601 UTC timestamp with offset and second precision (the same
  format as void `voided_at`). The moment `append_record` wrote this row. Invisible to
  readers.

### Run (`kind: "run"`)

One spawned attempt to solve a task, which may be part of a multi-attempt trial or the sole
attempt. Runs record token usage, turn count, duration, exit code, and the cost the provider
reported. A trial may have multiple run rows appended before its trial row; the ledger
orders them exactly as they arrived, and reports join them to their trial by `config_hash`.

**Resume key fields** (subset; the trial's resume key is the authoritative one):
`bank`, `dataset_version`, `task_id`, `config_hash`, `repeat` (form of identifier only).

**Fields:**

- `bank` (str): The bank name this run belongs to.
- `task_id` (str): The task id.
- `repeat` (int): Repeat count (matches the trial's repeat).
- `usage` (dict): Token usage reported by the provider, with keys like `input_tokens`,
  `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` (if the model
  supports prompt caching). Empty dict `{}` when unavailable.
- `turns` (int): Number of conversation turns (messages exchanged with the model).
- `duration` (float): Wall-clock seconds elapsed from spawn to completion.
- `exit_code` (int): The process exit code (0 for success, non-zero for failure or abort).
- `dataset_version` (str): The dataset version (same as the trial's).
- `config_hash` (str): The configuration hash (same as the trial's; used to join run to trial).
- `tool_git_sha` (str): The tool repository SHA at run time. Provenance only.
- `cli_version` (str): The fathom CLI version. Provenance only.
- `pin_level` (str): The pin strength (`"strong"` or `"series"`). Provenance only.
- `scenario` (str): The arm name (additive field; defaults to empty on legacy rows from
  before this field existed). Empty string means the arm identity is not recorded; the
  config_hash is the true key.
- `cost_usd_est` (float): USD as the provider reported it (additive field; defaults to 0.0).
  The sum of run-row costs is the per-experiment spend. Rows with `cost_source == "none"`
  carry no cost (a gap in the provider's reporting); reports note trials with such rows.
- `cost_source` (str): `"reported"` (the provider gave a USD value) or `"none"` (provider
  gave no cost; this run's cost is unknown). Additive; defaults to `"reported"`.
  Disambiguates measured cost from estimates or gaps.
- `model_id` (str): The exact model id the CLI reported (the strong pin; the model actually
  used, not a policy or tier name). Additive; defaults to empty on legacy rows.
  Provenance only; not part of config_hash.
- `models_seen` (list of str): Each distinct `model` value the spawn's output named, in the
  order first seen: the init event's, each assistant message's (a subagent's included) and
  the result's. `model_id` keeps one model; a spawn whose subagent ran on another model
  lists both here. Additive; `[]` on legacy rows, on series-strategy runs (built from the
  engine's spawn events, not a CLI stream) and when the output named no model. Provenance only; not part
  of config_hash.
- `config_preimage` (str): The exact configuration string hashed to produce `config_hash`.
  Additive; empty on rows written before 0.4.0. Stored for bit-exact validation.

**Provenance-only fields** (added by the ledger module):

- `engine_version` (str): The installed fathom version. Invisible to readers.
- `written_at` (str): ISO-8601 UTC write time. Invisible to readers.

### Grading (`kind: "grading"`)

Pairwise comparison of two trial configurations by a judge. Used to establish arm ordering
when multiple arms compete.

**Fields:**

- `bank` (str): The bank name.
- `task_id` (str): The task id.
- `repeat` (int): Repeat count.
- `verdict` (str): Judge's decision: `"a"` (config_hash_a won), `"b"` (config_hash_b won),
  or `"tie"` (tied).
- `dataset_version` (str): The dataset version.
- `config_hash_a` (str): The first configuration (often the baseline or "bare" arm).
- `config_hash_b` (str): The second configuration (the tested arm).
- `tool_git_sha` (str): The tool repository SHA.
- `cli_version` (str): The CLI version.
- `judge_config_hash` (str): The SHA256 hash of the judge's configuration. Provenance only.
- `judge_model` (str): The model the judge used (e.g., `"claude-sonnet-5-5"`). Provenance only.
- `pin_level` (str): The pin strength (`"strong"` or `"series"`).

**Provenance-only fields** (added by the ledger module):

- `engine_version` (str): The installed fathom version.
- `written_at` (str): ISO-8601 UTC write time.

### Void (`kind: "void"`)

Append-only exclusion of a trial (and its run rows) from consideration. A void names a
configuration and reason; all trial and run rows with that (bank, dataset_version, task_id,
config_hash, repeat) key written BEFORE the void are excluded. A void does not prevent
the same key from being re-run afterwards; if re-run, the new rows count.

**Fields:**

- `bank` (str): The bank name.
- `task_id` (str): The task id.
- `repeat` (int): Repeat count.
- `dataset_version` (str): The dataset version.
- `config_hash` (str): The configuration hash.
- `scenario` (str): The arm name (for reports; the hash is the key).
- `reason` (str): Why this trial is voided (e.g., `"fixture drift"`, `"manual exclusion"`).
  Shown in reports.
- `evidence` (str): Optional link or note pointing to proof (e.g., a path to the drift
  detection or a GitHub issue).
- `voided_at` (str): ISO-8601 UTC timestamp with offset and second precision when the void
  was recorded. Optional; set by the application that records the void.

**Provenance-only fields** (added by the ledger module):

- `engine_version` (str): The installed fathom version.
- `written_at` (str): ISO-8601 UTC write time.

## Resume key

The resume mechanism re-runs the same (bank, dataset_version, task_id, config_hash, repeat)
cell, avoiding re-run of completed cells. The key is formed from fields in the trial record,
and the CLI maintains a `completed_keys()` set by reading trial and void rows. Errored
trials do NOT occupy the resume key; they are eligible for re-run.

```python
(
    trial.bank,
    trial.dataset_version,
    trial.task_id,
    trial.config_hash,
    trial.repeat,
)
```

## Trial-to-run join

A trial may have multiple run rows, appended in the order they occurred. The ledger appends
all run rows for a trial before the trial row itself (so that if a crash happens between
the last run and the trial record, the runs exist but no trial claims them). Readers join
runs to trials by `config_hash` and then by (task_id, repeat) within that hash. When
a trial has no run rows, the trial is treated as a run with no token data.

## Per-experiment cost

The total cost for an arm × task × repeat cell is the sum of its run rows' `cost_usd_est`.
Rows with `cost_source == "none"` carry no provider-reported cost and are left out of the
sum; reports mark such trials. Cost is always computed, even when `cost_usd_est` is 0.0
or missing (a legacy row defaults to 0.0 and is included in the sum).

## Pass rate denominators

Pass-rate computation uses only completed trials (status == "completed"). Errored trials are
excluded from the denominator (they show in a separate "Infra Errors" column). Voided trials
are excluded: a void row removes all earlier trial and run rows with its key, and a re-run
appended after the void counts in full.

## Pass rule

A trial passes when its `verifier_results` is a non-empty dict with all truthy values. The
rule is implemented by `fathom.report.is_pass()`:

- `None` → `False` (no verification ran; trial errored before grading)
- Empty dict `{}` → `False` (verification ran but no criteria were checked)
- Dict with all truthy values, e.g., `{"criterion_a": True, "criterion_b": True}` → `True`
- Dict with any falsy value, e.g., `{"criterion_a": True, "criterion_b": False}` → `False`
- Other types → truthiness of the value (for forward compatibility)

## Void semantics

A void row applies to trial and run rows written BEFORE it (order matters). The same key
can be re-run after a void, and the re-run's rows are scored normally.

When `apply_voids(rows)` is called, it returns rows with voided trials and their runs
dropped, but void rows themselves kept (so reports can say what was excluded and why).

Resume does not re-run a void: `completed_keys()` reflects voids (a voided key is removed
from the set as of the void row).

## Field stability

Once a field is named on this page, it stays. New fields are additive and have defaults or
are optional, so old readers do not break. A field introduced in version X remains in all
later versions; the append-only invariant (ADR-0002) ensures it.

Fields marked "additive" in this document arrived in earlier units and are documented for
completeness and for consistency with bank documentation. Rows written before such a field
existed use the default value (0.0, empty string, false, empty dict, etc.) when the field
is read.
