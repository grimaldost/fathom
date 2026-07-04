# fathom

Scenario-blind tool-effectiveness evals. fathom measures whether an AI coding tool is worth using by scoring task results blind to scenario, comparing different execution strategies (bare agent, single long session, convoy multi-PR series), and joining performance with economy metrics into longitudinal verdicts.

New here? **[`CLAUDE.md`](CLAUDE.md)** is the operating manual (run recipe, as-built schemas, invariants).

## Run an eval

An analysis is a scenario matrix run against a task **bank**, scored into a **scorecard**:

```sh
uv run fathom smoke                       # real-spawn isolation gate — run before any paid matrix
uv run fathom run <bank> --dry-run        # plan + USD ceiling, spawns nothing
uv run fathom run <bank> --repeats 3      # the real (paid) matrix; resumable — re-invoking skips done trials
uv run fathom report <bank>               # render report/scorecard-<bank>.md from the ledger
```

A bank that ships its own arms needs `--scenarios-dir` (the run globs `<dir>/*.toml` non-recursively):

```sh
uv run fathom run skill-pyeng-v1 --scenarios-dir scenarios/skill-pyeng --repeats 3
```

Banks live under `tasks/` (`ls tasks/`); the reference bank is `skill-pyeng-v1` (arms in `scenarios/skill-pyeng/`). The `series` arm (`scenarios/series.toml`) drives the **convoy** multi-PR engine. Results land in `ledger/<bank>.jsonl` (committed) and `report/scorecard-<bank>.md` (gitignored). Other flags: `--limit N`. Full recipe, cost rails, and authoring schemas are in [`CLAUDE.md`](CLAUDE.md).

## Gate commands

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest`  — core tests are stdlib-runnable, e.g. `python tests/test_scenario.py`
- `uv run fathom smoke`

## Development

```sh
uv sync
uv run pytest
uv run ruff format .
uv run ruff check .
```

## Docs

- **[`CLAUDE.md`](CLAUDE.md)** — operating manual: run recipe, as-built scenario/task/bank schemas, the four invariants.
- **[`docs/STATUS.md`](docs/STATUS.md)** — analyses run, open defects, next steps.
- **[`docs/specs/`](docs/specs/)** — the [design](docs/specs/2026-06-10-fathom-v1-design.md) (architecture + module map) and [build](docs/specs/2026-06-10-fathom-v1-build.md) (per-section spec, invariants/enforcement) specs.
- **[`docs/adr/`](docs/adr/)** — the load-bearing decisions (vendor-abstract runner, append-only ledger, blind scoring, spawn isolation, sealed holdouts).
- **[`docs/specs/2026-07-03-series-engine-contract.md`](docs/specs/2026-07-03-series-engine-contract.md)** — the engine-agnostic contract the `series` arm drives (implemented by convoy).
- **[`docs/feedback/`](docs/feedback/)** — per-run notes: the longitudinal record + dogfooding findings.
