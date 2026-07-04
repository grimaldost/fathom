# fathom MCP server (plugin scope)

A thin, **read-only** MCP surface over the fathom CLI, launched by the plugin
manifest (`.claude-plugin/plugin.json` → `mcpServers.fathom`). It lives here,
outside `src/fathom/`, so the eval core stays stdlib-only (this server needs
`fastmcp` + `pydantic`; the core does not).

## Tools

| tool | wraps | spend | mutates ledger |
|---|---|---|---|
| `plan` | `fathom run <bank> --dry-run` | none | no |
| `report` | `fathom report <bank>` | none | no (writes gitignored `report/`) |
| `smoke` | `fathom smoke` | a few cents | no |

`fathom run` is **not** exposed as a tool — it is long-running, paid, and
appends to the committed longitudinal ledger. Use the `/fathom:run` slash
command for that.

## FATHOM_HOME

Every tool shells out to `uv run --project $FATHOM_HOME python -m fathom …`. `_resolve.py`
requires `FATHOM_HOME` to be a real fathom checkout (pyproject `name = "fathom"`,
`src/fathom/`, `tasks/`) and **refuses** a plugin cache-clone or the plugin root,
so the committed ledger never lands in a throwaway tree. If `FATHOM_HOME` is
unset, it walks up from the cwd looking for the checkout.

## Run it standalone (dev / debugging)

```sh
FATHOM_HOME=/path/to/fathom uv run --with "fastmcp>=2.0" python mcp/fathom_server.py
```

## Tests

- `tests/test_packaging.py` — stdlib, validates the manifests + the FATHOM_HOME guard.
- `mcp/test_server_schema.py` — needs fastmcp; asserts every tool parameter is described:

```sh
uv run --with "fastmcp>=2.0" --with pytest python -m pytest mcp/test_server_schema.py
```
