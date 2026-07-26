# Serena-first navigation

The serena MCP server is mounted in this session. Before editing, activate the
current working directory as the project (the `activate_project` tool) if it is
not already active.

Prefer serena's symbolic operations over whole-file reads and text grep:

- `get_symbols_overview` to map a file before opening it
- `find_symbol` to jump to a definition
- `find_referencing_symbols` to enumerate real (semantic) usages of a symbol -
  this distinguishes aliased imports and re-exports from same-named decoys
- `replace_symbol_body` / targeted edits at symbol granularity

Read only the symbols you need; avoid loading entire files when a symbol-level
view answers the question.
