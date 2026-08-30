# Contributing

## Setup

Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/). Then:

```sh
uv sync
uv run pytest
```

The core under `src/fathom/` imports **stdlib only** — every `tests/test_*.py` also runs as
plain `python tests/test_<name>.py`. uv manages dev tooling (ruff, pytest, pre-commit) only; do not add a
third-party dependency to the core without an ADR.

## Gates (all must pass before any commit)

```sh
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run fathom reconcile # free, spawns nothing — every fact this repo derives twice must agree (exit 13 = it doesn't)
uv run fathom smoke     # real spawns (costs cents); mandatory before any paid matrix and at every resume
```

CI (`.github/workflows/ci.yml`) runs the first three on ubuntu and windows, with
`uv lock --check` before sync (a stale lock is invisible to any test: `uv run` re-locks
before pytest could read the file). `fathom reconcile` is exercised inside pytest via
`tests/test_reconcile.py`, so CI holds it too; run it directly for the per-check report.
`fathom smoke` needs a real Claude credential, so it stays a manual gate — run it whenever
a change touches spawning, isolation, or the series engine boundary; it has caught real
shipped regressions that the unit suite (which stubs the engine) cannot see.

### The commit lane

The fast half of the gates runs before every commit, once per clone you run:

```sh
git config core.hooksPath tools/git-hooks
```

Not `pre-commit install` — that writes a hook invoking the bare `pre-commit` shim, which at
least one machine this repo is developed on blocks, so the hook silently never runs; the
tracked hooks call `uv run python -m pre_commit` instead. The lane runs ruff format + check,
`fathom reconcile` whenever `ledger/` or `docs/reports/` is staged, and a commit-msg stage
that enforces conventional-commit subjects and rejects AI-attribution trailers. Bypass a
single commit with `git commit --no-verify` when you mean to; CI runs the full set
regardless.

### The changelog moves with the change

A PR whose diff touches `src/`, `tools/`, `commands/`, `mcp/` or `skills/` fails CI unless
`CHANGELOG.md` moves with it (an `[Unreleased]` entry) or a commit in the range carries a
`Changelog: not needed (<reason>)` line (`tools/changelog_currency.py`).

## Invariants (the things a change must not break)

The first three have an ADR under `docs/adr/`; stdlib core has none — every core module and test
imports stdlib only, so `python tests/test_<name>.py` runs without uv; that is a convention, not a
CI gate (CI runs the suite under `uv run pytest`). The build spec's enforcement table
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
`skills/fathom-eval/reference/authoring.md`; the parsers in `src/fathom/scenario.py` and
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

## Releasing

A release is a metadata-only commit on its own branch, merged via PR: roll `[Unreleased]`
into a dated `## [X.Y.Z]` heading (argue the bump class in the heading's prose — this
changelog's convention), bump the version in `pyproject.toml` and
`.claude-plugin/plugin.json`, and run `uv lock`. The `version-sites` reconciliation holds
the three version sites together, so a half-performed bump fails the suite. Keep feature
work out of the release commit — it keeps bisect and per-commit review meaningful across
the boundary.

Tag the release PR's **merge commit**, with an annotated tag:

```sh
git tag -a vX.Y.Z <release-merge-commit> -m "fathom X.Y.Z"
git push origin vX.Y.Z
```

The plugin runtime re-pulls an installed copy only when the manifest's version moves, so a
release is also what delivers plugin-surface changes to installed consumers.

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
