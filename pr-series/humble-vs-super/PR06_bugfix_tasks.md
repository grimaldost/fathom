## Mode
plan -> implement (TDD) -> verify (small patches, test after each)

## Mandatory pre-read
- `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` — §6
- `tasks/skill-pyeng-v1/modernize-timeflow/verify.py` — model: blind (`argv[1]` only), layout-agnostic module
  load via `importlib`, JSON booleans to stdout
- `tasks/pr-pilot-v1/README.md` — the bank/task/verifier authoring guide
- `docs/adr/0003-*` (blindness), `docs/adr/0005-sealed-holdout-tasks.md` (the holdout)

## Task
Create the `humble-vs-super-v1` bank foundation and the bug-fix/regression task pack (stdlib-only Python):
- `tasks/humble-vs-super-v1/bank.toml`: `name`, `dataset_version = "1"`, `holdout = ["fix-cache-eviction-bug"]`.
- Two working bug-fix tasks (`fix-offbyone-paginator`, `fix-tz-dst-normalize`) and the sealed holdout
  (`fix-cache-eviction-bug`). Each task dir has: `task.toml` (`id`, `instruction`, `[limits] trial_timeout_s`,
  `max_turns`, `[verify] entry = "verify.py"`), a `fixtures/` project carrying a planted SUBTLE bug plus a
  shipped passing test suite that does NOT cover the bug, and a blind `verify.py`.
- Each `verify.py` emits a flat JSON boolean dict: `fix_correct` (a HIDDEN test covering the bug passes),
  `no_regression` (the shipped suite still passes), and `regression_test_present` — the candidate's new test
  must FAIL against the stashed original buggy source and PASS against the candidate's source (stash the
  original inside the task dir; swap it in, run, swap back; layout-agnostic discovery as in skill-pyeng).
- Set `[limits] max_turns` / `trial_timeout_s` sized for the LONGEST (allow-Task subagent) arm so discipline
  arms are not truncated.

## Constraints
- Bugs must be subtle enough that a naive guess passes the obvious case but fails the hidden one (so `bare`
  sometimes fails — the discrimination requirement). Stdlib only; verifier runs offline, reads ONLY `argv[1]`,
  carries no scenario/arm identity.
- The verifier itself gets stdlib unit tests; do NOT require a live bank wiring to test it.

## Starting file list
1. `tasks/humble-vs-super-v1/bank.toml`
2. `tasks/humble-vs-super-v1/{fix-offbyone-paginator,fix-tz-dst-normalize,fix-cache-eviction-bug}/` —
   `task.toml`, `fixtures/`, `verify.py`, stashed original
3. `tests/test_verify_humble_super_bugfix.py` (stdlib-runnable)

## Definition of done
- [ ] On the untouched fixture the verifier reports `fix_correct=false` (spec §6 acceptance).
- [ ] On a reference correct fix the verifier reports every criterion true.
- [ ] `regression_test_present` distinguishes a real regression test from none (unit-tested via the swap logic).
- [ ] `python tests/test_verify_humble_super_bugfix.py` exits 0; all quality gates pass.
