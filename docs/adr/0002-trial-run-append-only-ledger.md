# ADR-0002 — Two-level trial/run records in an append-only JSONL ledger

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

Scenarios in fathom are execution strategies, not flag sets: one scored attempt may
be a single long session or a series of many sessions run by the series engine. The prior harness
(craft-collection `evals/`) kept results in gitignored report JSONs merged
read-modify-write, which produced clobber hazards between runners and no
longitudinal history. Inspect AI's eval-set design (filesystem log dir, idempotent
resume) is the verified prior art for the alternative.

## Decision

The ledger is append-only JSONL, committed to git, with two levels: a **trial** is
one scored attempt at a task under a scenario (status, verifier results, version
pins) and owns 1..N **run** records (one agent invocation each: usage, turns,
duration, exit). **Grading** records reference trial pairs. The resume key is
`(bank, dataset_version, task_id, config_hash, repeat)`; re-runs skip completed
tuples; reports are always regenerated from the ledger, never merged in place.
Every record carries its version pins (dataset_version, config_hash, tool_git_sha,
cli_version, judge_config_hash where applicable).

## Alternatives considered

- **Single-level run records** — cannot represent multi-session strategies
  without aggregating at read time by fragile convention; session count would be
  reconstructed rather than recorded.
- **A database (SQLite)** — transactional comfort, but not git-diffable, harder
  to inspect on a phone, and adds a dependency to the stdlib core for no v1 need.
- **Keep read-modify-write report files** — the prior harness's demonstrated
  clobber/overwrite failure mode; rejected on field evidence.

## Consequences

- New invariant: **ledger files are append-only** — no code path rewrites an
  existing line; tolerant readers skip malformed lines with a warning. (Planned
  guard: an edit-time hook rejecting in-place rewrites of `ledger/*.jsonl`.)
- New invariant: **task IDs are stable** — renaming or renumbering a task breaks
  resume keys; dataset_version bumps instead.
- Interrupted matrices are resumable by construction; a budget stop is a
  checkpoint, not a loss.
