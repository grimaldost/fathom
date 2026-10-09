# fathom as a Claude Code plugin

This repository is also a Claude Code plugin. It gives an agent:

- the skill `fathom-eval`, with the authoring guide
  ([`skills/fathom-eval/reference/authoring.md`](skills/fathom-eval/reference/authoring.md));
- five slash commands: `/fathom:smoke`, `/fathom:plan`, `/fathom:run`, `/fathom:report`,
  `/fathom:reconcile`;
- a read-only MCP server with the tools `plan`, `report` and `smoke`.

The manifests live under `.claude-plugin/`.

## The engine it runs, and the data root it runs on

The plugin runs **the engine it ships**. Every slash command and MCP tool runs, from the data
root directory,

```sh
uv run --no-dev --frozen --project <plugin root> python -m fathom --home <data root> …
```

`--no-dev` because the engine needs no dependencies to run, and without it the first call
would install the development tools into the plugin's environment. `--frozen` because the
plugin's lock file is used as shipped and never rewritten inside a plugin cache.
`python -m fathom` rather than the `fathom` console script, because some application-control
policies (Windows Smart App Control, for one) block console-script executables. Running from
the data root means a relative path argument, such as `--scenarios-dir scenarios/example`,
resolves inside it.

The engine version is the plugin's version, and each ledger row it writes records that
version as `engine_version`.

The MCP server itself starts as `uv run --no-project --with "fastmcp>=2.11.3" python <plugin
root>/mcp/fathom_server.py` (`.claude-plugin/plugin.json`). `--no-project` keeps uv from
reading a `pyproject.toml` in the directory Claude Code was opened in, which is usually a
project of your own; the server needs only `fastmcp`, and the engine calls above name their
project explicitly.

The **data root** is yours: the directory that holds your banks, arms and committed ledger,
marked by a `fathom.toml` with a `[data_root]` table. It needs nothing else to be usable by
the plugin; in particular it needs no `pyproject.toml`. To create one, use the command line
(`uv tool install git+https://github.com/grimaldost/fathom@v0.11.0`, or a clone of this
repository with `uv run`):

```sh
fathom init /path/to/my-evals
```

It writes `fathom.toml` (the marker: `[data_root]` with `schema = 1`), a `.gitignore` listing
`.fathom/` and `report/`, and a `.gitattributes` that pins LF line endings for every text file
(`* text=auto eol=lf`); it creates `tasks/`, `scenarios/`, `ledger/` and `docs/reports/`; and
it never overwrites an existing file. Keep the data root in its own git repository. The
authoring guide explains everything that goes in it, and `examples/data-root/` in this
repository is a complete example.

## FATHOM_HOME

The plugin finds the data root as follows:

1. `$FATHOM_HOME`, if set. Set it to your data root.
2. Otherwise, the nearest directory at or above the current one whose `fathom.toml` has a
   `[data_root]` table.

Because `FATHOM_HOME` comes first, a value set for one data root applies to every session
until you change or unset it, including a session opened inside another data root. The
commands ask which one you mean when the two disagree.

The directory must carry the marker, and it must not be the plugin's own tree, a plugin
cache directory, or inside either. A real `fathom run` appends to `ledger/<bank>.jsonl`, and a
cache refresh would delete that file. The command line also accepts, with a warning, an
unmarked working directory that holds `tasks/` or `ledger/`; the plugin does not, because a
tool call has no terminal to show the warning on. When no usable data root resolves, the MCP
tools return an error that says how to create one or point at one, and the slash commands ask
for the path. An engine checkout is not a data root: it carries no marker.

The marker's `schema` must be the integer 1. A marker without it, or with any other value, is
an error wherever it is met, and the search stops at it rather than walking past to a data
root further up. A later schema means the data root was written for a newer fathom: update
the plugin.

Prerequisites: [`uv`](https://docs.astral.sh/uv/), git, and the `claude` CLI with a working
login.

## Install

### Marketplace

```sh
claude plugin marketplace add grimaldost/fathom
claude plugin install fathom@fathom
export FATHOM_HOME=/path/to/my-evals
```

### From a local engine checkout

```sh
claude plugin marketplace add /path/to/fathom
claude plugin install fathom@fathom
export FATHOM_HOME=/path/to/my-evals
```

The plugin runtime updates an installed plugin when the manifest's version moves, so a new
release of the engine reaches the plugin with that release.

## Surfaces

| Surface | What | Spend |
|---|---|---|
| skill `fathom-eval` | How to run an analysis, the authoring guide, the invariants, the cost rails | none |
| `/fathom:smoke` | The real-spawn go/no-go gate | a few cents |
| `/fathom:plan` | Dry run: arms, trial count, USD ceiling, resume state | none |
| `/fathom:run` | The paid matrix (resumable) | paid; the plan prints the ceiling |
| `/fathom:report` | Render the scorecard from the ledger | none |
| `/fathom:reconcile` | Check every fact the data root records twice | none |
| MCP `plan` / `report` / `smoke` | Structured wrappers for the same operations | none / none / a few cents |

`fathom run` is intentionally not an MCP tool. A paid matrix that can take hours and appends
to the ledger belongs in a streamed shell command (`/fathom:run`), not a synchronous tool
call.

The other commands (`init`, `validate`, `verify-arming`, `stop`, `void`, `index`) have no
slash command or MCP tool. Run them the same way, `uv run --no-dev --frozen --project <plugin
root> python -m fathom --home <data root> <command>`, or with an installed `fathom`. `init`
takes the directory to create in place of `--home`: `… python -m fathom init <dir>`.
`validate` is free; `verify-arming` makes one cheap real spawn per treatment arm and costs a
little.

## Verifying the package

```sh
# manifests and the data-root guard (standard library, part of the core suite)
uv run pytest tests/test_packaging.py

# MCP tool-schema descriptions and the commands each tool runs (needs fastmcp)
uv run --with "fastmcp>=2.11.3" --with pytest python -m pytest mcp/test_server_schema.py

# manifest lint
claude plugin validate .
```

## Not the same as convoy

fathom drives the [convoy](https://github.com/grimaldost/convoy) multi-PR engine only as the
measured `series` arm. To run convoy on real work, use convoy directly; this plugin is for
evaluating tools, not operating them.
