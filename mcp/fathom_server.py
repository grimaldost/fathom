"""fathom MCP server — thin, read-only wrappers over the fathom CLI.

Exposes ONLY the fast, safe, non-ledger-mutating operations:

- ``plan``   — ``fathom run <bank> --dry-run`` (trial count + USD ceiling + resume state)
- ``report`` — ``fathom report <bank>`` (regenerate the scorecard from the committed ledger)
- ``smoke``  — ``fathom smoke`` (real-spawn isolation gate; spends a few cents)

It deliberately does NOT expose ``fathom run``: a real matrix is long-running
(hours), paid (~$20-40), and appends to the committed longitudinal ledger — none
of which fits a synchronous tool call. Use the ``/fathom:run`` slash command.

Every op shells out to ``uv run --project <FATHOM_HOME> fathom …``, where
FATHOM_HOME is the user's canonical checkout (never the plugin cache-clone).
stdout carries the JSON-RPC stream only; diagnostics go to stderr.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import subprocess
import sys
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

# _resolve.py sits beside this file; import it without a package install.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _resolve import FathomHomeError, resolve_fathom_home  # noqa: E402

mcp = FastMCP("fathom")


def _plugin_root() -> pathlib.Path | None:
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    return pathlib.Path(root) if root else None


def _home() -> pathlib.Path:
    return resolve_fathom_home(dict(os.environ), plugin_root=_plugin_root())


def _run_fathom(args: list[str], home: pathlib.Path, timeout: float) -> dict[str, Any]:
    # `python -m fathom`, not the `fathom` console-script: the module form is
    # portable and sidesteps Windows Smart App Control blocking the generated
    # console-script .exe (os error 4551).
    cmd = ["uv", "run", "--project", str(home), "python", "-m", "fathom", *args]
    proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
        cmd, cwd=home, capture_output=True, text=True, timeout=timeout
    )
    return {
        "cmd": " ".join(cmd),
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


@mcp.tool
async def plan(
    bank: Annotated[str, Field(description="Bank name — the tasks/<bank>/ directory to plan.")],
    repeats: Annotated[
        int,
        Field(description="Repeats per (scenario, task) pair. Default 2; multiplies trial count."),
    ] = 2,
    scenarios_dir: Annotated[
        str,
        Field(
            description=(
                "Directory globbed NON-recursively for arm *.toml. Default 'scenarios'. "
                "REQUIRED (pass the subdir, e.g. 'scenarios/skill-pyeng') for any bank that "
                "ships its own arms, or the wrong arms are planned."
            )
        ),
    ] = "scenarios",
    tasks_dir: Annotated[
        str, Field(description="Directory holding <bank>/ task banks. Default 'tasks'.")
    ] = "tasks",
    limit: Annotated[
        int | None,
        Field(description="Cap the plan to the first N not-yet-done trials. None plans them all."),
    ] = None,
    include_holdout: Annotated[
        bool,
        Field(description="Also plan the bank's sealed holdout tasks (ADR-0005). Default false."),
    ] = False,
) -> dict[str, Any]:
    """Plan a fathom matrix: trial count, advisory USD ceiling, and resume state.

    Spawns nothing, spends nothing, writes no ledger — always safe. Requires
    FATHOM_HOME to point at your fathom checkout and uv on PATH.

    Returns a dict: ``ok`` (bool, exit 0), ``home`` (resolved checkout), ``plan``
    (the dry-run text with the trial count + USD ceiling + resume counts),
    ``cmd``, ``exit_code``, ``stdout``, ``stderr``. Read ``plan`` before any paid run.
    """
    try:
        home = _home()
    except FathomHomeError as exc:
        return {"ok": False, "error": str(exc)}
    args = [
        "run",
        bank,
        "--dry-run",
        "--repeats",
        str(repeats),
        "--scenarios-dir",
        scenarios_dir,
        "--tasks-dir",
        tasks_dir,
    ]
    if limit is not None:
        args += ["--limit", str(limit)]
    if include_holdout:
        args.append("--include-holdout")
    res = await asyncio.to_thread(_run_fathom, args, home, 120.0)
    return {"ok": res["exit_code"] == 0, "home": str(home), "plan": res["stdout"], **res}


@mcp.tool
async def report(
    bank: Annotated[
        str,
        Field(
            description="Bank name — regenerate report/scorecard-<bank>.md from its committed ledger."
        ),
    ],
) -> dict[str, Any]:
    """Render a fathom scorecard from the committed ledger.

    Idempotent: reads ledger/<bank>.jsonl, writes only the gitignored report/.
    Spends nothing. Requires FATHOM_HOME and uv.

    Returns a dict: ``ok``, ``home``, ``scorecard_path`` (the rendered file, or
    null if it was not produced), ``output`` (stdout), ``cmd``, ``exit_code``,
    ``stderr``. In the scorecard, the Per-Criterion Pass Rates table is the
    discriminating signal (not just the headline pass-rate); the 'Pairwise vs
    Bare Anchor' section is always empty in v1 because the judge ships dark.
    """
    try:
        home = _home()
    except FathomHomeError as exc:
        return {"ok": False, "error": str(exc)}
    res = await asyncio.to_thread(_run_fathom, ["report", bank], home, 120.0)
    scorecard = home / "report" / f"scorecard-{bank}.md"
    return {
        "ok": res["exit_code"] == 0,
        "home": str(home),
        "scorecard_path": str(scorecard) if scorecard.is_file() else None,
        "output": res["stdout"],
        **res,
    }


@mcp.tool
async def smoke(
    force_fail: Annotated[
        bool,
        Field(
            description="Append a forced failing check to demonstrate the nonzero-exit path. Default false."
        ),
    ] = False,
    no_engine_boundary: Annotated[
        bool,
        Field(
            description="Skip the real-engine (convoy) boundary assertion in group 4. Default false."
        ),
    ] = False,
) -> dict[str, Any]:
    """Run the real-spawn isolation smoke gate — the go/no-go before any paid matrix.

    Spends a few cents (tiny real spawns); the engine-boundary check is
    token-free. A clean run prints 'ALL PASS (8/8 checks)'. Requires FATHOM_HOME,
    uv, and valid Claude credentials.

    Returns a dict: ``ok`` (true only on exit 0), ``home``, ``output`` (stdout),
    ``cmd``, ``exit_code``, ``stderr``.
    """
    try:
        home = _home()
    except FathomHomeError as exc:
        return {"ok": False, "error": str(exc)}
    args = ["smoke"]
    if force_fail:
        args.append("--force-fail")
    if no_engine_boundary:
        args.append("--no-engine-boundary")
    res = await asyncio.to_thread(_run_fathom, args, home, 600.0)
    return {"ok": res["exit_code"] == 0, "home": str(home), "output": res["stdout"], **res}


if __name__ == "__main__":
    mcp.run()
