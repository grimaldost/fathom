## Mode
plan -> implement (TDD) -> verify (small patches, test after each)

## Mandatory pre-read
- `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` — §5
- `src/fathom/smoke.py` — the existing real-spawn check groups and the `--append-system-prompt-file` injection
  canary (model your mount check on that real-spawn pattern); note its credential-only isolated config
- `src/fathom/adapters/claude_cli.py` — `--plugin-dir` from PR03 (depends_on PR03, PR04)

## Task
Add a smoke check group that proves a `--plugin-dir`-mounted plugin's skills are AVAILABLE (mounted) in a
headless `-p` spawn, and that a control spawn WITHOUT the mount lacks them:
- Ship a tiny canary plugin under `tests/fixtures/canary-plugin/` (`.claude-plugin/plugin.json` +
  `skills/<canary>/SKILL.md`) with a uniquely-named skill.
- Treatment spawn: mount it via `--plugin-dir`; assert the spawn's init event lists the canary skill in its
  `skills` array.
- Control spawn: same prompt, no `--plugin-dir`; assert the canary skill is ABSENT.
- This proves MOUNT/availability, not auto-firing. Name the group accordingly; do not claim it proves
  triggering. The assertion reads the init event (model-agnostic), so the smoke model (haiku) is fine.

## Constraints
- This is a REAL-spawn check (like the existing smoke groups) — keep it within the smoke harness, not the
  stdlib unit suite. The logic helpers (parsing init `skills`) get stdlib unit tests in `tests/test_smoke_logic.py`.
- Isolation unchanged: credential-only temp config, default-deny.

## Starting file list
1. `src/fathom/smoke.py`
2. `tests/fixtures/canary-plugin/.claude-plugin/plugin.json`, `tests/fixtures/canary-plugin/skills/<canary>/SKILL.md`
3. `tests/test_smoke_logic.py` (stdlib-runnable: the init-`skills` parse/assert helper)

## Definition of done
- [ ] `uv run fathom smoke` includes and passes the new mount/available group (spec §5 acceptance).
- [ ] The check fails loudly (asserted in a unit test of the helper) when a mounted plugin's skills are absent
      from the init event.
- [ ] Stdlib helper test passes via plain `python tests/test_smoke_logic.py`; all quality gates pass.
