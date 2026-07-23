# series.toml skeleton

The `series.toml` schema is the **engine-agnostic series contract**
(`docs/specs/2026-07-03-series-engine-contract.md` §3; convoy's own format doc is
`docs/design/02-formats.md` in its repo). fathom **regenerates** this file per trial —
rewriting `[paths]` to absolute, pinning `[governance]`, and stripping any per-PR
`model`/`tier`/`effort`/`budget` override — so keep it to the contract's plain value types.

```toml
[series]
id = "<series-name>"
version = "1"

[branches]
base = "main"                      # fathom stages the fixture here
integration = "<topic>/integration"  # the engine leaves this checked out — fathom scores it

[paths]
prompts = "prompts"                # fathom rewrites to an absolute path outside the workspace
outputs = "outputs"                # spawns.jsonl telemetry lands here

[governance]                       # fathom PINS these from the resolved scenario
model = "claude-opus-4-8"
effort = "high"
permission_mode = "default"        # never bypassPermissions (§6 parity)
timeout_seconds = 1800

[governance.budgets]               # per-phase USD ceilings — TOML numbers, not strings.
implementation = 20.0              # a spawn that exceeds its cap halts un-integrated
review = 5.0                       # (outcome="budget" / exit 4, §7) rather than overspending —
fix = 3.0                          # this IS the wave-budget guard (no separate [budget] block).

[review]
blocking = false
max_fix_attempts = 0

[[checks]]                         # a blocking red stops the phase (never silently skipped)
name = "tests"
run = "python -m pytest -q"
blocking = true
independent = false

# Per-PR definitions: the DAG. NO per-PR model/tier/effort/budget — fathom strips them
# (`_PER_PR_PINS`) before spawning so an arm can't silently use a stronger model per PR.
# (convoy itself now ACCEPTS per-PR model/tier/effort — its ADR-0007 governance — and
# rejects only budget/budgets, so the parity guard here is fathom's strip, not convoy's.)
[[prs]]
id = "PR01"
branch = "<topic>/pr01"
prompt = "PR01.md"                 # relative to [paths].prompts
phase = "1"
depends_on = []

[[prs]]
id = "PR02"
branch = "<topic>/pr02"
prompt = "PR02.md"
phase = "2"
depends_on = ["PR01"]
```

## Wave budget

There is no wave-level `[budget]`/drift block that any engine reads. Cost is bounded per
spawn by `[governance.budgets]` (which fathom pins): when a spawn exceeds its cap, convoy
halts that PR **un-integrated** and reports `outcome = "budget"` / exit 4 (series contract §7).
fathom records that trial `errored` (excluded from the pass rate, re-runnable after raising
the cap) rather than scoring truncated work — the wave never quietly blows past its forecast.
