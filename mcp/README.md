# fathom MCP server (plugin scope)

A thin, **read-only** MCP surface over the fathom CLI, launched by the plugin
manifest (`.claude-plugin/plugin.json` → `mcpServers.fathom`). It lives here,
outside `src/fathom/`, so the eval core stays stdlib-only (this server needs
`fastmcp` + `pydantic`; the core does not).

## Tools

| tool | wraps | spend | mutates ledger |
|---|---|---|---|
| `plan` | `fathom run <bank> --dry-run` | none | no |
| `report` | `fathom report <bank>` | none | no (writes the gitignored `report/`) |
| `smoke` | `fathom smoke` (`force_fail`, `no_engine_boundary` map to the two flags) | a few cents | no |

`fathom run` is **not** exposed as a tool — it is long-running, paid, and
appends to the committed longitudinal ledger. Use the `/fathom:run` slash
command for that.

## FATHOM_HOME is the data root

fathom keeps the engine (this repository, which the plugin ships) apart from the
data it runs against. The data lives in a **data root**: a directory of your own
that holds `tasks/`, `scenarios/`, the committed `ledger/`, and `docs/reports/`.
Every tool runs the plugin's own engine against it:

```
uv run --no-dev --frozen --project <plugin root> python -m fathom --home <data root> ...
```

with the data root as the working directory. The data root needs no
`pyproject.toml` and no copy of fathom of its own. `--no-dev` keeps the development
tools out of the plugin's environment (the engine needs no dependencies to run), and
`--frozen` uses the plugin's lock file as shipped, never rewriting it in a plugin cache.

`_resolve.py` finds the data root with the engine's own resolver
(`src/fathom/home.py`, loaded by path), so the order is the command line's:
`FATHOM_HOME` if set, else the nearest directory at or above the server's working
directory whose `fathom.toml` has a `[data_root]` table. It then **refuses**:

- a directory without the marker, even one that holds `tasks/` or `ledger/` (the
  command line would use it with a warning; a tool call has nowhere to show one);
- a plugin cache directory, and the plugin's own tree or anything inside it,
  even when marked, so the committed ledger never lands in a tree that a cache
  refresh deletes.

Every refusal says how to make a data root. `fathom init DIR` makes one:

```
my-evals/
  fathom.toml        # [data_root]
                     # schema = 1
  .gitignore         # .fathom/, report/
  .gitattributes     # text files pinned to LF
  tasks/<bank>/      # banks
  scenarios/         # arms
  ledger/            # committed, append-only
  docs/reports/      # write-ups, and the generated LEDGER-INDEX.md
```

The root `README.md` spells out each file.

## Run it standalone (dev / debugging)

```sh
FATHOM_HOME=/path/to/my-evals uv run --with "fastmcp>=2.11.3" python mcp/fathom_server.py
```

## Tests

- `tests/test_packaging.py` — stdlib; validates the manifests and the data-root
  guard against temporary directories, and holds the guard to the command line's
  resolver.
- `mcp/test_server_schema.py` — needs fastmcp; asserts every tool parameter is
  described and that each tool runs the expected command against the data root
  (with `subprocess.run` replaced, so nothing spawns). CI runs this file:

```sh
uv run --with "fastmcp>=2.11.3" --with pytest python -m pytest mcp/test_server_schema.py
```
