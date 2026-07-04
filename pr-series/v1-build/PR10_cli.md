## Mode
plan -> implement (TDD) -> verify

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 10 (+ skim sections 2, 6 for the pieces you wire)

## Task
Implement `src/fathom/cli.py` (argparse; console script `fathom` in pyproject) per
spec section 10: `fathom run <bank>` plans the matrix (scenario set x non-holdout
tasks x repeats, default repeats 2), consults the ledger resume set and skips
completed tuples, prints the upfront trial/spawn counts and cost ceiling BEFORE
any spawn, executes trials via the strategy executors, appends to the ledger,
and runs verifier grading per completed trial; `--dry-run` prints the plan and
ceiling and spawns nothing; `--limit N` caps planned trials; `fathom report
<bank>` calls the section-9 renderer; `fathom smoke` is registered but may
delegate to a stub raising "not yet implemented" (section 11 fills it). An
infrastructure error from ANY executor stops the matrix cleanly: affected
trial not scored, named infrastructure exit status, ledger untouched as the
resume checkpoint.

## Constraints
- Stdlib only (argparse). Executors/runners injectable; tests fully stubbed.
- No spawn may happen before the ceiling print (assert the ordering in tests).

## Starting file list
1. `src/fathom/cli.py` (+ console-script entry in `pyproject.toml`)
2. `tests/test_cli.py` (stdlib-runnable)

## Definition of done
- [ ] Dry-run: counts + ceiling printed, zero spawns
- [ ] `--limit` caps the plan; completed ledger -> zero planned trials
- [ ] Stubbed usage-limit error: clean stop, trial unscored, named exit status
- [ ] `python tests/test_cli.py` exits 0; all quality gates pass
