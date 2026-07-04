## Mode
plan -> implement (TDD) -> verify

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 6 + the Context engine-facts paragraph (read both fully; they encode pre-mortem blockers)
- Engine source for reference (read-only, outside this repo): `/path/to/pr-pilot-main/src/pr_pilot/` (config.py, claude.py, tracker.py, series.py)

## Task
Implement `src/fathom/strategies/base.py` (`StrategyExecutor` typing.Protocol —
`run_trial(task, workspace, scenario, runner) -> TrialResult` with 1..N run
records), `src/fathom/strategies/single_session.py` (exactly one Runner call),
and `src/fathom/strategies/series.py` per spec section 6. The series
executor: instantiate the task's committed series assets OUTSIDE the trial
workspace (sibling temp dir; absolute paths in the instantiated series.toml;
engine outputs dir outside the workspace too); PIN every engine config field —
non-bypass permission_mode, model/effort/budgets mapped from the resolved
scenario, parallel off (the engine's defaults include bypassPermissions and
must never be accepted); invoke the scenario's pinned invocation command with
the trial workspace as cwd and the trial's `CLAUDE_CONFIG_DIR` exported;
materialize one run record per `SUBAGENT_COMPLETE` tracker event whose run id
matches this invocation (ignore IMPL_META echoes and foreign run ids; mark the
weaker series pin level); classify engine failures before scoring (auth /
usage-limit signatures, retry-exhausted reasons -> infrastructure error);
terminate the ENTIRE engine process tree on trial timeout (Windows:
`taskkill /T` or equivalent — killing only the direct child orphans the
grandchild `claude`).

## Constraints
- Stdlib only. Engine subprocess injectable; all tests stubbed — no real engine runs.
- This module is the ONE sanctioned non-adapter model-call path (documented
  exception in the spec's Invariants) — keep the boundary tight: no other new
  module may spawn anything.

## Starting file list
1. `src/fathom/strategies/__init__.py`, `base.py`, `single_session.py`, `series.py`
2. `tests/test_strategies.py` (stdlib-runnable) + tracker.jsonl fixture (SUBAGENT_COMPLETE + IMPL_META echo + foreign-run-id event)

## Definition of done
- [ ] Single-session: exactly one run per trial
- [ ] Emitted series.toml: sibling dir, absolute paths, outputs outside workspace, non-bypass permission mode, scenario-mapped model/effort/budgets
- [ ] Isolation env passed through; records only from matching SUBAGENT_COMPLETE events
- [ ] Genuine nonzero engine exit -> trial errored; stubbed usage-limit failure -> infrastructure (not scored)
- [ ] Simulated timeout terminates the whole process tree, no orphan (test with a stub process tree)
- [ ] `python tests/test_strategies.py` exits 0; all quality gates pass
