## Mode
plan -> implement (TDD) -> verify

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 8
- `docs/adr/0003-blind-result-only-scoring.md`
- Port source (read-only, outside this repo): `/path/to/craft-collection/evals/harness/judge.py`

## Task
Port the swap-order pairwise judge to `src/fathom/grading/judge.py` per spec
section 8: judge each (treatment, bare-anchor) pair in BOTH A/B orders; win
only when both orders agree, else tie; pairs match by repeat index; the judge
call goes through the `Runner` protocol with tools disabled and a strict-JSON
rubric prompt; the A/B payload is the section-7 scored result view rendered as
a unified diff against the task's fixture baseline, size-capped with a recorded
truncation marker; grading records carry the resolved judge model and a judge
config hash. This path ships dark in v1 (exercised by tests, not by the v1
verdict) — correctness still gates.

## Constraints
- Stdlib only. Runner stubbed in all tests — no real judge spawns.
- No scenario names in any judge prompt content (assert it).

## Starting file list
1. `src/fathom/grading/judge.py`
2. `tests/test_judge.py` (stdlib-runnable)

## Definition of done
- [ ] Agreement -> win; disagreement -> tie; repeat-index pairing covered
- [ ] Payload: result-view unified diff vs fixture baseline, size cap + truncation marker
- [ ] Judge prompt contains A/B diffs and no scenario names (asserted)
- [ ] Grading records carry judge model + judge config hash
- [ ] `python tests/test_judge.py` exits 0; all quality gates pass
