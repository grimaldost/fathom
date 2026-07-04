## Mode
plan -> implement (TDD) -> verify

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 2 + Context
- `docs/adr/0002-trial-run-append-only-ledger.md`

## Task
Implement `src/fathom/ledger.py` per spec section 2: dataclasses for the three
record kinds (trial, run, grading) carrying the version-pin fields ADR-0002
names (dataset_version, config_hash, tool_git_sha, cli_version,
judge_config_hash where applicable, plus a pin-level marker for weaker series
pins); append and iterate operations over per-bank JSONL files under `ledger/`;
resume-key computation `(bank, dataset_version, task_id, config_hash, repeat)`
returning the set of completed tuples; a tolerant reader that skips malformed
lines with a `warnings.warn` and keeps reading.

## Constraints
- Stdlib only. Append-only: no function rewrites or truncates an existing file;
  the only write primitive opens in append mode.
- Stable serialization: `json.dumps` with `sort_keys=True`.
- Records carry `kind`; unknown kinds round-trip untouched by readers.

## Starting file list
1. `src/fathom/ledger.py`
2. `tests/test_ledger.py` (stdlib-runnable)

## Definition of done
- [ ] Round-trip tests for all three record kinds
- [ ] Resume-set computation skips completed tuples (errored tuples are NOT completed)
- [ ] Malformed-line fixture: warning emitted, later lines still load
- [ ] `python tests/test_ledger.py` exits 0; all quality gates pass
