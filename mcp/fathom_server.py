"""fathom MCP server — thin, read-only wrappers over the fathom CLI.

Exposes ONLY the fast, safe, non-ledger-mutating operations:

- ``plan``   — ``fathom run <bank> --dry-run`` (trial count + USD ceiling + resume state)
- ``report`` — ``fathom report <bank>`` (regenerate the scorecard from the committed ledger)
- ``smoke``  — ``fathom smoke`` (real-spawn isolation gate; spends a few cents)

It deliberately does NOT expose ``fathom run``: a real matrix is long-running,
paid, and appends to the committed longitudinal ledger — none of which fits a
synchronous tool call. Use the ``/fathom:run`` slash command.

Every op runs the engine this plugin ships against the user's data root::

    uv run --no-dev --frozen --project <plugin root> python -m fathom --home <data root> ...

with the data root as the working directory, so a relative path argument (such as
``scenarios_dir``) means the same as it does on the command line run from there. The
data root is the directory holding ``tasks/``, ``scenarios/`` and the committed
``ledger/``, marked by a ``fathom.toml`` with a ``[data_root]`` table; ``FATHOM_HOME``
names it, or the server finds it at or above its working directory. It is never the
plugin's own tree or a plugin cache directory (``_resolve.py``). stdout carries the
JSON-RPC stream only; diagnostics go to stderr, and the framework's start-up banner is off.

The server reports fathom's version, read from the plugin manifest, as its own in the
handshake, not the version of the framework serving it. That needs ``fastmcp`` 2.11.3 or
later, the floor named in ``.claude-plugin/plugin.json``.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import subprocess
import sys
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

# _resolve.py sits beside this file; import it without a package install.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _resolve
from _resolve import FathomHomeError, fathom_command, resolve_fathom_home


def _plugin_version() -> str:
    """fathom's version, read from the plugin manifest at the plugin root.

    The server runs in a temporary environment that has fastmcp and not the fathom package,
    so ``importlib.metadata`` cannot see it. ``fathom reconcile`` keeps the manifest's
    version equal to ``pyproject.toml``'s.
    """
    manifest = _resolve.PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    return str(json.loads(manifest.read_text(encoding="utf-8"))["version"])


mcp = FastMCP("fathom", version=_plugin_version())


def _home() -> pathlib.Path:
    return resolve_fathom_home(dict(os.environ))


def _engine_env() -> dict[str, str]:
    """The server's environment without ``VIRTUAL_ENV``.

    The server runs in the temporary environment ``uv run --with fastmcp`` makes, which
    sets ``VIRTUAL_ENV``. Passed on, it makes the engine's ``uv run --project <plugin root>``
    print on every call that it does not match the project environment and will be ignored,
    a warning the agent then reads in each tool's ``stderr``.
    """
    return {k: v for k, v in os.environ.items() if k.upper() != "VIRTUAL_ENV"}


def _run_fathom(args: list[str], home: pathlib.Path, timeout: float) -> dict[str, Any]:
    cmd = fathom_command(home, args)
    proc = subprocess.run(
        cmd, cwd=home, env=_engine_env(), capture_output=True, text=True, timeout=timeout
    )
    return {
        "cmd": " ".join(cmd),
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


@mcp.tool
async def plan(
    bank: Annotated[
        str, Field(description="Bank name — the tasks/<bank>/ directory in the data root to plan.")
    ],
    repeats: Annotated[
        int,
        Field(description="Repeats per (scenario, task) pair. Default 2; multiplies trial count."),
    ] = 2,
    scenarios_dir: Annotated[
        str,
        Field(
            description=(
                "Directory, relative to the data root, globbed NON-recursively for arm "
                "*.toml. Default 'scenarios'. REQUIRED for any bank whose arms live in a "
                "subdir (pass it, e.g. 'scenarios/example'), or the wrong arms are planned."
            )
        ),
    ] = "scenarios",
    tasks_dir: Annotated[
        str,
        Field(
            description="Directory, relative to the data root, holding <bank>/ task banks. "
            "Default 'tasks'."
        ),
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
    FATHOM_HOME (or a working directory inside the data root) and uv on PATH.

    Returns a dict: ``ok`` (bool, exit 0), ``home`` (resolved data root), ``plan``
    (the dry-run text with the trial count + USD ceiling + resume counts),
    ``cmd``, ``exit_code``, ``stdout``, ``stderr``. Read ``plan`` before any paid run.
    When no data root resolves, returns ``ok`` false and ``error`` saying how to make one.
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
            description=(
                "Bank name — regenerate report/scorecard-<bank>.md in the data root from "
                "its committed ledger."
            )
        ),
    ],
) -> dict[str, Any]:
    """Render a fathom scorecard from the committed ledger.

    Idempotent: reads ledger/<bank>.jsonl in the data root, writes only the
    gitignored report/ there. Spends nothing. Requires FATHOM_HOME (or a working
    directory inside the data root) and uv on PATH.

    Returns a dict: ``ok``, ``home``, ``scorecard_path`` (the rendered file, or
    null if it was not produced), ``output`` (stdout), ``cmd``, ``exit_code``,
    ``stderr``. In the scorecard, the Per-Criterion Pass Rates table is the
    discriminating signal (not just the headline pass-rate). ``fathom run`` does
    not call the pairwise judge, so a scorecard of its trials has no 'Pairwise vs
    Bare Anchor' section.
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
            description=(
                "Append a forced failing check to demonstrate the nonzero-exit path. Default false."
            )
        ),
    ] = False,
    no_engine_boundary: Annotated[
        bool,
        Field(
            description=(
                "Skip the engine-boundary check, which reads the data root's series arm "
                "(scenarios/series.toml). Default false; set it when the data root has no "
                "series arm."
            )
        ),
    ] = False,
) -> dict[str, Any]:
    """Run the real-spawn isolation smoke gate — the go/no-go before any paid matrix.

    Spends a few cents (tiny real spawns); the engine-boundary check is
    token-free and reads the data root's series arm (``scenarios/series.toml``).
    A clean run ends with 'SMOKE RESULT: ALL PASS (n/n checks)'. Requires
    FATHOM_HOME (or a working directory inside the data root), uv on PATH, and
    valid Claude credentials; it runs the fathom engine this plugin ships.

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
    # The banner is the framework's own start-up text on stderr, not diagnostics of ours.
    mcp.run(show_banner=False)
