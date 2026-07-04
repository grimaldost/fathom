## Mode
plan -> author -> verify (bank authorship; tests validate the bank)

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 12 (entire section; it encodes pre-mortem blockers) + section 5 of `docs/specs/2026-06-10-fathom-v1-design.md`
- `docs/adr/0005-sealed-holdout-tasks.md`
- Engine series schema reference (read-only, outside this repo): `C:/Users/grima/Documents/pr-pilot-main/docs/series-toml-reference.md`

## Task
Author the `tasks/pr-pilot-v1/` bank per spec section 12: 3-5 realistic Python
tasks at the coordination threshold (multi-file feature/fix in a small fixture
codebase where decomposition into 3-5 PRs plausibly helps). Per task:
`task.toml` (stable id, instruction, limits — the series scenario gets a larger
trial-timeout override sized so one engine subagent allowance cannot exceed the
trial budget), a git-initializable `fixtures/` skeleton (a small working Python
project with passing baseline tests), a deterministic `verify.py` (reads ONLY
the result-view path argument; never git metadata or automation dirs; the
task's deliberately-failing acceptance checks live HERE, never in engine gate
commands), and the task's series assets: `series.toml` template, `prompts/`
with one prompt per series PR, and a review prompt. `bank.toml` marks exactly
one task holdout.

## Constraints
- Fixture baseline tests must PASS on the unmodified fixture (the engine's
  baseline gate sweep runs non-dry and strict); `verify.py` must FAIL on the
  unmodified fixture (acceptance not yet implemented). These coexist by
  construction — keep them in separate files.
- Tasks must be solvable by a competent agent in one long session AND
  decomposable — that comparison is the whole point.
- No task may require network access or repo-external state.

## Starting file list
1. `tasks/pr-pilot-v1/bank.toml`
2. `tasks/pr-pilot-v1/<task-id>/` x 3-5 (task.toml, fixtures/, verify.py, series.toml, prompts/, review prompt)
3. `tests/test_bank_pr_pilot_v1.py` — the bank-validation test

## Definition of done
- [ ] Every verifier passes on its reference solution and fails on the unmodified fixture (validation test stages both)
- [ ] Engine preflight passes against a staged fixture workspace for every task's series assets
- [ ] Baseline gate sweep passes non-dry on every unmodified staged fixture
- [ ] Exactly one holdout task in `bank.toml`
- [ ] `python tests/test_bank_pr_pilot_v1.py` exits 0; all quality gates pass
