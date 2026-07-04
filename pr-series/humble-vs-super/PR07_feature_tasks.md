## Mode
plan -> implement (TDD) -> verify (small patches, test after each)

## Mandatory pre-read
- `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` — §7 (and the "worth-loading bar" note in §5/Spike)
- `tasks/skill-pyeng-v1/modernize-timeflow/verify.py` — blind, layout-agnostic verifier model
- `tasks/pr-pilot-v1/README.md` — bank/task/verifier authoring guide

## Task
Create the small-feature edge-case-trap task pack (stdlib-only Python), added to the `humble-vs-super-v1` bank:
- Two feature tasks (`feature-csv-coalesce`, `feature-retry-backoff`), each sized ABOVE the worth-loading bar —
  operationalized as: the reference solution spans >= 2 files OR requires a reproducing test / written plan
  before the change, so the model's own dispatch rationally loads a discipline rather than free-handing it.
- Each task dir: `task.toml` (`id`, `instruction`, `[limits] trial_timeout_s`, `max_turns` sized for the
  longest allow-Task arm, `[verify] entry = "verify.py"`), `fixtures/` (the starting project + the spec the
  feature must satisfy), and a blind `verify.py`.
- `verify.py` emits a flat JSON boolean dict: `behavior_correct` (a hidden suite passes), one boolean per named
  edge case (empty input, ragged/boundary, type coercion, zero-retry / jitter-bounds / error-propagation as
  appropriate), and `tests_present` (the candidate's own tests exercise the named edge cases).

## Constraints
- Edge cases must be genuine traps a rushed implementation misses (so `bare` sometimes fails). Stdlib only;
  verifier reads ONLY `argv[1]`, carries no scenario/arm identity, runs offline.
- These tasks are NOT holdout (the bank's holdout stays the single bug-fix task from PR06). Do not edit
  `bank.toml`'s holdout list.

## Starting file list
1. `tasks/humble-vs-super-v1/{feature-csv-coalesce,feature-retry-backoff}/` — `task.toml`, `fixtures/`, `verify.py`
2. `tests/test_verify_humble_super_feature.py` (stdlib-runnable)

## Definition of done
- [ ] Each verifier emits one boolean per named edge case (spec §7 acceptance).
- [ ] A reference solution passes all criteria; a deliberately naive solution fails at least one edge criterion
      — demonstrated in the unit test.
- [ ] `python tests/test_verify_humble_super_feature.py` exits 0; all quality gates pass.
