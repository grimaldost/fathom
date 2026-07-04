## Mode
plan -> implement (TDD) -> verify (small patches, test after each)

## Mandatory pre-read
- `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` — §2
- `src/fathom/scenario.py` — model your change on the existing `ContextConfig` / `[context] inject` field and the
  conditional-hashing pattern in `_resolved_to_dict` and `_tools_to_dict` (included-only-when-non-empty)
- `docs/adr/0002-*` (append-only ledger; `config_hash` is in the resume key)

## Task
Add a `[plugins] mount = [...]` scenario field and fold the mounted plugin set into `config_hash`. Mirror the
existing `[context] inject` mechanism exactly:
- Add `PluginsConfig(mount: tuple[str, ...] = ())` to `ScenarioConfig` and `ResolvedScenario`.
- In `load_scenario`, parse `[plugins] mount` and absolutize each path relative to the scenario file (as
  `context.inject` is absolutized).
- In `resolve_scenario`, compute `(name, version, tree_sha)` per mounted dir. `name`/`version` come from the
  plugin's `.claude-plugin/plugin.json`. `tree_sha` is the `git write-tree` of the plugin subtree at its pinned
  commit, computed over tracked files only (ignore `__pycache__`, `.venv`, `.git`) so incidental writes never
  fork the ledger.
- In `_resolved_to_dict`, include a `"plugins"` key **only when `mount` is non-empty** (exactly like the
  `inject`/`allowed` conditionals), so scenarios without a mount keep their hashes unchanged.

## Constraints
- Stdlib only; resolution stays injectable (no real git calls in unit tests — stub the tree-sha resolver like
  the existing `ScenarioResolver` stubs).
- Absent `[plugins]` and an empty `mount` must be the same effective config (no hash shift).

## Starting file list
1. `src/fathom/scenario.py`
2. `tests/test_scenario.py` (stdlib-runnable)

## Definition of done
- [ ] A scenario with a `[plugins] mount` hashes differently from one without (test).
- [ ] Absent-mount scenarios keep the committed `pr-pilot-v1` and `skill-pyeng-v1` config_hashes byte-identical
      — assert against the known-good hashes (spec §2 acceptance; regression test).
- [ ] Changing a plugin's `tree_sha` changes the hash (test with a stub resolver).
- [ ] `python tests/test_scenario.py` exits 0; all quality gates pass.
