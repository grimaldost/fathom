---
description: Check every fact the data root derives twice, and report where they disagree (free; spends nothing)
argument-hint: "[--check NAME] [--list]"
allowed-tools: Bash
---

Run fathom's reconciliations: checks that compare two independent derivations of
the same fact and fail while they disagree.

1. Resolve the data root: `$FATHOM_HOME` if set, else the nearest directory at or
   above the current one whose `fathom.toml` has a `[data_root]` table, else ask
   the user. The directory must carry that marker, and it must not be the
   plugin's own tree, a plugin cache directory, or inside either. If
   `$FATHOM_HOME` is set but the current directory sits inside a different data
   root, ask the user which one they mean: `FATHOM_HOME` wins without any error.
2. From the data root directory, run the engine this plugin ships:
   `uv run --no-dev --frozen --project "${CLAUDE_PLUGIN_ROOT}" python -m fathom --home "<data root>" reconcile $ARGUMENTS`
   Keep both uv flags: `--no-dev` stops the first call from installing the
   development tools into the plugin's environment, and `--frozen` uses the
   plugin's lock file as shipped instead of rewriting it.
3. Read the exit code and the last line.
   - **0**: no unexcused disagreement and no stale exception. The last line reads
     `RECONCILE: OK (N check(s) run, N skipped, N disagreement(s), N excused, N stale
     exception(s))`, with `, N warning(s)` before the closing parenthesis when a
     `[WARNING]` line was printed. Skipped checks, warnings and excused (accepted)
     findings do not change the exit code.
   - **13** (`EXIT_UNRECONCILED`), after the checks ran: at least one `[DISAGREES]` or
     `[STALE EXCEPTION]` line was printed, and the last line reads
     `RECONCILE: FAILED (...)`.
   - **13**, before any check ran: a refusal, printed on stderr as one `error:` line
     with no summary. The causes are
     - `fathom.toml` cannot be read, is not UTF-8 (Windows PowerShell 5.1 writes UTF-16
       with `>`), or is not valid TOML;
     - a malformed exception list: `reconcile` is not a table, `reconcile.known` is not
       an array of tables, or an entry has a missing or unknown field, an empty value, a
       check name that is not registered, or the same check, subject and key as an
       earlier entry;
     - `--check` names a check that is not registered;
     - the directory is neither a data root nor an engine checkout.

     Fix the file or the path, then run again.
   - `--list` prints the registered checks and exits 0 without looking at any directory.

Why this exists: a run can complete with every artifact internally consistent and
still carry a defect — a report quoting a trial count the ledger no longer has, or
trials from an arm whose configuration was never committed. Spending more or
operating longer does not surface that class. Holding two derivations of one fact
against each other does.

When reading the output:

- **`[SKIPPED] <check>: <reason>`** — a check that does not apply at this root.
  `version-sites` runs only in an engine checkout, so in a data root
  `[SKIPPED] version-sites: …` is expected. A skipped check is neither a pass nor a
  failure, and the summary counts it separately. A `[[reconcile.known]]` entry for a
  skipped check is reported as a stale exception.
- **`[DISAGREES] [<check>] <subject> (<key>): <detail>`** — two derivations of one
  fact do not match. The check, subject and key are the three values an exception is
  declared against; the detail says what differs. Never "fix" one side to match the
  other without establishing which is right. A stale `docs/reports/LEDGER-INDEX.md` is
  fixed by rendering it again: `index --write`, with the same invocation form as in
  step 2.
- **`[WARNING] [<check>] <subject> (<key>): <detail>`** — a finding of a check that
  warns and never fails. Only `replication` does: for a bank with completed trials, key
  `undeclared` (its `bank.toml` declares no `[plan] repeats_per_cell`, has none, or has a
  malformed one; the detail says which) or `one` (a plan of 1) means every result from
  the bank is directional, and `short:<arm>/<task>` names a cell holding fewer completed
  trials than the plan declares. Tell the user the results are directional, not
  replicated. A warning is excused like a disagreement, by its check, subject and key.
- **`[STALE EXCEPTION]`** — an accepted finding stopped occurring, so its entry
  must be deleted. This is a failure on purpose: an exception list that only grows
  lets the gate pass on anything.
- **`preimage coverage: N/M`** — how many ledger rows carry the stored configuration
  string the exact `config-hash-preimage` check needs. Rows written by older engine
  versions carry none. That is a coverage gap, not a disagreement.

The registered checks: `ledger-index` (the committed index against a fresh render of
`ledger/`), `config-hash-preimage` (each row's `config_hash` against the sha256 of its
own stored preimage, computed again), `scenario-known` (every completed trial's arm
against the scenario files in the data root), `version-sites` (the engine's version
declarations; engine checkouts only) and `replication` (each bank's `[plan]
repeats_per_cell` against the completed trials per arm and task, counted as the
scorecard counts them; it warns and never fails).

Accepted discrepancies and warnings are data, not engine code. They live in the data
root's `fathom.toml`, one table per finding, keyed by the check name, subject and key the
output prints:

```toml
[[reconcile.known]]
check = "scenario-known"
subject = "example"
key = "retired-arm"
reason = "Why this discrepancy is accepted, and where a reader can verify it."
```

The engine ships no exceptions of its own. `--check NAME` (repeatable) runs a subset;
an unknown name is an error rather than a silent empty run.
