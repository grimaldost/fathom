"""Package-level checks for the fathom Claude Code plugin surface.

Stdlib only (fathom core invariant): validates the manifests and the
FATHOM_HOME guard WITHOUT importing fastmcp. The MCP tool-schema guard that
needs fastmcp lives in ``mcp/test_server_schema.py`` (run under a fastmcp env).

Runnable bare: ``python tests/test_packaging.py``.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile

_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load_resolve():
    spec = importlib.util.spec_from_file_location("fathom_resolve", _ROOT / "mcp" / "_resolve.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_plugin_manifest_wellformed() -> None:
    data = json.loads((_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert data["name"] == "fathom"
    assert data["version"]
    assert data["description"].strip()
    assert data["author"]["name"]
    server = data["mcpServers"]["fathom"]
    # anchored on the plugin root, launched as a script (not a PATH-dependent shim)
    assert any("${CLAUDE_PLUGIN_ROOT}" in a for a in server["args"])
    assert server["args"][-1].endswith("fathom_server.py")


def test_marketplace_manifest_wellformed() -> None:
    data = json.loads((_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert data["name"] == "fathom"
    assert data["owner"]["name"]
    assert "fathom" in [p["name"] for p in data["plugins"]]


def test_resolve_refuses_unset_and_undetectable() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        try:
            r.resolve_fathom_home({}, start=pathlib.Path(d))
        except r.FathomHomeError:
            return
    raise AssertionError("expected FathomHomeError when FATHOM_HOME is unset and undetectable")


def test_cache_clone_detection() -> None:
    r = _load_resolve()
    cache = pathlib.Path.home() / ".claude" / "plugins" / "cache" / "mkt" / "fathom" / "0.1.0"
    assert r._looks_like_cache_clone(cache) is True
    assert r._looks_like_cache_clone(_ROOT) is False


def test_resolve_refuses_non_checkout() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        try:
            r.resolve_fathom_home({"FATHOM_HOME": d})
        except r.FathomHomeError:
            return
    raise AssertionError("expected FathomHomeError for a dir that is not a fathom checkout")


def test_resolve_accepts_real_checkout() -> None:
    r = _load_resolve()
    home = r.resolve_fathom_home({"FATHOM_HOME": str(_ROOT)})
    assert home == _ROOT.resolve()


def test_plugin_invokes_fathom_as_module_not_console_script() -> None:
    # The `fathom` console-script .exe is blocked by Windows Smart App Control
    # (os error 4551); the plugin must run `python -m fathom` everywhere it
    # invokes fathom, so a fresh install works on a SAC-guarded host.
    runnable = [
        _ROOT / "commands" / "smoke.md",
        _ROOT / "commands" / "plan.md",
        _ROOT / "commands" / "run.md",
        _ROOT / "commands" / "report.md",
        _ROOT / "mcp" / "fathom_server.py",
    ]
    for path in runnable:
        text = path.read_text(encoding="utf-8")
        assert "uv run fathom " not in text, f"{path.name} invokes the SAC-blocked console script"
    server = (_ROOT / "mcp" / "fathom_server.py").read_text(encoding="utf-8")
    assert '"python", "-m", "fathom"' in server, "MCP server must invoke fathom as a module"


if __name__ == "__main__":
    import traceback

    _fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    _failed = 0
    for _fn in _fns:
        try:
            _fn()
            print(f"ok   {_fn.__name__}")
        except Exception:
            _failed += 1
            print(f"FAIL {_fn.__name__}")
            traceback.print_exc()
    sys.exit(1 if _failed else 0)
