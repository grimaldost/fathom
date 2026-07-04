## Mode
plan -> implement (TDD) -> verify (small patches, test after each)

## Mandatory pre-read
- `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` — §4
- `src/fathom/cli.py` — the runner factory (`_default_runner_factory` or equivalent) and the existing
  loud-WARNING path for an unarmed/missing-inject treatment arm (model your warning on it)
- `src/fathom/scenario.py` — the `PluginsConfig.mount` field added in PR02 (depends_on PR02)
- `src/fathom/adapters/claude_cli.py` — `ClaudeCliRunner(plugin_dirs=...)` added in PR03 (depends_on PR03)

## Task
Wire mounted plugins from scenario to runner in the CLI factory:
- Read `scenario.plugins.mount` and pass it to `ClaudeCliRunner(plugin_dirs=...)`.
- Print a loud `WARNING` and flag the arm unarmed when a declared mount dir is missing or empty, mirroring the
  existing missing-inject warning (same failure class as the unarmed-treatment defect).

## Constraints
- Reuse the existing warning style/path; do not invent a new logging mechanism.
- A scenario with no `[plugins] mount` must behave exactly as today (no warning, no plugin dirs).

## Starting file list
1. `src/fathom/cli.py`
2. the CLI/factory test module (e.g. `tests/test_cli.py` / `tests/test_strategies.py` — match where the
   existing factory + inject-warning tests live)

## Definition of done
- [ ] A scenario naming a nonexistent mount dir produces the WARNING and marks the arm unarmed in the run log
      (spec §4 acceptance; test).
- [ ] A valid mount produces no warning and the dirs reach the runner (test).
- [ ] All quality gates pass.
