## Mode
plan -> implement -> verify (small patches, test after each)

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 1 (your section) + Gate commands

## Task
Scaffold the fathom Python project exactly as spec section 1 describes: uv project,
src-layout (`src/fathom/` with empty `__init__.py`), ruff and pytest configured in
`pyproject.toml`, a placeholder stdlib-runnable test, `.gitignore` covering
`report/`, `.pr-outputs/`, `.worktrees/`, and workspace temp dirs, and a README
stub naming fathom's purpose (scenario-blind tool-effectiveness evals) and the
exact gate commands. Commit `uv.lock` (gates run `uv sync --frozen`).

## Constraints
- Python >= 3.12; dev-dependencies only `ruff` and `pytest` (core stays stdlib).
- The placeholder test must pass under BOTH `uv run pytest` and plain
  `python tests/test_placeholder.py` (stdlib-runnable pattern: plain asserts in
  functions plus a `__main__` block that runs them).
- No unrelated files, no CI config (not in scope), no src code beyond `__init__.py`.

## Starting file list
Only create/modify:
1. `pyproject.toml`, `uv.lock`
2. `src/fathom/__init__.py`
3. `tests/test_placeholder.py`
4. `.gitignore`, `README.md`

## Definition of done
- [ ] `uv sync --frozen` succeeds on a fresh checkout
- [ ] All three gate commands pass (`ruff format --check .`, `ruff check .`, `pytest`)
- [ ] `python tests/test_placeholder.py` exits 0
- [ ] README names the gate commands verbatim
