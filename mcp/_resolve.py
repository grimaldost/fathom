"""Resolve the data root the plugin's MCP server runs fathom against.

fathom is two things kept in separate places: the engine, which the plugin ships (this
repository, at the plugin root), and a data root of the user's own that holds the banks
(``tasks/``), the arms (``scenarios/``), the committed ledger (``ledger/``) and the
write-ups (``docs/reports/``, ``docs/STATUS.md``). The server runs the engine the plugin
ships and points it at the data root::

    uv run --no-dev --frozen --project <plugin root> python -m fathom --home <data root> ...

``--no-dev`` because the engine needs no dependencies to run, and without it the first
call would install the development tools into the plugin's environment. ``--frozen``
because the plugin's lock file is used as shipped and never rewritten in a plugin cache.

The data root is found by the same function the command line uses,
``fathom.home.resolve``, loaded here from the engine's own source file so that the two
cannot drift and the server needs no installed copy of fathom. The order is therefore the
command line's: ``FATHOM_HOME`` if set, else the nearest directory at or above the
working directory whose ``fathom.toml`` has a ``[data_root]`` table of a schema the engine
reads. (No ``--home`` enters that search: the ``--home`` the server passes the engine is its
result.)

The server then holds the result to two further rules the command line does not need:

- it must carry the marker. The command line accepts an unmarked working directory that
  holds ``tasks/`` or ``ledger/``, with a warning; a tool call has no terminal to warn
  on, so the server refuses instead.
- it must not be a plugin cache directory, the plugin's own tree, or anything inside
  either. A paid ``fathom run`` appends to ``ledger/<bank>.jsonl``, the committed
  longitudinal record, and a cache refresh deletes that tree.

A data root needs no ``pyproject.toml``: the engine comes from the plugin root.

Stdlib only: this module is imported by the MCP server and exercised by
``tests/test_packaging.py``, which stays third-party-free like the rest of the core suite.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from collections.abc import Mapping
from types import ModuleType

# The plugin root is the engine checkout this file ships in.
PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
HOME_MODULE = PLUGIN_ROOT / "src" / "fathom" / "home.py"
_MODULE_NAME = "_fathom_home_for_the_mcp_server"


def _load_home() -> ModuleType:
    """The engine's ``fathom/home.py``, loaded from its file without importing fathom."""
    loaded = sys.modules.get(_MODULE_NAME)
    if loaded is not None:
        return loaded
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, HOME_MODULE)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {HOME_MODULE}")
    module = importlib.util.module_from_spec(spec)
    # Registered before it runs: dataclasses look their module up in sys.modules.
    sys.modules[_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[_MODULE_NAME]
        raise
    return module


home = _load_home()
MARKER = home.CONFIG_FILE


class FathomHomeError(RuntimeError):
    """No usable data root: none resolves, or the one that does is refused."""


def _looks_like_cache_clone(path: pathlib.Path) -> bool:
    """True if the path is under a Claude Code plugin cache (…/plugins/cache/…)."""
    parts = [p.lower() for p in path.parts]
    return any(parts[i] == "plugins" and parts[i + 1] == "cache" for i in range(len(parts) - 1))


def resolve_fathom_home(
    env: Mapping[str, str],
    *,
    start: pathlib.Path | None = None,
    plugin_root: pathlib.Path | None = None,
) -> pathlib.Path:
    """Return the data root the server runs against, or raise FathomHomeError.

    *env* is the server's environment, *start* the working directory to search from
    (default: the current one), *plugin_root* the plugin's own tree to refuse (default:
    the tree this file ships in).
    """
    try:
        found = home.resolve(None, env=env, cwd=start)
    except home.DataRootError as exc:
        raise FathomHomeError(str(exc)) from exc
    if not found.marked:
        raise FathomHomeError(
            f"{found.path} is not a fathom data root. {home.unmarked_reason(found.path)} The "
            f"plugin runs only against a marked data root. {home.how_to_mark(found.path)} "
            f"{home.HOW_TO}"
        )

    candidate = found.path.resolve()
    if _looks_like_cache_clone(candidate):
        raise FathomHomeError(
            f"refusing to use {candidate}: it is inside a plugin cache directory, and a cache "
            "refresh deletes it together with any ledger written there. Point FATHOM_HOME at "
            "your own data root."
        )
    root = (plugin_root if plugin_root is not None else PLUGIN_ROOT).resolve()
    if candidate == root or root in candidate.parents:
        raise FathomHomeError(
            f"refusing to use {candidate}: it is inside the plugin's own tree ({root}). "
            "Runs write the ledger into your data root, not the plugin. Point FATHOM_HOME at "
            "your own data root."
        )
    return candidate


def fathom_command(home_dir: pathlib.Path, args: list[str]) -> list[str]:
    """The argv that runs the engine the plugin ships against the data root *home_dir*.

    ``python -m fathom`` rather than the ``fathom`` console script: the generated
    console-script ``.exe`` can be blocked by Windows Smart App Control (os error 4551),
    and the module form runs the same entry point.
    """
    return [
        "uv",
        "run",
        "--no-dev",
        "--frozen",
        "--project",
        str(PLUGIN_ROOT),
        "python",
        "-m",
        "fathom",
        "--home",
        str(home_dir),
        *args,
    ]
