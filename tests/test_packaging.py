"""Package-level checks for the fathom Claude Code plugin surface.

Stdlib only (fathom core invariant): validates the manifests and the MCP server's
data-root guard (``mcp/_resolve.py``) WITHOUT importing fastmcp. The MCP checks that need
fastmcp live in ``mcp/test_server_schema.py`` (run under a fastmcp env).

The guard finds the data root with the command line's own resolver, ``fathom.home``, so
several tests below hold the two to each other: same function, same order, same answer.

Runnable bare: ``python tests/test_packaging.py``.
"""

from __future__ import annotations

import codecs
import functools
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
from collections.abc import Callable

_ROOT = pathlib.Path(__file__).resolve().parents[1]
# The engine package, for the tests that compare the guard with it; bare runs have no
# installed copy to import.
sys.path.insert(0, str(_ROOT / "src"))

from fathom import home as engine_home  # noqa: E402

_MARKER = "[data_root]\nschema = 1\n"


@functools.cache
def _load_resolve():
    # Loaded once, so every test sees the same FathomHomeError class.
    spec = importlib.util.spec_from_file_location("fathom_resolve", _ROOT / "mcp" / "_resolve.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _make_data_root(path: pathlib.Path, *, marker: str | None = _MARKER) -> pathlib.Path:
    """Build a synthetic data root: the marker and the three data dirs, no pyproject."""
    path.mkdir(parents=True, exist_ok=True)
    if marker is not None:
        (path / "fathom.toml").write_text(marker, encoding="utf-8")
    for sub in ("tasks", "scenarios", "ledger"):
        (path / sub).mkdir(exist_ok=True)
    return path


def _error_of(fn: Callable[[], object]) -> str:
    """The FathomHomeError message ``fn`` raises; fails the test if it raises none."""
    r = _load_resolve()
    try:
        fn()
    except r.FathomHomeError as exc:
        return str(exc)
    raise AssertionError("expected FathomHomeError")


def _plain_dir(parent: str) -> pathlib.Path:
    """A directory that is no data root and has none above it (a temporary directory's)."""
    path = pathlib.Path(parent) / "plain"
    path.mkdir()
    return path


# --- manifests ----------------------------------------------------------------


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
    # uv must not read this repo's own project config when serving the plugin, and
    # that flag has to land before the interpreter it modifies is even named.
    args = server["args"]
    assert "--no-project" in args
    assert args.index("--no-project") < args.index("python")


def test_marketplace_manifest_wellformed() -> None:
    data = json.loads((_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert data["name"] == "fathom"
    assert data["owner"]["name"]
    assert "fathom" in [p["name"] for p in data["plugins"]]


# --- one resolver: the guard runs the command line's own ---------------------------


def test_the_guard_loads_the_engines_resolver_from_its_source_file() -> None:
    r = _load_resolve()
    assert pathlib.Path(r.home.__file__).resolve() == pathlib.Path(engine_home.__file__).resolve()
    assert r.HOME_MODULE == _ROOT / "src" / "fathom" / "home.py"
    assert r.PLUGIN_ROOT == _ROOT


def test_the_guard_and_the_command_line_resolve_in_the_same_order() -> None:
    """Every place a data root can come from, alone and in competition.

    For each setup the guard's answer must be the command line's answer (``--home`` aside,
    which the server never passes): FATHOM_HOME before the walk up, the nearest marker
    before a farther one, a marker above before an unmarked working directory.
    """
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d)
        outer = _make_data_root(base / "outer")
        inner = _make_data_root(outer / "nested" / "inner")
        other = _make_data_root(base / "other")
        deep = inner / "tasks" / "example" / "add"
        deep.mkdir(parents=True)
        unmarked_inside = outer / "scratch"
        (unmarked_inside / "ledger").mkdir(parents=True)
        cases = {
            "walk up from deep inside": ({}, deep, inner),
            "walk up from the root itself": ({}, inner, inner),
            "the nearest marker wins": ({}, outer / "nested", outer),
            "FATHOM_HOME beats the walk up": ({"FATHOM_HOME": str(other)}, deep, other),
            "a relative FATHOM_HOME is taken from the working directory": (
                {"FATHOM_HOME": os.path.relpath(other, deep)},
                deep,
                other,
            ),
            "a blank FATHOM_HOME counts as unset": ({"FATHOM_HOME": "  "}, deep, inner),
            "a marker above beats an unmarked working directory": ({}, unmarked_inside, outer),
        }
        for name, (env, cwd, expected) in cases.items():
            cli = engine_home.resolve(None, env=env, cwd=cwd)
            guard = r.resolve_fathom_home(env, start=cwd, plugin_root=base / "plugin")
            assert cli.path.resolve() == expected.resolve(), name
            assert guard == expected.resolve(), name
            assert cli.marked, name


def test_only_the_command_line_accepts_an_unmarked_working_directory() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        unmarked = _make_data_root(pathlib.Path(d) / "unmarked", marker=None)
        found = engine_home.resolve(None, env={}, cwd=unmarked)
        assert found.path.resolve() == unmarked.resolve()
        assert not found.marked
        assert "not a fathom data root" in (found.warning() or "")
        msg = _error_of(lambda: r.resolve_fathom_home({}, start=unmarked))
    assert "marked data root" in msg
    assert "fathom init" in msg


# --- FATHOM_HOME: what is accepted ---------------------------------------------


def test_resolve_accepts_data_root_from_env() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        root = _make_data_root(pathlib.Path(d) / "data")
        assert r.resolve_fathom_home({"FATHOM_HOME": str(root)}) == root.resolve()


def test_a_data_root_needs_no_pyproject() -> None:
    # The server runs the engine the plugin ships, so the data root installs nothing.
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        root = _make_data_root(pathlib.Path(d) / "data")
        assert not (root / "pyproject.toml").exists()
        assert r.resolve_fathom_home({"FATHOM_HOME": str(root)}) == root.resolve()
        assert r.resolve_fathom_home({}, start=root / "ledger") == root.resolve()


def test_resolve_passes_over_a_fathom_toml_without_the_marker_table() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        outer = _make_data_root(pathlib.Path(d) / "outer")
        other = outer / "sub"
        other.mkdir()
        (other / "fathom.toml").write_text("[something_else]\nkey = 1\n", encoding="utf-8")
        assert r.resolve_fathom_home({}, start=other) == outer.resolve()


def test_engine_checkout_is_not_a_data_root() -> None:
    # The public engine ships no data: its root must never carry the marker, or a
    # plugin run started inside it would write a ledger into the engine tree.
    assert not engine_home.has_marker(_ROOT)
    assert engine_home.looks_like_engine_checkout(_ROOT)


# --- FATHOM_HOME: what is refused, and what the message says --------------------


def test_resolve_refuses_unset_and_undetectable() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        msg = _error_of(lambda: r.resolve_fathom_home({}, start=_plain_dir(d)))
    assert "FATHOM_HOME is not set" in msg
    assert "fathom.toml" in msg and "[data_root]" in msg
    assert "fathom init" in msg, "message must say how to make one"


def test_resolve_refuses_missing_directory() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        missing = pathlib.Path(d) / "absent"
        msg = _error_of(lambda: r.resolve_fathom_home({"FATHOM_HOME": str(missing)}))
    assert "not a directory" in msg


def test_resolve_refuses_directory_without_marker() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        root = _make_data_root(pathlib.Path(d) / "data", marker=None)
        msg = _error_of(lambda: r.resolve_fathom_home({"FATHOM_HOME": str(root)}))
    assert "has no fathom.toml" in msg
    assert "[data_root]" in msg and "schema = 1" in msg, "message must say how to make one"
    assert "fathom init" in msg


def test_resolve_refuses_engine_checkout_with_a_hint() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        engine = pathlib.Path(d) / "engine"
        (engine / "src" / "fathom").mkdir(parents=True)
        (engine / "tasks").mkdir()
        (engine / "pyproject.toml").write_text(
            '[project]\nname = "fathom"\nversion = "0.8.0"\n', encoding="utf-8"
        )
        msg = _error_of(lambda: r.resolve_fathom_home({"FATHOM_HOME": str(engine)}))
    assert "engine checkout" in msg
    assert "fathom init" not in msg.split("engine checkout")[0]


def test_resolve_refuses_fathom_toml_without_marker_table() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        root = _make_data_root(pathlib.Path(d) / "data", marker="data_root = 1\n")
        msg = _error_of(lambda: r.resolve_fathom_home({"FATHOM_HOME": str(root)}))
    assert "no [data_root] table" in msg


def test_resolve_refuses_unparseable_marker() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        root = _make_data_root(pathlib.Path(d) / "data", marker="[data_root\n")
        msg = _error_of(lambda: r.resolve_fathom_home({"FATHOM_HOME": str(root)}))
    assert "not valid TOML" in msg


def test_resolve_walk_up_stops_at_an_unparseable_marker() -> None:
    # A broken fathom.toml may have been meant as a marker; walking past it to an
    # outer data root would run against the wrong ledger.
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        outer = _make_data_root(pathlib.Path(d) / "outer")
        broken = outer / "inner"
        broken.mkdir()
        (broken / "fathom.toml").write_text("[data_root\n", encoding="utf-8")
        msg = _error_of(lambda: r.resolve_fathom_home({}, start=broken))
    assert "not valid TOML" in msg
    assert "stops there" in msg


# --- FATHOM_HOME: how the marker file is read ------------------------------------


def test_resolve_accepts_a_marker_with_a_utf8_byte_order_mark() -> None:
    # Common Windows editors, and Windows PowerShell 5.1's `-Encoding UTF8`, write one.
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        root = _make_data_root(pathlib.Path(d) / "data", marker=None)
        (root / "fathom.toml").write_bytes(codecs.BOM_UTF8 + _MARKER.encode("utf-8"))
        assert r.resolve_fathom_home({"FATHOM_HOME": str(root)}) == root.resolve()
        assert r.resolve_fathom_home({}, start=root / "tasks") == root.resolve()


def test_resolve_names_a_utf16_marker_rather_than_failing_to_decode_it() -> None:
    # What Windows PowerShell 5.1's `>` and Out-File write by default.
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        root = _make_data_root(pathlib.Path(d) / "data", marker=None)
        (root / "fathom.toml").write_text(_MARKER, encoding="utf-16")
        msg = _error_of(lambda: r.resolve_fathom_home({"FATHOM_HOME": str(root)}))
        msg_walk = _error_of(lambda: r.resolve_fathom_home({}, start=root / "tasks"))
    for text in (msg, msg_walk):
        assert "UTF-16 text" in text, text
        assert "must be UTF-8" in text, text
        assert "codec" not in text, "the decode error itself is not the message"


def test_resolver_and_reconcile_agree_on_what_marks_a_data_root() -> None:
    # The plugin resolves the data root with _resolve.py; `fathom reconcile` and
    # `fathom run` recognise it with fathom.ledgerindex. A marker one of them accepts
    # and the other refuses sends the plugin and the CLI to different directories.
    from fathom import ledgerindex

    r = _load_resolve()
    encodings = {
        "utf-8": _MARKER.encode("utf-8"),
        "utf-8 with a byte-order mark": codecs.BOM_UTF8 + _MARKER.encode("utf-8"),
        "utf-16": _MARKER.encode("utf-16"),
        "no [data_root] table": b"[other]\nkey = 1\n",
    }
    with tempfile.TemporaryDirectory() as d:
        for name, raw in encodings.items():
            root = _make_data_root(pathlib.Path(d) / name.replace(" ", "-"), marker=None)
            (root / "fathom.toml").write_bytes(raw)
            try:
                accepted = r.resolve_fathom_home({"FATHOM_HOME": str(root)}) == root.resolve()
            except r.FathomHomeError:
                accepted = False
            assert accepted == ledgerindex.is_data_root(root), name


# --- the plugin's own tree and its cache -----------------------------------------


def test_cache_clone_detection() -> None:
    r = _load_resolve()
    cache = pathlib.Path.home() / ".claude" / "plugins" / "cache" / "mkt" / "fathom" / "0.1.0"
    assert r._looks_like_cache_clone(cache) is True
    assert r._looks_like_cache_clone(_ROOT) is False


def test_resolve_refuses_cache_clone_even_with_a_marker() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        clone = pathlib.Path(d) / "plugins" / "cache" / "mkt" / "fathom" / "0.8.0"
        _make_data_root(clone)
        msg = _error_of(lambda: r.resolve_fathom_home({"FATHOM_HOME": str(clone)}))
        msg_walk = _error_of(lambda: r.resolve_fathom_home({}, start=clone / "tasks"))
    assert "plugin cache" in msg
    assert "plugin cache" in msg_walk


def test_resolve_refuses_plugin_root_and_anything_inside_it() -> None:
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        plugin = _make_data_root(pathlib.Path(d) / "plugin")
        fixture = _make_data_root(plugin / "examples" / "data-root")
        for candidate in (plugin, fixture):
            msg = _error_of(
                lambda c=candidate: r.resolve_fathom_home(
                    {"FATHOM_HOME": str(c)}, plugin_root=plugin
                )
            )
            assert "plugin's own tree" in msg
        # a data root beside the plugin, not inside it, is fine
        beside = _make_data_root(pathlib.Path(d) / "data")
        home = r.resolve_fathom_home({"FATHOM_HOME": str(beside)}, plugin_root=plugin)
        assert home == beside.resolve()


def test_by_default_the_plugin_tree_is_this_engine() -> None:
    # The example data root ships inside the plugin, so the server never runs against it.
    r = _load_resolve()
    example = _ROOT / "examples" / "data-root"
    msg = _error_of(lambda: r.resolve_fathom_home({"FATHOM_HOME": str(example)}))
    assert "plugin's own tree" in msg


# --- how the plugin invokes fathom ----------------------------------------------


def test_the_server_runs_the_plugins_engine_against_the_data_root() -> None:
    r = _load_resolve()
    home = pathlib.Path("/data/root")
    cmd = r.fathom_command(home, ["report", "example"])
    assert cmd[:6] == ["uv", "run", "--no-dev", "--frozen", "--project", str(_ROOT)]
    assert cmd[6:] == ["python", "-m", "fathom", "--home", str(home), "report", "example"]


def test_the_server_runs_the_engine_without_its_development_tools() -> None:
    """The engine needs no dependencies to run. Without --no-dev the first tool call installs
    the dev group (linters, test runner, hook manager) into the plugin's environment, and
    without --frozen uv may rewrite the lock file inside a plugin cache."""
    r = _load_resolve()
    cmd = r.fathom_command(pathlib.Path("/data/root"), ["smoke"])
    run_options = cmd[2 : cmd.index("python")]
    assert "--no-dev" in run_options
    assert "--frozen" in run_options


# --- the marker's schema ----------------------------------------------------------


def test_the_guard_refuses_a_data_root_of_another_schema() -> None:
    """A schema this engine does not read is refused, named, and never walked past."""
    r = _load_resolve()
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d)
        outer = _make_data_root(base / "outer")
        newer = _make_data_root(outer / "newer", marker="[data_root]\nschema = 2\n")
        deep = newer / "tasks"
        msg = _error_of(lambda: r.resolve_fathom_home({"FATHOM_HOME": str(newer)}))
        assert "schema = 2" in msg and "Upgrade fathom" in msg, msg
        msg = _error_of(lambda: r.resolve_fathom_home({}, start=deep, plugin_root=base / "p"))
        assert "schema = 2" in msg, "the walk up stopped at the newer root, not the outer one"
        for marker, phrase in (
            ("[data_root]\n", "has no schema"),
            ('[data_root]\nschema = "1"\n', "must be the integer 1"),
        ):
            (newer / "fathom.toml").write_text(marker, encoding="utf-8")
            msg = _error_of(lambda: r.resolve_fathom_home({"FATHOM_HOME": str(newer)}))
            assert phrase in msg, (marker, msg)


def test_plugin_invokes_fathom_as_module_not_console_script() -> None:
    # The `fathom` console-script .exe is blocked by Windows Smart App Control
    # (os error 4551); the plugin must run `python -m fathom` everywhere it
    # invokes fathom, so a fresh install works on a SAC-guarded host.
    runnable = [
        *sorted((_ROOT / "commands").glob("*.md")),
        _ROOT / "mcp" / "fathom_server.py",
        _ROOT / "mcp" / "_resolve.py",
    ]
    for path in runnable:
        text = path.read_text(encoding="utf-8")
        assert "uv run fathom " not in text, f"{path.name} invokes the SAC-blocked console script"
    server = (_ROOT / "mcp" / "fathom_server.py").read_text(encoding="utf-8")
    assert "fathom_command(" in server, "the MCP server must build its argv with fathom_command"


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
