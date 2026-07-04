## Mode
plan -> implement (TDD) -> verify

## Mandatory pre-read
- `docs/specs/2026-06-10-fathom-v1-build.md` — section 4 + Context engine facts
- `docs/adr/0001-subscription-cli-behind-vendor-abstract-runner.md`

## Task
Implement `src/fathom/scenario.py` per spec section 4: parse `scenarios/*.toml`
(adapter, model, strategy, `effort`, tool source, limits); a ResolvedScenario
produced by a resolver that records pins — exact model id as later reported by
the CLI (field present, fillable at run time), tool repo git SHA for
`tools.source = "repo"`, and the explicit tool invocation command (e.g.
`uv run --project <repo> series-engine` — never a bare PATH lookup); `config_hash` =
sha256 over the canonicalized (sorted-keys JSON) resolved scenario including
the invocation command. Scenario may override per-task trial limits. Ship the
three committed scenario files under `scenarios/`: `bare.toml`,
`single-long-session.toml`, `series.toml` — all three declaring equal
`effort` values, the series one carrying `tools.source="repo"` pointing at
`C:/Users/grima/Documents/pr-pilot-main` and a larger trial-timeout override.

## Constraints
- Stdlib only. Resolution is injectable (stub resolver in tests; no real git/CLI calls).
- Hash must be insensitive to TOML key order and sensitive to every resolved pin.

## Starting file list
1. `src/fathom/scenario.py`
2. `scenarios/bare.toml`, `scenarios/single-long-session.toml`, `scenarios/series.toml`
3. `tests/test_scenario.py` (stdlib-runnable)

## Definition of done
- [ ] config_hash stable under key reordering; changes when any pin (incl. invocation command) changes
- [ ] Three scenario files parse and resolve against a stub resolver; equal `effort` asserted
- [ ] `python tests/test_scenario.py` exits 0; all quality gates pass
