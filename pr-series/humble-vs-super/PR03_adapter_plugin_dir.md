## Mode
plan -> implement (TDD) -> verify (small patches, test after each)

## Mandatory pre-read
- `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` — §3
- `src/fathom/adapters/claude_cli.py` — model your change EXACTLY on the existing `append_system_prompt_file`
  wiring: `build_command(..., append_system_prompt_file=...)` and the `ClaudeCliRunner.__init__` /
  `execute` plumbing
- `docs/adr/0004-vendor-claude-runner-core.md` (spawn isolation; default-deny)

## Task
Add repeatable `--plugin-dir` support to the adapter:
- `build_command(..., plugin_dirs: Sequence[str] = ())` appends one `["--plugin-dir", d]` per dir, in order,
  after the existing flags. Empty -> no `--plugin-dir` token.
- `ClaudeCliRunner.__init__` gains a `plugin_dirs` parameter (default `()`), stored like
  `append_system_prompt_file`; `execute` passes the resolved scenario's mounted plugin dirs through to
  `build_command`. (The resolved-scenario field lands in PR02; until then accept the constructor param.)

## Constraints
- Pure command-assembly change; the injectable `Spawn` boundary keeps every test stub-only — NO real spawns.
- Do not add `--permission-mode` or `--dangerously-skip-permissions` (ADR-0004 default-deny is preserved); do
  not touch `make_isolated_config`.

## Starting file list
1. `src/fathom/adapters/claude_cli.py`
2. `tests/test_adapter_claude_cli.py`

## Definition of done
- [ ] `build_command(plugin_dirs=["A","B"])` emits `--plugin-dir A --plugin-dir B` in order; with none, no
      `--plugin-dir` token appears (spec §3 acceptance; stub-only tests).
- [ ] `ClaudeCliRunner` forwards configured plugin dirs into the assembled argv (test via the stub `Spawn`).
- [ ] All quality gates pass; no real `claude` invocation in tests.
