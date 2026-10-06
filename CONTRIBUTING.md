# Contributing

This repository is the fathom engine: the package under `src/fathom/`, its command line, the
Claude Code plugin (`.claude-plugin/`, `commands/`, `mcp/`, `skills/`) and the repository
tooling. It holds no task banks, arms or results; see
[Data stays out of this repository](#data-stays-out-of-this-repository).

## Setup

Python 3.12 or later and [uv](https://docs.astral.sh/uv/). Then:

```sh
uv sync
uv run pytest
```

The core under `src/fathom/` imports the standard library only, and so does every
`tests/test_*.py`, so each test file also runs as plain `python tests/test_<name>.py`. uv
manages development tooling (ruff, pytest, pre-commit) only. Do not add a third-party
dependency to the core without an ADR.

## Gates

All of these must pass before a commit. This is the one gate list: `README.md` and
`CLAUDE.md` point here rather than repeat it. It matches `.github/workflows/ci.yml`; a change
to the gates is made in both.

```sh
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run --with "fastmcp>=2.0" --with pytest python -m pytest mcp/test_server_schema.py
FATHOM_HOME= uv run fathom reconcile                # the engine checkout: version sites
uv run fathom --home examples/data-root reconcile   # the example data root
uv run fathom smoke --no-engine-boundary            # manual: real spawns, a few cents
```

`FATHOM_HOME=` in front of a command sets the variable to empty for that command alone, and
fathom reads an empty `FATHOM_HOME` as unset. In PowerShell, run `$env:FATHOM_HOME = $null`
first, which removes the variable for the rest of the session.

- `uv lock --check` comes first because no test can see a stale lock: `uv run` re-locks
  before pytest could read the file. CI runs it before `uv sync`.
- `pytest` collects `tests/` only. The MCP server's tests import `fastmcp`, which the core
  does not depend on, so they run as their own step with `fastmcp` added for that command
  alone. They check each tool's parameter descriptions and the command each tool runs.
- `fathom reconcile` is free and spawns nothing. Every fact the tree records twice must
  agree; exit 13 means one does not. It runs twice. At the engine root it holds the version
  sites (`pyproject.toml`, `.claude-plugin/plugin.json` and the newest `CHANGELOG.md`
  heading) to each other. Against `examples/data-root/` it checks that the example data root
  still reconciles: its ledger index, its rows' config hashes and its arm names. Exit 13 also
  covers a refusal before any check ran: a malformed `fathom.toml`, an unknown `--check`
  name, or a directory that is neither a data root nor an engine checkout.
- Both reconcile runs are written so that a developer's own `FATHOM_HOME` cannot redirect
  them. `FATHOM_HOME` comes before the working directory when fathom looks for a data root,
  and the engine checkout is used only when no data root is named or found. With the
  variable set, a plain `uv run fathom reconcile` at the engine root would check that
  developer's data root instead, where the version-sites check is skipped, so a half-done
  version bump could pass. The engine-root run therefore clears the variable, and the
  example run names its root with `--home`, which comes before `FATHOM_HOME`. CI and the
  pre-commit hooks do the same. The pytest suite needs neither: `tests/conftest.py` removes
  `FATHOM_HOME` before any test runs.
- `fathom smoke` makes tiny real spawns and needs a working `claude` login, so it stays
  manual and CI does not run it. Run it whenever a change touches spawning, isolation, the
  run lock or the series-engine boundary: the unit suite stubs every spawn and cannot see
  those regressions. Its engine-boundary check needs a data root with a series arm
  (`scenarios/series.toml`); the engine has none, so at the engine root it is skipped with
  `--no-engine-boundary`. For a change to that boundary, run
  `uv run --project <engine checkout> fathom --home <data root with a series arm> smoke`.
- `fathom verify-arming` is not a gate here. It proves a data root's own treatment arms on
  real spawns, costs money, and the engine has no arms.

CI (`.github/workflows/ci.yml`) runs every gate above except `fathom smoke`, on ubuntu and
windows. It also reconciles the example data root the two other ways a user reaches one:
named by `FATHOM_HOME`, and found from inside it (`uv run --project ../.. fathom reconcile`
in `examples/data-root/`, with `FATHOM_HOME` empty). Then three more checks:

- **The installed wheel.** The steps above import the source tree, so a file the wheel leaves
  out would pass them and be missing from every installed copy (the smoke canary plugin is
  package data). CI builds the wheel (`uv build --wheel -o dist`) and runs it in a
  throwaway environment that holds the wheel alone
  (`uv run --isolated --no-project --with <wheel> …`): from inside `examples/data-root/`,
  `fathom --version`, `fathom reconcile` and import checks; from a directory outside it,
  `fathom --home <example> reconcile` and `fathom --home <example> run example --dry-run`.
- **Changelog currency** (pull requests only); see below.
- **Workflow lint**: `zizmor` over `.github/workflows`.

`fathom reconcile` is also exercised inside pytest (`tests/test_reconcile.py`).

### Hooks

The fast half of the gates runs before every commit. Install the tracked hooks once per
clone:

```sh
git config core.hooksPath tools/git-hooks
```

Do not use `pre-commit install`. It writes a hook that invokes the bare `pre-commit`
console-script shim, and where an application-control policy blocks such shims the hook
silently never runs. The tracked hooks call `uv run python -m pre_commit` instead. The
pre-commit stage runs ruff format and check and, for the paths listed in
`.pre-commit-config.yaml`, the `fathom reconcile` runs and the pytest test that re-derives
the example data root's config hashes. Each hook that runs fathom clears `FATHOM_HOME` or
names its root with `--home`, for the reason given under the gates. The commit-msg stage
enforces conventional-commit subjects and rejects AI-attribution trailers. Skip a single
commit with `git commit --no-verify` when you mean to; CI runs the full set regardless.

### The changelog moves with the change

A pull request whose diff touches a harness path fails CI unless `CHANGELOG.md` moves with
it (an `[Unreleased]` entry) or a commit in the range carries a
`Changelog: not needed (<reason>)` line. Harness paths are `src/`, `pyproject.toml`,
`.claude-plugin/`, `commands/`, `mcp/`, `skills/` and `tools/`: what reaches an installed
copy, plus the tooling the gates run from. Docs, examples, tests, CI configuration and
`uv.lock` are exempt. The check is `tools/changelog_currency.py`.

## Invariants

A change must not break these. The first three have an ADR under `docs/adr/`; the build
spec's enforcement table (`docs/specs/2026-06-10-fathom-v1-build.md`) says how each is
checked. [`CLAUDE.md`](CLAUDE.md) describes them with the modules that hold them.

- **Append-only ledger (ADR-0002).** No code path rewrites or deletes a ledger line; reports
  regenerate from the ledger; invalid runs are archived, never deleted. New row fields are
  additive, and readers accept rows written before a field existed.
- **Blind scoring (ADR-0003).** Verifiers receive only the result-view path in `argv[1]`: no
  arm identity in argv or env, no git metadata, no engine artifacts. A verifier runs in an
  empty temporary working directory, not the data root, with an environment reduced to
  system variables, none of which names the data root. Judges see A/B-labelled outputs only.
  Cost data joins after scoring. The agent under test is kept from the same facts: trial
  spawns, the series engine and gate commands get no `FATHOM_*` variable, no launch-directory
  variable (`PWD`, `OLDPWD`) and no variable whose value names the data root (`PATH` loses
  only its entries there), and each trial spawn is given staged copies of the arm's
  `[context]` and `[plugins]` files, so its command line names no path in the data root.
  `CLAUDE.md` names the functions that do this.
- **Spawn isolation (ADR-0004).** Spawns run with a credential-only temporary
  `CLAUDE_CONFIG_DIR`, headless default-deny and explicit allow lists, never
  `bypassPermissions` or `--dangerously-skip-permissions`. All model calls go through
  `Runner` adapters (ADR-0001); the one sanctioned exception is the series-engine subprocess
  in `src/fathom/strategies/series.py`.
- **Standard-library core.** `typing.Protocol` at the seams (`Runner`, `StrategyExecutor`).
  A convention, not a CI gate.

## Data stays out of this repository

Task banks, arms, ledgers, analysis write-ups and status pages belong in a data root: a
separate directory, usually a private repository, marked by a `fathom.toml` with a
`[data_root]` table. `fathom init` creates one; fathom finds it through `--home`,
`FATHOM_HOME` or by walking up from the working directory. The engine ships no
`[[reconcile.known]]` exceptions: those are facts about one data root's history.

Tests use synthetic data only: the fixtures under `tests/fixtures/` and the example data
root under `examples/data-root/`. Do not copy a real bank, arm, ledger or report into this
repository.

The guide to building a bank is
[`skills/fathom-eval/reference/authoring.md`](skills/fathom-eval/reference/authoring.md). It
describes as-built behaviour, so a change to a parser, a default, a flag, an exit code or to
what enters `config_hash` updates it in the same pull request. The parsers
(`src/fathom/taskbank.py`, `src/fathom/scenario.py`) remain the source of truth.

## Releasing

A release is a metadata-only commit on its own branch, merged through a pull request:

1. Roll `[Unreleased]` into a dated `## [X.Y.Z] - YYYY-MM-DD` heading, and state the bump
   class and the reason for it in the heading's prose.
2. Bump the version in `pyproject.toml` and `.claude-plugin/plugin.json`.
3. Run `uv lock`.

The `version-sites` reconciliation holds the three version sites together, so a half-done
bump fails the suite. Keep feature work out of the release commit, so that bisect and
per-commit review stay meaningful across the boundary.

After the merge, tag the release pull request's merge commit with an annotated tag:

```sh
git tag -a vX.Y.Z <release-merge-commit> -m "fathom X.Y.Z"
git push origin vX.Y.Z
```

Tags start at 0.8.0, the first version in this repository's history; the `CHANGELOG.md`
preamble records that floor. The `tag-watch` workflow checks every released version from the
floor on, once a day, and fails while any of them has no tag. It is scheduled rather than
triggered by the push, because the release commit lands before it can be tagged.

Users take a release with `uv tool install git+https://github.com/grimaldost/fathom@vX.Y.Z`
(which replaces an installed version), then run `fathom smoke` and `fathom reconcile` in
their data root. `fathom smoke` needs `--no-engine-boundary` there unless the data root has
a series arm at `scenarios/series.toml`, which the engine-boundary check reads
(`fathom smoke --help`). The plugin runtime re-pulls an installed plugin only when the
manifest's version moves, so a release is also what delivers plugin changes.

## Docs

- `docs/README.md` maps the tree. ADRs and dated specs are records: correct them with a dated
  note, never by silently rewriting them.
- Engine documents, `CHANGELOG.md` included, describe the engine. The results, trial counts,
  spend, bank and arm names of anyone's evaluations belong in that person's data root. Where
  an engine document needs an example, it uses a neutral one (`example`, `add`, `bare`,
  `nudge`), and it states a design rationale as the rule and its reason.
- Write in English, in a plain register.

Substantial changes to the harness follow the keel governed-series method bound in
`docs/method/method-bindings.md` (spec, Definition of Ready with a pre-mortem, a series of
pull requests, Definition of Done). A one-file fix does not need it.
