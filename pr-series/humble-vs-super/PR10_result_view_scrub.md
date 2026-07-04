## Mode
plan -> implement (TDD) -> verify (small patches, test after each)

## Mandatory pre-read
- `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` — §10
- `src/fathom/grading/verifier.py` — the result-view builder the verifier receives (`argv[1]`)
- `docs/adr/0003-*` (blindness)

## Task
Harden blindness against plugin process-scaffolding: when building the result-view handed to grading, strip or
normalize known process-scaffolding paths so a later judge cannot infer which arm produced the workspace —
e.g. `.remember/`, `plans/`, `docs/plans/`, and journal dirs. Phase-1 verifiers already key only on the task
deliverable, so this is forward-looking hardening for when the pairwise judge is lit.

## Constraints
- Verifier output must be IDENTICAL with or without the scaffolding present — the scrub must not change any
  criterion result (test this explicitly).
- Strip by a small, explicit allow/deny list of scaffolding dir names; do not over-scrub the deliverable.

## Starting file list
1. `src/fathom/grading/verifier.py`
2. `tests/test_verifier.py` (or the grading test module)

## Definition of done
- [ ] Given a workspace containing scaffolding directories, the result-view handed to grading excludes them
      (spec §10 acceptance; unit-tested).
- [ ] Verifier output is identical with and without the scaffolding directories present (unit-tested).
- [ ] All quality gates pass.
