# Contributing

## Setup

Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/). Then:

```sh
uv sync
uv run pytest
```

The core under `src/fathom/` imports **stdlib only** — every `tests/test_*.py` also runs as
plain `python tests/test_<name>.py`. uv manages dev tooling (ruff, pytest) only; do not add a
third-party dependency to the core without an ADR.

## Gates (all must pass before any commit)

```sh
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run fathom smoke     # real spawns (costs cents); mandatory before any paid matrix and at every resume
```

CI (`.github/workflows/ci.yml`) runs the first three. `fathom smoke` needs a real Claude
credential, so it stays a manual gate — run it whenever a change touches spawning, isolation,
or the series engine boundary; it has caught real shipped regressions that the unit suite
(which stubs the engine) cannot see.

## Invariants (the things a change must not break)

Each has an ADR under `docs/adr/`; the build spec's enforcement table
(`docs/specs/2026-06-10-fathom-v1-build.md`) says how each is checked.

- **Append-only ledger (ADR-0002).** Never edit `ledger/*.jsonl` — by hand or in code. No code
  path rewrites a line; reports regenerate from the ledger. Invalid runs are *archived* to
  `ledger/archive/`, never deleted. Task IDs are stable; any change to a task's instruction,
  fixtures, or verifier bumps the bank's `dataset_version` (it is part of the resume key).
- **Blind scoring (ADR-0003).** Verifiers receive only the result-view path in `argv[1]` — no
  scenario identity in argv or env, no reading git metadata or engine artifacts. Judges see
  A/B-labeled outputs only. Economy joins *after* scoring.
- **Spawn isolation (ADR-0004).** Spawns run with a credential-only temp `CLAUDE_CONFIG_DIR`,
  headless default-deny, explicit allowlists — never `bypassPermissions` or
  `--dangerously-skip-permissions`. All model calls go through `Runner` adapters (ADR-0001);
  the one sanctioned exception is the series-engine subprocess in
  `src/fathom/strategies/series.py`.
- **Stdlib core.** `typing.Protocol` at the seams (`Runner`, `StrategyExecutor`).

## Adding a bank or an arm

Schemas (flat-TOML scenario, `bank.toml`, `task.toml`, the `verify.py` contract) are in
`CLAUDE.md` → "Authoring banks / scenarios"; the parsers in `src/fathom/scenario.py` and
`src/fathom/taskbank.py` are the source of truth.

1. Author the bank under `tasks/<bank>/` and its arms under `scenarios/<bank>/`.
2. Validate free of charge before any spend: the bank-validation triad — every verifier
   **fails** on the unmodified fixture, **passes** on a reference solution, and the baseline
   gates run green — plus `uv run fathom run <bank> --dry-run --scenarios-dir scenarios/<bank>`.
3. `uv run fathom smoke`, then a small `--limit` pilot to check the per-trial cost before the
   full matrix.
4. Mark a sealed holdout in `bank.toml` where the bank feeds a tuning loop (ADR-0005).
5. After the run: commit the ledger, add the analysis row to `docs/STATUS.md`, and write the
   run notes / findings report under `docs/reports/`.

## Docs conventions

- `docs/README.md` maps the tree. Live indexes (`STATUS.md`, the core specs) are kept current;
  dated specs and reports are **records** — corrected with dated banners, never silently
  rewritten (same discipline as the ledger).
- Analysis run notes and findings go to `docs/reports/`. Dogfooding feedback about fathom
  itself goes to the local, gitignored `feedback/` dir — it is working input for triage, not
  documentation, and never lands under `docs/`.
- `report/` is generated output (gitignored); never commit scorecards.

Substantial changes to the harness follow the keel/convoy governed-series method bound in
`docs/method/method-bindings.md` (spec → Definition-of-Ready with a pre-mortem → PR series →
Definition-of-Done); a one-file fix does not need the ceremony.
