## Mode
plan -> implement (TDD) -> verify

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 5
- `docs/adr/0001-subscription-cli-behind-vendor-abstract-runner.md`, `docs/adr/0004-vendor-claude-runner-core.md`
- Vendor source (read-only, outside this repo): `C:/Users/grima/Documents/craft-collection/evals/harness/claude_runner.py`

## Task
Implement `src/fathom/adapters/base.py` (the `Runner` typing.Protocol —
`execute(prompt, workspace, scenario) -> RunRecord` — and the `RunRecord`
dataclass: tokens in/out/cache, num_turns, duration_s, cost_usd_est, exit
status incl. an `infrastructure` classification, resolved model id, cli
version) and `src/fathom/adapters/claude_cli.py` by VENDORING the proven core
from the source above per ADR-0004: temp `CLAUDE_CONFIG_DIR` containing only
the copied credential; headless default-deny — the command carries NO
`--permission-mode` and NO `--dangerously-skip-permissions`; explicit
`--allowed-tools`/`--disallowed-tools` from the scenario; `--effort` resolved
from the scenario; `--output-format stream-json` parsing with partial-stream
tolerance on timeout; retry with cap; per-spawn `--max-budget-usd` and
`--max-turns`. Classify auth failures and subscription usage-limit responses
as infrastructure errors (never scored, never burning trial error-retries).

## Constraints
- Stdlib only. Subprocess boundary injectable so every test runs with a stub —
  no real spawns in this PR (that is the smoke gate's job, spec section 11).
- Keep vendored behavior recognizable; adapt names/shape to the protocol, do
  not redesign retry/parse logic.

## Starting file list
1. `src/fathom/adapters/__init__.py`, `src/fathom/adapters/base.py`, `src/fathom/adapters/claude_cli.py`
2. `tests/test_adapter_claude_cli.py` (stdlib-runnable) + stream-json fixtures (complete + truncated) under `tests/fixtures/`

## Definition of done
- [ ] Argv assertion: absence of both permission flags; exact allow/disallow lists; resolved `--effort` present
- [ ] Isolation env assertion: temp config dir contains only the credential copy
- [ ] Complete + truncated stream fixtures parse into RunRecords (usage/turns/duration/cost)
- [ ] Retry cap honored; auth-failure and usage-limit fixtures classified infrastructure
- [ ] `python tests/test_adapter_claude_cli.py` exits 0; all quality gates pass
