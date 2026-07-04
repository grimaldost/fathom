## Mode
plan -> implement -> verify (this PR's tests include REAL spawns)

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 11
- `docs/adr/0004-vendor-claude-runner-core.md`
- Port source (read-only, outside this repo): `/path/to/craft-collection/evals/harness/smoke.py`

## Task
Implement `src/fathom/smoke.py` wired to `fathom smoke` per spec section 11, porting
the real-spawn assertions: (1) a spawn under the credential-only temp config is
authenticated and completes; (2) a disallowed tool call is refused under
default-deny; (3) stream parsing detects activity; plus (4) the engine-boundary
assertion — a minimal one-PR engine invocation against a scratch workspace
confirms the section-6 pinned non-bypass permission mode reaches the engine's
spawned CLI invocation (no bypass flag in the spawn; a PATH-shim `claude`
recording argv is an acceptable mechanism for this assertion). Exit nonzero on
any violation; support a forced-fail flag to demonstrate the nonzero path.

## Constraints
- Stdlib only. Real spawns are expected here (keep them minimal and cheap:
  tiny prompts, low budgets); the engine-boundary check must NOT spend real
  model tokens if the shim mechanism is used.
- Unit-test the assertion plumbing with stubs; the real-spawn path is executed
  manually via `fathom smoke` and its output pasted into the PR summary.

## Starting file list
1. `src/fathom/smoke.py` (+ wiring in `src/fathom/cli.py`)
2. `tests/test_smoke_logic.py` (stdlib-runnable; stubs only)

## Definition of done
- [ ] `fathom smoke` runs all four assertion groups and reports each
- [ ] Forced-fail flag demonstrates nonzero exit
- [ ] Real `fathom smoke` run output included in the PR summary (all passing)
- [ ] `python tests/test_smoke_logic.py` exits 0; all quality gates pass
