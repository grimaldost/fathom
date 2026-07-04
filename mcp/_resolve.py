"""Resolve and validate FATHOM_HOME — the user's canonical fathom checkout.

Stdlib only: this module is imported by the MCP server AND exercised by
``tests/test_packaging.py``, which must stay third-party-free per fathom's
stdlib-core invariant. It is the guard that keeps a paid ``fathom run`` from
executing inside the plugin's cache-clone: a real matrix appends to
``ledger/<bank>.jsonl``, which is the committed longitudinal record and belongs
in the source tree, not a throwaway clone that a cache refresh deletes.
"""

from __future__ import annotations

import pathlib
import tomllib


class FathomHomeError(RuntimeError):
    """FATHOM_HOME is unset, invalid, or points at a plugin cache-clone."""


def _looks_like_cache_clone(path: pathlib.Path) -> bool:
    """True if the path is under a Claude Code plugin cache (…/plugins/cache/…)."""
    parts = [p.lower() for p in path.parts]
    return any(parts[i] == "plugins" and parts[i + 1] == "cache" for i in range(len(parts) - 1))


def _is_fathom_checkout(path: pathlib.Path) -> bool:
    """True if `path` is a real fathom repo: pyproject name=fathom + src + tasks."""
    pyproj = path / "pyproject.toml"
    if not pyproj.is_file():
        return False
    try:
        data = tomllib.loads(pyproj.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    if data.get("project", {}).get("name") != "fathom":
        return False
    return (path / "src" / "fathom").is_dir() and (path / "tasks").is_dir()


def resolve_fathom_home(
    env: dict[str, str],
    *,
    start: pathlib.Path | None = None,
    plugin_root: pathlib.Path | None = None,
) -> pathlib.Path:
    """Return the validated fathom checkout, or raise FathomHomeError.

    Resolution order:
      1. ``$FATHOM_HOME`` if set;
      2. else walk up from ``start`` (default: cwd) for a fathom pyproject.

    A path that is a plugin cache-clone, equal to ``plugin_root``, or not a real
    fathom checkout is refused — runs must write the committed ledger into the
    user's own source tree.
    """
    candidate: pathlib.Path | None = None
    raw = env.get("FATHOM_HOME", "").strip()
    if raw:
        candidate = pathlib.Path(raw).expanduser()
        if not candidate.is_dir():
            raise FathomHomeError(f"FATHOM_HOME={raw!r} is not a directory")
    else:
        start = (start or pathlib.Path.cwd()).resolve()
        for d in (start, *start.parents):
            if _is_fathom_checkout(d):
                candidate = d
                break
        if candidate is None:
            raise FathomHomeError(
                "FATHOM_HOME is unset and no fathom checkout was found walking up from "
                f"{start}. Set FATHOM_HOME to your fathom repository."
            )

    candidate = candidate.resolve()
    if _looks_like_cache_clone(candidate):
        raise FathomHomeError(
            f"refusing to use {candidate} — it is a plugin cache-clone. Point FATHOM_HOME "
            "at your own fathom checkout so the committed ledger stays in the source tree."
        )
    if plugin_root is not None and candidate == plugin_root.resolve():
        raise FathomHomeError(
            f"refusing to use the plugin root {candidate} as FATHOM_HOME — runs must write "
            "the ledger into your source checkout, not the plugin tree."
        )
    if not _is_fathom_checkout(candidate):
        raise FathomHomeError(
            f"{candidate} is not a fathom checkout (need pyproject name=fathom, src/fathom/, tasks/)."
        )
    return candidate
