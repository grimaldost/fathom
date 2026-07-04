## Mode
plan -> implement (TDD) -> verify

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 3
- `docs/adr/0005-sealed-holdout-tasks.md`

## Task
Implement `src/fathom/taskbank.py` per spec section 3: parse `bank.toml` (name,
dataset_version, holdout list) and per-task `task.toml` (stable id,
instruction, limits, verify entry) with `tomllib`; named-error rejection for
duplicate task ids and missing required fields; staging — copy a task's
`fixtures/` into a fresh temp workspace, `git init -b <base>` with the base
branch name an explicit required argument (never the host default), set
`core.autocrlf=false` on the staged repo, and commit the fixture content as the
initial commit.

## Constraints
- Stdlib only (`tomllib`, `shutil`, `subprocess` for git, `tempfile`).
- Holdout ids must reference existing tasks (named error otherwise).
- No knowledge of scenarios or runners leaks in — staging is scenario-agnostic.

## Starting file list
1. `src/fathom/taskbank.py`
2. `tests/test_taskbank.py` (stdlib-runnable) + minimal bank fixture under `tests/fixtures/`

## Definition of done
- [ ] Sample bank loads; duplicate-id and missing-field fixtures raise named errors
- [ ] Holdout list parsed and validated
- [ ] Staged workspace: git repo, pinned branch name, `core.autocrlf=false`, fixture content committed
- [ ] `python tests/test_taskbank.py` exits 0; all quality gates pass
