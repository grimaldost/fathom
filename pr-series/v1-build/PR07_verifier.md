## Mode
plan -> implement (TDD) -> verify

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 7
- `docs/adr/0003-blind-result-only-scoring.md`

## Task
Implement `src/fathom/grading/verifier.py` per spec section 7: extract the
**scored result view** from a final trial workspace (working tree at the final
integration tip; exclude engine output paths — outputs dir, tracker.jsonl,
logs, the automation gitignore marker — AND any stray engine input assets:
series config, prompt files); run the task's `verify.py` in the harness
environment with the result-view path as its only task argument — no scenario
identity anywhere in argv or env; capture per-criterion JSON from stdout;
nonzero exit with valid JSON = scored fail; crash or non-JSON = trial errored.

## Constraints
- Stdlib only. The result view is a copy/export, never a mutation of the trial workspace.
- The verifier subprocess env is constructed minimal-explicit (not inherited wholesale).

## Starting file list
1. `src/fathom/grading/__init__.py`, `src/fathom/grading/verifier.py`
2. `tests/test_verifier.py` (stdlib-runnable) + fixtures: passing/failing/crashing verify.py samples; bare-style and series-style workspaces with identical code (series-style includes a stray engine asset)

## Definition of done
- [ ] Three outcomes covered: pass-with-criteria, fail-with-criteria, errored (crash/garbage)
- [ ] Argv/env blindness asserted (no scenario identifier)
- [ ] Blindness fixture: bare-style and series-style workspaces yield byte-identical verifier input
- [ ] `python tests/test_verifier.py` exits 0; all quality gates pass
