"""Schema and command checks for the fathom MCP server.

This imports fastmcp, so it is NOT part of fathom's stdlib-only core suite — it
lives at plugin scope. Run it under an env that has fastmcp:

    uv run --with "fastmcp>=2.0" --with pytest python -m pytest mcp/test_server_schema.py

Two guards:

- every tool parameter carries a schema description, because a parameter
  without one is a feature that does not exist for a blind agent;
- every tool runs the engine the plugin ships against the data root,
  ``uv run --no-dev --frozen --project <plugin root> python -m fathom --home <data root>
  ...``, with the
  data root as the working directory, and refuses to run anything when no data root
  resolves. ``subprocess.run`` is replaced, so nothing is spawned.
"""

from __future__ import annotations

import asyncio
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))


def _tool_properties() -> dict[str, dict]:
    import fathom_server

    server = fathom_server.mcp
    if hasattr(server, "list_tools"):  # fastmcp 3 and later: list[FunctionTool]
        tools = list(asyncio.run(server.list_tools()))
    else:  # fastmcp 2: {name: FunctionTool}
        tools = list(asyncio.run(server.get_tools()).values())
    return {t.name: (t.parameters or {}).get("properties", {}) for t in tools}


def test_expected_tools_present() -> None:
    assert set(_tool_properties()) == {"plan", "report", "smoke"}


def test_every_tool_parameter_is_described() -> None:
    for tool_name, props in _tool_properties().items():
        for param, spec in props.items():
            assert spec.get("description", "").strip(), (
                f"{tool_name}.{param} has no schema description"
            )


# --- the commands each tool runs -------------------------------------------------


def _call(tool, **kwargs):
    """Call a tool's function directly (fastmcp 2 wraps it in ``.fn``; later versions do not)."""
    return asyncio.run(getattr(tool, "fn", tool)(**kwargs))


