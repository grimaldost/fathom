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
`CLAUDE.md` point here rather than repeat it. CI runs the same checks, from two places: the
shared pipeline that railform writes from this repository's frame (`railform.toml`; see
[CI](#ci)), and the engine checks in `.github/workflows/ci.yml`. A change to the gates is made
there and here.

```sh
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run --with "fastmcp>=2.11.3" --with pytest python -m pytest mcp/test_server_schema.py
uv run --with "fastmcp==2.11.3" --with pytest python -m pytest mcp/test_server_schema.py
FATHOM_HOME= uv run fathom reconcile                # the engine checkout: version sites
uv run fathom --home examples/data-root reconcile   # the example data root
uv run fathom smoke                                 # manual: real spawns, a few cents
```

`FATHOM_HOME=` in front of a command sets the variable to empty for that command alone, and
fathom reads an empty `FATHOM_HOME` as unset. In PowerShell, run `$env:FATHOM_HOME = $null`
first, which removes the variable for the rest of the session.

- `uv lock --check` comes first because no test can see a stale lock: `uv run` re-locks
  before pytest could read the file. CI runs it before `uv sync`.
- `pytest` collects `tests/` only. The MCP server's tests import `fastmcp`, which the core
  does not depend on, so they run as their own step with `fastmcp` added for that command
  alone. They check each tool's parameter descriptions, the command each tool runs, the
  version the server reports and that starting it prints no banner. They run twice: at the
  newest `fastmcp` and pinned at the floor, 2.11.3, the oldest release that accepts the
  `version` constructor argument and the `show_banner` run argument the server passes and
  that installs against current dependencies. Raising the floor means changing the
  `fastmcp` string in `.claude-plugin/plugin.json`, in both CI steps and in this list.
- `fathom reconcile` is free and spawns nothing. Every fact the tree records twice must
  agree; exit 13 means one does not. It runs twice. At the engine root it holds the version
  sites (`pyproject.toml`, `.claude-plugin/plugin.json`, the newest `CHANGELOG.md`
  heading, and the pinned install lines in `README.md`, `README-plugin.md` and the authoring
  guide) to each other. Against `examples/data-root/` it checks that the example data root
  still reconciles: its ledger index, its rows' config hashes, its arm names and its
  replication plan (one warning, excused). Exit 13 also
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
  run lock or the spawn environment: the unit suite stubs every spawn and cannot see those
  regressions. It reads no data root, so it runs the same at the engine root and in a data
  root. The engine-boundary check was retired in 0.13.0 with the series strategy, and
  `--no-engine-boundary` is retired too: accepted and ignored for one release.
- `fathom verify-arming` is not a gate here. It proves a data root's own treatment arms on
  real spawns, costs money, and the engine has no arms.

### CI

`.github/workflows/ci.yml` runs every gate above except `fathom smoke`, on ubuntu and windows,
in two parts. Both are required through one context, `gate`, which the branch ruleset names.

- **railform.** The `railform` job calls the shared workflow of
  [railform](https://github.com/grimaldost/railform) at the commit pinned in `ci.yml`, which
  `.pre-commit-config.yaml` and `.github/workflows/railform-tag-watch.yml` name too. It runs
  the lock check, the sync, `ruff format --check`, `ruff check` and pytest on Python 3.12
  (`railform frame` prints the exact commands), and these checks:
  - `frame`: `railform.toml` is valid, and a value that departs from the project type's
    preset has an `exceptions` row with a reason. This repository has three rows: no type check
    (fathom has no type checker), the files a release commit may edit, and the four user names
    its tests and docstrings use in home-directory paths.
  - **Changelog currency** (pull requests only); see below.
  - **Commit lane** (pull requests only): every commit subject is a conventional subject,
    no commit or pull request text carries an AI-attribution line, and the head branch has a
    conventional name (`<category>/<slug>`, or Dependabot's).
  - `hooks`: the hook wrappers are tracked as `100755` and are the text railform renders, the
    owned parts of the CI, hook and Dependabot files have not been edited by hand, and the
    hygiene hooks pass over the pull request's changed files.
  - `checks` also runs railform's private-reference check over every tracked file.
  - **Workflow lint**: `zizmor` over `.github/workflows`.
- **The engine checks** (`engine-checks` in `ci.yml`). They reconcile the example data root
  the two other ways a user reaches one: named by `FATHOM_HOME`, and found from inside it
  (`uv run --project ../.. fathom reconcile` in `examples/data-root/`, with `FATHOM_HOME`
  empty). The MCP server's tests run at both `fastmcp` versions. Then one more check:
  - **The installed wheel.** The steps above import the source tree, so a file the wheel leaves
    out would pass them and be missing from every installed copy (the smoke canary plugin is
    package data). CI builds the wheel (`uv build --wheel -o dist`) and runs it in a
    throwaway environment that holds the wheel alone
    (`uv run --isolated --no-project --with <wheel> …`): from inside `examples/data-root/`,
    `fathom --version`, `fathom reconcile` and import checks; from a directory outside it,
    `fathom --home <example> reconcile` and `fathom --home <example> run example --dry-run`.

`fathom reconcile` is also exercised inside pytest (`tests/test_reconcile.py`).

Moving the railform pin is one change to every reference at once, made with
`railform adopt --pin <sha>`, never by hand; `railform adopt --check` fails while any owned
line differs. A job added to `ci.yml` is picked up by `gate` on the next `railform adopt`.

### Hooks

The fast half of the gates runs before every commit. Arm the tracked hooks once per clone,
with railform's own command, run from the pinned commit (`<sha>` is the `rev` of the railform
entry in `.pre-commit-config.yaml`):

```sh
uvx --from "git+https://github.com/grimaldost/railform@<sha>" railform arm
```

`railform arm` sets `core.hooksPath` to `.githooks`, so `git config core.hooksPath .githooks`
does the same. `railform hooks-check --armed` fails in a clone that is armed to another
directory. Worktrees share their clone's configuration, so arm each clone, not each worktree.
The hooks used to live in `tools/git-hooks/`; that directory holds stubs that fail with the
command to run, so a clone still armed to it cannot commit unchecked. They are removed in a
later change, once every clone has been armed again.

Do not use `pre-commit install`. It writes a hook that invokes the bare `pre-commit`
console-script shim, and where an application-control policy blocks such shims the hook
silently never runs. The tracked hooks call `uv run --frozen python -m pre_commit` instead.
The pre-commit stage runs railform's hygiene hooks, its private-reference check, its hook
wrapper check, ruff format and check and, for the paths listed in `.pre-commit-config.yaml`,
the `fathom reconcile` runs and the pytest test that re-derives the example data root's config
hashes. Each hook that runs fathom clears `FATHOM_HOME` or names its root with `--home`, for the
reason given under the gates. The commit-msg stage enforces conventional-commit subjects and
rejects AI-attribution trailers (railform's `commit.types` and `commit.attribution_patterns`),
and the pre-push stage judges the branch name. Skip a single commit with `git commit --no-verify`
when you mean to; CI runs the full set regardless.

### The changelog moves with the change

A pull request whose diff touches a harness path fails CI unless `CHANGELOG.md` moves with
it (an `[Unreleased]` entry) or each commit that touches one carries a trailer line
`Changelog: none (<reason>)`, which declares its own commit only. The older spelling,
`Changelog: not needed (<reason>)`, no longer counts. Harness paths are `src/`, `pyproject.toml`, `.claude-plugin/`,
`commands/`, `mcp/`, `skills/`, `tools/` and `.githooks/`: what reaches an installed copy, plus
the tooling the gates and hooks run from. They are the `[changelog] records` rows of
`railform.toml`. Docs, examples, tests, CI configuration and `uv.lock` are exempt, and
`tests/test_changelog_records.py` holds every top-level entry of the tree to one decision or
the other. The check is `railform changelog-gate`, run by the `changelog` job.

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
  spawns and gate commands get no `FATHOM_*` variable, no launch-directory
  variable (`PWD`, `OLDPWD`) and no variable whose value names the data root (`PATH` loses
  only its entries there), and each trial spawn is given staged copies of the arm's
  `[context]` and `[plugins]` files, so its command line names no path in the data root.
  `CLAUDE.md` names the functions that do this.
- **Spawn isolation (ADR-0004).** Spawns run with a credential-only temporary
  `CLAUDE_CONFIG_DIR`, headless default-deny and explicit allow lists, never
  `bypassPermissions` or `--dangerously-skip-permissions`. All model calls go through
  `Runner` adapters (ADR-0001), with no exception since the series strategy was retired in
  0.13.0.
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

The guide to building a bank starts at
[`skills/fathom-eval/reference/authoring.md`](skills/fathom-eval/reference/authoring.md) and
continues in `arming.md` and `bank-design.md` beside it. It describes as-built behaviour, so a
change to a parser, a default, a flag, an exit code or to what enters `config_hash` updates it
in the same pull request. The parsers
(`src/fathom/taskbank.py`, `src/fathom/scenario.py`) remain the source of truth. Each of the
three files states a line budget in its header; an addition that would pass it displaces
something first, and `tests/test_authoring_guide.py` fails otherwise. The same test checks
that every citation of a guide section names the file that holds it.

## Releasing

A release is a metadata-only commit on its own branch, merged through a pull request:

1. For a release that changes `commands/`, `skills/`, `mcp/` or the authoring guide, run
   the fresh-agent acceptance test on the release branch before merging:
   `uv run python tools/agent_acceptance.py --preflight-only --data-root DIR`, then
   `--scenarios S1,S3,S2`. Record its verdict in the release PR. It needs a working
   Claude login and spends money; link [`docs/agent-acceptance.md`](docs/agent-acceptance.md)
   and its Cost section for the caps.
2. Roll `[Unreleased]` into a dated `## [X.Y.Z] - YYYY-MM-DD` heading, and state the bump
   class and the reason for it in the heading's prose. Set the version on every
   `docs/backlog.md` line that says the release closed something as "Unreleased";
   `tests/test_backlog_versions.py` fails once `[Unreleased]` is empty and one still does.
3. Bump the version in `pyproject.toml`, `.claude-plugin/plugin.json` and the pinned install
   lines (`git+https://.../fathom@vX.Y.Z`) in `README.md`, `README-plugin.md` and the
   authoring guide.
4. Run `uv lock`.

The `version-sites` reconciliation holds these version sites together, so a half-done
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

`railform release-check` (the `railform-tag-watch` workflow: every tag push, once a day, on
demand) judges the tags that exist, from v0.9.0 on: each is annotated, sits on the merge commit
of its release pull request, and that pull request's `release:` commit changes only release
metadata (`release.metadata_paths` in `railform.toml`: the files this section names, the lock and
`docs/backlog.md`). A release pull request is identified by its head branch,
`release/X.Y.Z`, or by a title that starts `release:` and carries the version. The `tag-watch`
workflow above stays because it judges the other direction, a released changelog heading with
no tag.

Users take a release with `uv tool install git+https://github.com/grimaldost/fathom@vX.Y.Z`
(which replaces an installed version), then run `fathom smoke` and `fathom reconcile` in
their data root. A data root whose arms still use the retired `series` strategy or
`[tools] source = "repo"` stops loading on 0.13.0 or later, so remove those arms first.
The plugin runtime re-pulls an installed plugin only when the
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
