# fathom as a Claude Code plugin

This repository is also a Claude Code plugin: it serves fathom to a fresh agent
as a skill (`fathom-eval`), four slash commands (`/fathom:smoke`, `/fathom:plan`,
`/fathom:run`, `/fathom:report`), and a thin read-only MCP server (`plan`,
`report`, `smoke`). The manifests live under `.claude-plugin/`.

The plugin is a **thin launcher + docs**. The engine, the task banks, and the
**committed longitudinal ledger** live in your own fathom checkout — the plugin
shells into it and never runs fathom from its own install directory.

## FATHOM_HOME (the one requirement)

Every command and MCP tool runs `uv run python -m fathom …` inside your fathom checkout,
resolved as:

1. `$FATHOM_HOME` if set (recommended — set it to your fathom repo path);
2. otherwise the current directory or an ancestor that is a fathom checkout
   (`pyproject.toml` with `name = "fathom"`, plus `src/fathom/` and `tasks/`).

A plugin cache-clone or the plugin root itself is **refused** — a real
`fathom run` appends to `ledger/<bank>.jsonl`, which is committed and must stay
in the source tree, not a throwaway clone a cache refresh deletes.

Prerequisites: [`uv`](https://docs.astral.sh/uv/) and a local fathom checkout.

## Install

### Local (works today)

You already have the checkout — install the plugin from this path and set
`FATHOM_HOME`:

```sh
export FATHOM_HOME=/path/to/fathom
claude plugin marketplace add /path/to/fathom
claude plugin install fathom@fathom
```

### Marketplace (after the repo is published)

Once the repo is pushed to a public remote (e.g. `grimaldost/fathom`):

```sh
claude plugin marketplace add grimaldost/fathom
claude plugin install fathom@fathom
```

`.claude-plugin/marketplace.json` is authored for this path but is inert until
the public remote exists. The plugin still shells into your `FATHOM_HOME`
checkout for the actual runs — it does not run fathom from the marketplace
cache-clone.

## Surfaces

| surface | what | spend |
|---|---|---|
| skill `fathom-eval` | the operating manual: recipe, schemas, invariants, cost rails | — |
| `/fathom:smoke` | real-spawn go/no-go gate | a few cents |
| `/fathom:plan` | dry-run: trial count + USD ceiling + resume state | none |
| `/fathom:run` | the paid matrix (resumable) | ~$2/trial, ~$20-40/matrix |
| `/fathom:report` | render the scorecard from the ledger | none |
| MCP `plan` / `report` / `smoke` | read-only structured wrappers | none / none / a few cents |

`fathom run` is intentionally **not** an MCP tool — a paid, multi-hour,
ledger-mutating matrix is a streamed shell-out (`/fathom:run`), not a synchronous
tool call.

## Verifying the package

```sh
# manifests + FATHOM_HOME guard (stdlib, part of the core suite)
uv run pytest tests/test_packaging.py

# MCP tool-schema descriptions (needs fastmcp; plugin scope)
uv run --with "fastmcp>=2.0" --with pytest python -m pytest mcp/test_server_schema.py

# manifest lint
claude plugin validate .
```

## Not the same as convoy

fathom drives the [convoy](https://github.com/grimaldost/convoy) multi-PR engine
only as the measured `series` arm. To run convoy on real PRs, use convoy
directly — this plugin is for **evaluating** tools, not operating them.
