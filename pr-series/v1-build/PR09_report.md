## Mode
plan -> implement (TDD) -> verify

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 9
- Port source for the interval math (read-only, outside this repo): `/path/to/craft-collection/evals/harness/stats.py`

## Task
Implement `src/fathom/report.py` per spec section 9: `render(bank) ->
report/scorecard-<bank>.md`, computed from the ledger ALONE (no other state):
per-scenario verifier pass-rate with Wilson 95% CI (port `wilson_interval`),
pairwise win/tie/loss vs the bare anchor when grading records exist, economy
table (tokens, turns, wall-clock, sessions per trial, estimated USD), holdout
section separated from dev tasks, one verdict line per scenario. Every verdict
line prints its n and the Wilson CI with a "directional, not final" qualifier;
the series-pipeline verdict line enumerates the arm deltas (human
decomposition, per-PR gates, review/fix subagents, engine settings).

## Constraints
- Stdlib only. Rendering is deterministic and idempotent — same ledger, byte-identical output.
- Infrastructure-errored trials appear in an error column, never in pass-rate denominators.

## Starting file list
1. `src/fathom/report.py`
2. `tests/test_report.py` (stdlib-runnable) + fixture ledger (three scenarios, one multi-run trial, one holdout task, one infrastructure error) + golden scorecard file

## Definition of done
- [ ] Golden-file test passes; re-render is byte-identical
- [ ] Verdict lines carry n + CI + qualifier; pipeline line enumerates arm deltas
- [ ] Economy table includes sessions-per-trial from multi-run trials
- [ ] `python tests/test_report.py` exits 0; all quality gates pass
