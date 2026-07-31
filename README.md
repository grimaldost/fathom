<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/fathom-hero-dark.svg">
  <img alt="fathom" src="assets/fathom-hero-light.svg" width="100%">
</picture>

[![ci](https://img.shields.io/github/actions/workflow/status/grimaldost/fathom/ci.yml?style=flat-square&labelColor=2A3238&label=ci)](https://github.com/grimaldost/fathom/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.12%2B-00666D?style=flat-square&labelColor=2A3238)](pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-00666D?style=flat-square&labelColor=2A3238)](LICENSE)

**Scenario-blind tool-effectiveness evals.** fathom measures whether an AI coding tool is worth
using: it runs real coding tasks under different tool configurations and execution strategies
(**arms**), scores the results **blind to which arm produced them**, and joins quality with
economy (tokens, turns, wall-clock, estimated USD) into longitudinal verdicts — *worth using*,
*which direction to improve*, *did the new version regress*.

It has been used to answer questions like: does force-loading a Python-engineering skill
change what an agent ships? Is plugin A more effective than plugin B, and at what cost? Is a
multi-PR orchestration engine worth its overhead? Is a complexity→model-tier routing map
well-tuned? The verdicts so far are indexed in [`docs/STATUS.md`](docs/STATUS.md).

## Run an eval

Requirements: Python ≥ 3.12, [uv](https://docs.astral.sh/uv/), the `claude` CLI on PATH with a
working subscription login (each spawn authenticates from a copy of your
`~/.claude/.credentials.json`), and a clone of this repository. fathom runs **inside its own
checkout** — `scenarios/`, `tasks/` and `ledger/` are resolved relative to the working directory.

```sh
git clone https://github.com/grimaldost/fathom && cd fathom
```

An **analysis** = a scenario matrix run against a task bank, scored into a scorecard:

```sh
uv run fathom smoke                       # real-spawn isolation gate — run before any paid matrix
uv run fathom run <bank> --dry-run        # plan + USD ceiling, spawns nothing
uv run fathom run <bank> --repeats 3      # the real (paid) matrix; resumable — re-invoking skips done trials
uv run fathom report <bank>               # render report/scorecard-<bank>.md from the ledger
```

`uv run python -m fathom …` is equivalent and is what the plugin surfaces use — prefer it on
Windows, where the generated `fathom.exe` console script can be blocked by Smart App Control
(os error 4551).

A bank that ships its own arms needs `--scenarios-dir` (the run globs `<dir>/*.toml`
non-recursively — without it the run silently uses the default arms):

```sh
uv run fathom run skill-pyeng-v1 --scenarios-dir scenarios/skill-pyeng --repeats 3
```

Cost rails: a per-trial ceiling is printed before anything spawns; `fathom run` takes `--dry-run`
and `--limit N`; `--max-budget-usd` caps each spawn; a full v1 matrix is ~$20–40. Results land in
`ledger/<bank>.jsonl` (committed) and `report/scorecard-<bank>.md` (gitignored, regenerable). Read
the scorecard's **Per-Criterion Pass Rates** table for the discriminating signal, not just the
headline pass rate.

The run recipe and repo conventions live in [`CLAUDE.md`](CLAUDE.md) — the operating manual; the
full as-built authoring schemas (bank / task / scenario / `verify.py`, plus the `config_hash`
resume mechanics) are in
[`skills/fathom-eval/reference/authoring.md`](skills/fathom-eval/reference/authoring.md).

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

Four load-bearing invariants, three of them with an ADR under [`docs/adr/`](docs/adr/): blind
result-only scoring (ADR-0003), the append-only ledger (ADR-0002), spawn isolation (ADR-0004),
and a stdlib-only core under `src/fathom/` — no ADR, and held by convention rather than a CI
gate: every core module and test imports stdlib only, so `python tests/test_<name>.py` runs
without uv. All model calls additionally go through a vendor-abstract `Runner` (ADR-0001).

## Repository layout

| Path | What it is |
|---|---|
| `src/fathom/` | The harness: CLI, ledger, scenario/bank loaders, adapters, strategies, grading, report. Stdlib-only. |
| `tasks/<bank>/` | Task banks: fixtures, instructions, verifiers (some vendor plugin snapshots as test subjects). |
| `scenarios/` | Arm definitions (flat TOML), grouped per bank in subdirectories. |
| `ledger/` | **Committed** append-only results; `ledger/archive/` holds invalidated runs (archived, never deleted). |
| `ledger-rg2x2/`, `streams-rg2x2/`, `scripts-rg2x2/` | The rg-2x2 side study (registry × gate, 2×2) over the `e1-*` banks — arms in `scenarios/rg-{data,debug,verif}/`, with their mounted plugin snapshots and inject brief in `scenarios/rg-assets/`. Its ledgers sit outside `ledger/` (`--ledger-dir` is the flag that puts them there); the raw spawn streams are `FATHOM_STREAM_DIR` captures; the scripts render the post-hoc activation / gate-compliance / footprint tables. No findings report yet. |
| `report/` | Generated scorecards — gitignored; regenerate with `uv run fathom report <bank>`. |
| `docs/` | Specs, ADRs, method kit, per-analysis reports, status. Map: [`docs/README.md`](docs/README.md). |
| `pr-series/` | PR briefs + series.toml of the governed series that built fathom itself (method artifacts). |
| `tests/` | Stdlib-runnable unit tests (also run via `uv run pytest`). |
| `skills/`, `commands/`, `mcp/`, `.claude-plugin/` | The Claude Code plugin surfaces — see [`README-plugin.md`](README-plugin.md). |
| `assets/` | The visual identity (hero, lockup, mark, social card) — see [`assets/README.md`](assets/README.md). |
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
- [`CLAUDE.md`](CLAUDE.md) — operating manual: run recipe, conventions, the abridged schemas.

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
