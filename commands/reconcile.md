---
description: Check every fact this repo derives twice, and report where they disagree (free; spends nothing)
argument-hint: "[--check NAME] [--list]"
allowed-tools: Bash
---

Run fathom's reconciliations — the checks that compare two independent derivations of the
same fact and fail while they disagree.

1. Resolve the fathom checkout (`$FATHOM_HOME`, else the current fathom repo, else ask).
2. From that directory, run: `uv run python -m fathom reconcile $ARGUMENTS`
3. Exit 0 means every derivation agrees. Exit 13 (`EXIT_UNRECONCILED`) means either a
   disagreement or a stale exception — both are failures, and the output names which.

Why this exists: counting how every defect since 0.2.0 was found gives paid-measurement 6,
sustained-operation 6, **post-hoc-audit 3**. That last class shares one property — the run
completed and every artifact was internally self-consistent — so no amount of buying or
operating surfaces it. What surfaces it is holding two derivations of one fact against each
other.

When reading the output:

- **`[DISAGREES]`** — two derivations of one fact do not match. Each line says which check,
  which subject, and what to do. Never "fix" one of them to match the other without
  establishing which is right.
- **`[STALE EXCEPTION]`** — an accepted discrepancy stopped occurring, so its excuse must be
  deleted. This is a failure on purpose: an exception list that only grows is how a gate
  becomes vacuous, which is the failure mode this repo keeps catching.
- **`preimage coverage: N/M`** — how many ledger rows carry the second derivation the exact
  `config-hash-preimage` check needs. Rows written before 0.4.0 carry none. That is a
  reported coverage gap, **not** a disagreement, and it only shrinks as new trials are
  bought. Do not read a low number as a failure.

`--list` prints the registered checks. `--check NAME` (repeatable) runs a subset; an unknown
name is an error rather than a silent empty run.
