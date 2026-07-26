"""Arming probe for MCP-served arms — run BEFORE any paid matrix.

Asserts that a scenario's mounted MCP server is not merely *registered* but that
its tools are **callable** under the scenario's own allow-list. This exists
because a silently-unarmed MCP arm is indistinguishable from a null result in the
scorecard: on 2026-07-25 the `serena` arm allowed `mcp__serena` while the real
tool names were `mcp__plugin_serena-arm_serena__*`, so 9 trials (~$2.7) measured
a brief-only condition that the scorecard labeled "serena".

Usage (from FATHOM_HOME):
    uv run python scenarios/serena-nav/arming_probe.py scenarios/serena-nav/serena.toml

Exit 0 = armed (a mounted-server tool was actually invoked); exit 1 = NOT armed.
Costs a few cents (one short headless spawn).
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import tomllib

PROMPT = (
    "Use your serena MCP tools, not Read or Grep: first activate this directory as the "
    "project, then call get_symbols_overview on mod.py and report the symbol names it "
    "returns. You must call the MCP tools."
)


def main() -> int:
    scen_path = pathlib.Path(sys.argv[1]).resolve()
    scen = tomllib.loads(scen_path.read_text(encoding="utf-8"))
    allowed = (scen.get("tools") or {}).get("allowed") or []
    mounts = [
        str((scen_path.parent / m).resolve()) for m in (scen.get("plugins") or {}).get("mount", [])
    ]
    if not mounts:
        print(f"[SKIP] {scen['name']}: no [plugins].mount — nothing to arm")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        ws = pathlib.Path(tmp)
        (ws / "mod.py").write_text(
            "def alpha():\n    return 1\n\n\ndef beta():\n    return 2\n", encoding="utf-8"
        )
        cmd = [
            "claude",
            "-p",
            PROMPT,
            "--output-format",
            "stream-json",
            "--verbose",
            "--allowed-tools",
            ",".join(allowed),
        ]
        for m in mounts:
            cmd += ["--plugin-dir", m]
        proc = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=900)

    registered: list[dict] = []
    called: set[str] = set()
    denied: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "system" and obj.get("subtype") == "init":
            registered = obj.get("mcp_servers") or []
        content = ((obj.get("message") or {}).get("content")) or []
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and str(block.get("name", "")).startswith(
                    "mcp__"
                ):
                    called.add(str(block["name"]))
                if block.get("type") == "tool_result":
                    txt = json.dumps(block.get("content"))
                    if "permission" in txt.lower() or "denied" in txt.lower():
                        denied.append(txt[:160])

    print(f"scenario:            {scen['name']}")
    print(f"mcp_servers at init: {[s.get('name') for s in registered]}")
    print(f"mcp tools CALLED:    {sorted(called) or '(none)'}")
    if denied:
        print(f"denied tool_results: {len(denied)} e.g. {denied[0]}")
    armed = bool(called) and not denied
    print("ARMING:", "PASS (tools callable)" if armed else "FAIL (arm would run unarmed)")
    return 0 if armed else 1


if __name__ == "__main__":
    sys.exit(main())