@pytest.fixture
def data_root(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    # No pyproject.toml: the engine comes from the plugin root, not the data root.
    root = tmp_path / "data"
    for sub in ("tasks", "scenarios", "ledger"):
        (root / sub).mkdir(parents=True)
    (root / "fathom.toml").write_text("[data_root]\nschema = 1\n", encoding="utf-8")
    monkeypatch.setenv("FATHOM_HOME", str(root))
    return root.resolve()


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    import fathom_server

    seen: list[dict] = []

    def fake_run(cmd, *, cwd, env, capture_output, text, timeout):
        seen.append({"cmd": list(cmd), "cwd": pathlib.Path(cwd), "env": dict(env)})
        return subprocess.CompletedProcess(cmd, 0, stdout="stdout text", stderr="")

    monkeypatch.setattr(fathom_server.subprocess, "run", fake_run)
    return seen


def _prefix(home: pathlib.Path) -> list[str]:
    import _resolve

    engine = str(_resolve.PLUGIN_ROOT)
    return [
        *("uv", "run", "--no-dev", "--frozen", "--project", engine),
        *("python", "-m", "fathom", "--home", str(home)),
    ]


def test_the_engine_is_the_plugin_root() -> None:
    """The server runs the engine it ships in, whatever the data root installs."""
    import _resolve

    assert (_resolve.PLUGIN_ROOT / "src" / "fathom" / "cli.py").is_file()
    here = pathlib.Path(__file__).resolve().parent
    assert here.parent == _resolve.PLUGIN_ROOT


def test_plan_runs_a_dry_run_in_the_data_root(data_root, calls) -> None:
    import fathom_server

    out = _call(
        fathom_server.plan,
        bank="example-v1",
        repeats=3,
        scenarios_dir="scenarios/example",
        tasks_dir="tasks",
        limit=4,
        include_holdout=True,
    )
    assert out["ok"] is True
    assert out["home"] == str(data_root)
    assert out["plan"] == "stdout text"
    [call] = calls
    assert call["cwd"] == data_root
    assert call["cmd"] == [
        *_prefix(data_root),
        "run",
        "example-v1",
        "--dry-run",
        "--repeats",
        "3",
        "--scenarios-dir",
        "scenarios/example",
        "--tasks-dir",
        "tasks",
        "--limit",
        "4",
        "--include-holdout",
    ]


def test_report_runs_in_the_data_root_and_finds_the_scorecard(data_root, calls) -> None:
    import fathom_server

    (data_root / "report").mkdir()
    (data_root / "report" / "scorecard-example-v1.md").write_text("# card\n", encoding="utf-8")
    out = _call(fathom_server.report, bank="example-v1")
    [call] = calls
    assert call["cwd"] == data_root
    assert call["cmd"] == [*_prefix(data_root), "report", "example-v1"]
    assert out["scorecard_path"] == str(data_root / "report" / "scorecard-example-v1.md")


def test_the_engine_does_not_inherit_the_server_virtual_environment(
    data_root, calls, monkeypatch
) -> None:
    """The server's own temporary environment would make every engine call warn."""
    import fathom_server

    monkeypatch.setenv("VIRTUAL_ENV", str(data_root / "server-env"))
    monkeypatch.setenv("KEEP_ME", "yes")
    _call(fathom_server.plan, bank="example-v1")
    [call] = calls
    assert not {k for k in call["env"] if k.upper() == "VIRTUAL_ENV"}
    assert call["env"]["KEEP_ME"] == "yes"
    assert "FATHOM_HOME" in call["env"]


def test_smoke_passes_its_flags(data_root, calls) -> None:
    import fathom_server

    _call(fathom_server.smoke, force_fail=True, no_engine_boundary=True)
    [call] = calls
    assert call["cwd"] == data_root
    assert call["cmd"] == [*_prefix(data_root), "smoke", "--force-fail", "--no-engine-boundary"]


def test_tools_spawn_nothing_without_a_data_root(tmp_path, monkeypatch, calls) -> None:
    import fathom_server

    not_a_root = tmp_path / "plain"
    (not_a_root / "ledger").mkdir(parents=True)
    unset = tmp_path / "elsewhere"
    unset.mkdir()
    for setup in ("unmarked FATHOM_HOME", "nothing found"):
        if setup == "unmarked FATHOM_HOME":
            monkeypatch.setenv("FATHOM_HOME", str(not_a_root))
        else:
            monkeypatch.delenv("FATHOM_HOME", raising=False)
            monkeypatch.chdir(unset)
        for tool, kwargs in (
            (fathom_server.plan, {"bank": "example-v1"}),
            (fathom_server.report, {"bank": "example-v1"}),
            (fathom_server.smoke, {}),
        ):
            out = _call(tool, **kwargs)
            assert out["ok"] is False, setup
            assert "fathom.toml" in out["error"] and "[data_root]" in out["error"], setup
            assert "fathom init" in out["error"], setup
    assert calls == []


def test_an_unmarked_working_directory_is_refused(tmp_path, monkeypatch, calls) -> None:
    """The command line would use it with a warning; a tool call has nowhere to warn."""
    import fathom_server

    unmarked = tmp_path / "unmarked"
    (unmarked / "tasks").mkdir(parents=True)
    monkeypatch.delenv("FATHOM_HOME", raising=False)
    monkeypatch.chdir(unmarked)
    out = _call(fathom_server.plan, bank="example-v1")
    assert out["ok"] is False
    assert "marked data root" in out["error"]
    assert calls == []


def test_the_example_data_root_inside_the_plugin_is_refused(monkeypatch, calls) -> None:
    """A ledger written inside the plugin's tree is deleted by the next cache refresh."""
    import _resolve
    import fathom_server

    monkeypatch.setenv("FATHOM_HOME", str(_resolve.PLUGIN_ROOT / "examples" / "data-root"))
    out = _call(fathom_server.report, bank="example")
    assert out["ok"] is False
    assert "plugin's own tree" in out["error"]
    assert calls == []
