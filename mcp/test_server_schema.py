"""Schema-description regression guard for the fathom MCP server.

This imports fastmcp, so it is NOT part of fathom's stdlib-only core suite — it
lives at plugin scope. Run it under an env that has fastmcp:

    uv run --with "fastmcp>=2.0" --with pytest python -m pytest mcp/test_server_schema.py

The guard enforces the frame's "dead surface" rule: a parameter without a
schema description is a feature that does not exist for a blind agent.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))


def _tool_properties() -> dict[str, dict]:
    import fathom_server

    tools = asyncio.run(fathom_server.mcp.list_tools())  # list[FunctionTool]
    return {t.name: (t.parameters or {}).get("properties", {}) for t in tools}


def test_expected_tools_present() -> None:
    assert set(_tool_properties()) == {"plan", "report", "smoke"}


def test_every_tool_parameter_is_described() -> None:
    for tool_name, props in _tool_properties().items():
        for param, spec in props.items():
            assert spec.get("description", "").strip(), (
                f"{tool_name}.{param} has no schema description"
            )
