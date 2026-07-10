# fathom

Scenario-blind tool-effectiveness evals. fathom measures whether an AI coding tool is worth
using: it runs real coding tasks under different tool configurations and execution strategies
(**arms**), scores the results **blind to which arm produced them**, and joins quality with
economy (tokens, turns, wall-clock, estimated USD) into longitudinal verdicts — *worth using*,
*which direction to improve*, *did the new version regress*.

It has been used to answer questions like: does force-loading a Python-engineering skill
change what an agent ships? Is plugin A more effective than plugin B, and at what cost? Is a
multi-PR orchestration engine worth its overhead? Is a complexity→model-tier routing map
well-tuned? The verdicts so far are indexed in [`docs/STATUS.md`](docs/STATUS.md).

## How it works

```
taskbank → scenario (resolve + config_hash) → Runner (claude-cli adapter) → StrategyExecutor
        → grading (verifier-first, pairwise judge) → append-only ledger → scorecard report
```

- A **bank** (`tasks/<bank>/`) holds real coding tasks: a fixture repo, an instruction, and a
  deterministic `verify.py` that emits per-criterion booleans.
- An **arm** (`scenarios/*.toml`) pins everything about one way of attempting the task — model,
  effort, tool allowlist, injected context, mounted plugins, execution strategy (one session,
  gated session, or a multi-PR series driven by an external engine). The resolved configuration
  is content-hashed (`config_hash`), which makes runs resumable and history fork-proof.
- Each **trial** spawns a headless, credential-isolated `claude` CLI in a temp workspace,
  default-deny permissions, never `bypassPermissions`.
- **Grading is blind**: the verifier sees only the final workspace (scenario identity stripped
  from the result view, argv, and env); economy data joins *after* scoring.
- Every result is appended to a **committed ledger** (`ledger/<bank>.jsonl`) — the longitudinal
  record. Scorecards are regenerated from it, never edited.

Four load-bearing invariants, each with an ADR under [`docs/adr/`](docs/adr/): blind result-only
scoring (ADR-0003), the append-only ledger (ADR-0002), spawn isolation (ADR-0004), and a
vendor-abstract runner (ADR-0001). The core under `src/fathom/` is stdlib-only.

## Run an eval

An **analysis** = a scenario matrix run against a task bank, scored into a scorecard:

```sh
uv run fathom smoke                       # real-spawn isolation gate — run before any paid matrix
uv run fathom run <bank> --dry-run        # plan + USD ceiling, spawns nothing
uv run fathom run <bank> --repeats 3      # the real (paid) matrix; resumable — re-invoking skips done trials
uv run fathom report <bank>               # render report/scorecard-<bank>.md from the ledger
```

A bank that ships its own arms needs `--scenarios-dir` (the run globs `<dir>/*.toml`
non-recursively — without it the run silently uses the default arms):

```sh
uv run fathom run skill-pyeng-v1 --scenarios-dir scenarios/skill-pyeng --repeats 3
```

Cost rails: a per-trial ceiling is printed before anything spawns; `--dry-run` and `--limit N`
exist on every entry point; `--max-budget-usd` caps each spawn; a full matrix has historically
cost ~$15–45. Results land in `ledger/<bank>.jsonl` (committed) and `report/scorecard-<bank>.md`
(gitignored, regenerable). Read the scorecard's **Per-Criterion Pass Rates** table for the
discriminating signal, not just the headline pass rate.

Authoring schemas (bank / task / scenario / `verify.py`) and the full recipe live in
[`CLAUDE.md`](CLAUDE.md) — the operating manual.

## Repository layout

| Path | What it is |
|---|---|
| `src/fathom/` | The harness: CLI, ledger, scenario/bank loaders, adapters, strategies, grading, report. Stdlib-only. |
| `tasks/<bank>/` | Task banks: fixtures, instructions, verifiers (some vendor plugin snapshots as test subjects). |
| `scenarios/` | Arm definitions (flat TOML), grouped per bank in subdirectories. |
| `ledger/` | **Committed** append-only results; `ledger/archive/` holds invalidated runs (archived, never deleted). |
| `report/` | Generated scorecards — gitignored; regenerate with `uv run fathom report <bank>`. |
| `docs/` | Specs, ADRs, method kit, per-analysis reports, status. Map: [`docs/README.md`](docs/README.md). |
| `pr-series/` | PR briefs + series.toml of the governed series that built fathom itself (method artifacts). |
| `tests/` | Stdlib-runnable unit tests (also run via `uv run pytest`). |
| `skills/`, `commands/`, `mcp/`, `.claude-plugin/` | The Claude Code plugin surfaces — see [`README-plugin.md`](README-plugin.md). |
| `feedback/` | Local dogfooding feedback reports — gitignored, not part of the repo. |

## Docs

- [`docs/README.md`](docs/README.md) — map of the whole docs tree and of every analysis record.
- [`docs/STATUS.md`](docs/STATUS.md) — analyses run (with verdicts), open items, next steps.
- [`docs/specs/2026-06-10-fathom-v1-design.md`](docs/specs/2026-06-10-fathom-v1-design.md) —
  architecture and module map; [`...-v1-build.md`](docs/specs/2026-06-10-fathom-v1-build.md) —
  build spec with the invariants/enforcement table.
- [`docs/specs/2026-07-03-series-engine-contract.md`](docs/specs/2026-07-03-series-engine-contract.md)
  — the engine-agnostic contract the `series` arm drives (implemented by
  [convoy](https://github.com/grimaldost/convoy)).
- [`CLAUDE.md`](CLAUDE.md) — operating manual: run recipe, as-built schemas, conventions.

## Development

```sh
uv sync
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run fathom smoke     # real spawns, costs cents — the go/no-go before any paid matrix
```

Core modules and their tests import stdlib only (`python tests/test_scenario.py` works without
uv); uv manages dev tooling. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the gates, the
invariants, and how to add a bank or an arm.

## License

[MIT](LICENSE).
