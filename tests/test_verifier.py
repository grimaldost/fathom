"""Tests for src/fathom/grading/verifier.py — stdlib-runnable."""

import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.grading.verifier import extract_criteria, extract_result_view, run_verifier

# ---------------------------------------------------------------------------
# Inline verify.py fixture scripts — written to temp dirs during tests
# ---------------------------------------------------------------------------

_VERIFY_PASSING = """\
import json, sys
print(json.dumps({"criterion_a": True, "criterion_b": True}))
sys.exit(0)
"""

_VERIFY_FAILING = """\
import json, sys
print(json.dumps({"criterion_a": False, "criterion_b": True}))
sys.exit(1)
"""

_VERIFY_CRASHING = """\
raise RuntimeError("verifier crashed")
"""

_VERIFY_GARBAGE = """\
import sys
print("this is definitely not json")
sys.exit(0)
"""

# Captures argv and env keys; used for blindness assertions.
_VERIFY_CAPTURE = """\
import json, os, sys
print(json.dumps({
    "argv": sys.argv,
    "env_keys": sorted(os.environ.keys()),
}))
sys.exit(0)
"""

# Lists all files in the result view as a path→hex-bytes dict.
_VERIFY_LIST_TREE = """\
import json, os, sys
result_view = sys.argv[1]
tree = {}
for dirpath, dirnames, filenames in os.walk(result_view):
    dirnames.sort()
    for fname in sorted(filenames):
        fpath = os.path.join(dirpath, fname)
        rel = os.path.relpath(fpath, result_view).replace(os.sep, "/")
        with open(fpath, "rb") as f:
            tree[rel] = f.read().hex()
print(json.dumps(tree, sort_keys=True))
sys.exit(0)
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace(tmp: Path, name: str, files: dict) -> Path:
    ws = tmp / name
    ws.mkdir()
    for rel_path, content in files.items():
        dest = ws / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            dest.write_bytes(content)
        else:
            dest.write_text(content, encoding="utf-8")
    return ws


def _write_verify(tmp: Path, name: str, source: str) -> Path:
    p = tmp / name
    p.write_text(source, encoding="utf-8")
    return p


def _collect_tree(root: Path) -> dict:
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            rel = fpath.relative_to(root).as_posix()
            files[rel] = fpath.read_bytes()
    return files


# ---------------------------------------------------------------------------
# Three outcomes
# ---------------------------------------------------------------------------


def test_pass_with_criteria():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(tmp, "ws", {"main.py": "x = 1\n"})
        verify = _write_verify(tmp, "verify.py", _VERIFY_PASSING)
        result = run_verifier(verify, ws)
    assert result.outcome == "pass"
    assert result.criteria == {"criterion_a": True, "criterion_b": True}
    assert result.exit_code == 0


def test_fail_with_criteria():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(tmp, "ws", {"main.py": "x = 1\n"})
        verify = _write_verify(tmp, "verify.py", _VERIFY_FAILING)
        result = run_verifier(verify, ws)
    assert result.outcome == "fail"
    assert result.criteria == {"criterion_a": False, "criterion_b": True}
    assert result.exit_code != 0


def test_error_on_crash():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(tmp, "ws", {"main.py": "x = 1\n"})
        verify = _write_verify(tmp, "verify.py", _VERIFY_CRASHING)
        result = run_verifier(verify, ws)
    assert result.outcome == "error"
    assert result.criteria is None


def test_error_on_garbage_output():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(tmp, "ws", {"main.py": "x = 1\n"})
        verify = _write_verify(tmp, "verify.py", _VERIFY_GARBAGE)
        result = run_verifier(verify, ws)
    assert result.outcome == "error"
    assert result.criteria is None


def test_timeout_s_bounds_the_verifier():
    # A verifier slower than timeout_s → error (timed out); a generous timeout → pass.
    # Verifiers that shell out to heavy harnesses (e.g. pytest) may need large timeouts.
    script = "import json, sys, time\ntime.sleep(2)\nprint(json.dumps({'ok': True}))\nsys.exit(0)\n"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(tmp, "ws", {"main.py": "x = 1\n"})
        verify = _write_verify(tmp, "verify.py", script)
        timed_out = run_verifier(verify, ws, timeout_s=1)
        assert timed_out.outcome == "error"
        assert timed_out.criteria is None
        completed = run_verifier(verify, ws, timeout_s=20)
        assert completed.outcome == "pass"
        assert completed.criteria == {"ok": True}


def test_error_nonzero_with_garbage_output():
    """Non-JSON output with nonzero exit is still an error (not a scored fail)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(tmp, "ws", {"main.py": ""})
        # Exits 1 but no JSON
        src = "import sys\nprint('not json')\nsys.exit(1)\n"
        verify = _write_verify(tmp, "verify.py", src)
        result = run_verifier(verify, ws)
    assert result.outcome == "error"
    assert result.criteria is None


# ---------------------------------------------------------------------------
# Argv / env blindness
# ---------------------------------------------------------------------------


def test_argv_is_script_plus_result_view_only():
    """verify.py receives exactly two argv elements: script path + result view path."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(tmp, "ws", {"main.py": "x = 1\n"})
        verify = _write_verify(tmp, "capture.py", _VERIFY_CAPTURE)
        result = run_verifier(verify, ws)
    assert result.outcome == "pass"
    data = json.loads(result.stdout)
    assert len(data["argv"]) == 2, f"Expected 2 argv elements, got: {data['argv']}"
    assert "fathom-result-view-" in data["argv"][1], (
        f"argv[1] should be the temp result-view path, got: {data['argv'][1]}"
    )


def test_env_does_not_inherit_scenario_vars():
    """Verifier env is built minimal-explicit; fathom-specific vars are absent."""
    from fathom.grading.verifier import _SYSTEM_ENV_KEYS

    sentinel_key = "FATHOM_TEST_SCENARIO_SENTINEL"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(tmp, "ws", {"main.py": ""})
        verify = _write_verify(tmp, "capture.py", _VERIFY_CAPTURE)

        original = os.environ.get(sentinel_key)
        os.environ[sentinel_key] = "should_not_appear_in_verifier"
        try:
            result = run_verifier(verify, ws)
        finally:
            if original is None:
                os.environ.pop(sentinel_key, None)
            else:
                os.environ[sentinel_key] = original

    assert result.outcome == "pass"
    data = json.loads(result.stdout)
    assert sentinel_key not in data["env_keys"], f"{sentinel_key} leaked into verifier env"
    extra = set(data["env_keys"]) - _SYSTEM_ENV_KEYS
    assert not extra, f"env contains keys outside _SYSTEM_ENV_KEYS: {extra}"


_VERIFY_CWD = """\
import json, os, sys
print(json.dumps({
    "cwd": os.getcwd(),
    "cwd_entries": sorted(os.listdir(".")),
    "cwd_has_fathom": os.path.isdir(".fathom"),
}))
sys.exit(0)
"""


def test_the_verifier_does_not_start_in_the_data_root():
    """fathom runs with the data root as its working directory, and the data root holds
    `.fathom/streams/`, whose files are named after the arms. A verifier that inherits
    that directory can read which arm produced the result it scores (ADR-0003)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        data_root = tmp / "data-root"
        streams = data_root / ".fathom" / "streams" / "bank-x"
        streams.mkdir(parents=True)
        (streams / "bank-x--planted-arm-name--t--r0--a1--1.ndjson").write_text("{}\n")
        ws = _make_workspace(tmp, "ws", {"main.py": "x = 1\n"})
        verify = _write_verify(tmp, "cwd.py", _VERIFY_CWD)
        here = os.getcwd()
        os.chdir(data_root)
        try:
            result = run_verifier(verify, ws)
        finally:
            os.chdir(here)
    assert result.outcome == "pass", result
    data = json.loads(result.stdout)
    assert data["cwd_has_fathom"] is False, data
    assert data["cwd_entries"] == [], f"the verifier's working directory is not empty: {data}"
    assert "data-root" not in data["cwd"], data
    assert "planted-arm-name" not in result.stdout


# ---------------------------------------------------------------------------
# Result view extraction — per-artifact exclusions
# ---------------------------------------------------------------------------


def test_extract_excludes_tracker_jsonl():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                "tracker.jsonl": '{"event": "SUBAGENT_COMPLETE"}\n',
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert not (dest / "tracker.jsonl").exists()
        assert (dest / "main.py").exists()


def test_extract_excludes_outputs_dir():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                "outputs/review.log": "log content\n",
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert not (dest / "outputs").exists()
        assert (dest / "main.py").exists()


def test_extract_excludes_logs_dir():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                "logs/engine.log": "log content\n",
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert not (dest / "logs").exists()
        assert (dest / "main.py").exists()


def test_extract_excludes_stray_series_toml():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                "series.toml": '[series]\nid = "test"\n',
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert not (dest / "series.toml").exists()
        assert (dest / "main.py").exists()


def test_extract_excludes_stray_prompts_dir():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                "prompts/pr01.md": "# Prompt 1\n",
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert not (dest / "prompts").exists()
        assert (dest / "main.py").exists()


def test_extract_strips_the_automation_block_from_gitignore():
    """The fixture's lines stay; the block a series engine appended goes."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                ".gitignore": b"*.pyc\n# PR automation\n.engine-output/\n",
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert (dest / ".gitignore").read_bytes() == b"*.pyc\n"
        assert (dest / "main.py").exists()


def test_a_gitignore_holding_only_the_automation_block_is_left_out():
    """A series engine that finds no .gitignore creates one; the other arms have none."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp, "ws", {"main.py": "x = 1\n", ".gitignore": b"# PR automation\n.engine-output/\n"}
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert sorted(p.name for p in dest.iterdir()) == ["main.py"]


def test_a_fixture_gitignore_reads_the_same_whether_or_not_an_engine_appended_to_it():
    """The file's presence and its bytes must not tell a series trial apart (ADR-0003),
    however the fixture ends and however the engine separates its block."""
    fixtures = [b"*.pyc\n", b"*.pyc", b"*.pyc\n\n", b"*.pyc\r\nbuild/\r\n", b""]
    blocks = [b"# PR automation\n.engine-output/\n", b"\n# PR automation\n.engine-output/\n"]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for i, fixture in enumerate(fixtures):
            bare = _make_workspace(tmp, f"bare{i}", {"a.py": "x\n", ".gitignore": fixture})
            bare_view = tmp / f"bare{i}-view"
            bare_view.mkdir()
            extract_result_view(bare, bare_view)
            expected = _collect_tree(bare_view)
            for j, block in enumerate(blocks):
                series = _make_workspace(
                    tmp, f"series{i}-{j}", {"a.py": "x\n", ".gitignore": fixture + block}
                )
                series_view = tmp / f"series{i}-{j}-view"
                series_view.mkdir()
                extract_result_view(series, series_view)
                got = _collect_tree(series_view)
                assert got == expected, (repr(fixture), repr(block), got, expected)
                assert b"PR automation" not in got.get(".gitignore", b""), got


_VERIFY_PATH = """\
import json, os, sys
print(json.dumps({"path": os.environ.get("PATH", "").split(os.pathsep)}))
sys.exit(0)
"""


def test_the_verifier_path_names_no_withheld_directory():
    """`uv run fathom` from a data repository puts the data root's .venv on PATH; the
    verifier, and the agent code it shells out to, must not inherit that entry."""
    from fathom.adapters.claude_cli import hidden_from_children

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        data_root = tmp / "data-root"
        scripts = data_root / ".venv" / ("Scripts" if os.name == "nt" else "bin")
        scripts.mkdir(parents=True)
        ws = _make_workspace(tmp, "ws", {"main.py": ""})
        verify = _write_verify(tmp, "path.py", _VERIFY_PATH)
        original = os.environ.get("PATH")
        os.environ["PATH"] = os.pathsep.join([str(scripts), original or ""])
        try:
            with hidden_from_children(data_root):
                result = run_verifier(verify, ws)
        finally:
            if original is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = original
    assert result.outcome == "pass", result
    # Assertions name no entry: a failure message would print the machine's PATH.
    path = json.loads(result.stdout)["path"]
    leaked = str(scripts) in path
    assert not leaked, "the entry inside the data root reached the verifier"
    kept = [e for e in (original or "").split(os.pathsep) if e]
    same = [e for e in path if e] == kept
    assert same, "the other PATH entries must stay, in order"


def test_extract_preserves_gitignore_without_automation_marker():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                ".gitignore": "*.pyc\n__pycache__/\n",
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert (dest / ".gitignore").exists()
        assert (dest / ".gitignore").read_text(encoding="utf-8") == "*.pyc\n__pycache__/\n"


def test_extract_does_not_modify_workspace():
    """extract_result_view copies; it never mutates the source workspace."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                "series.toml": "[series]\n",
            },
        )
        original_files = {p.name for p in ws.iterdir()}
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        after_files = {p.name for p in ws.iterdir()}
        assert original_files == after_files


def test_extract_skips_git_dir():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(tmp, "ws", {"main.py": "x = 1\n"})
        (ws / ".git").mkdir()
        (ws / ".git" / "config").write_text("[core]\n", encoding="utf-8")
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert not (dest / ".git").exists()
        assert (dest / "main.py").exists()


def test_extract_preserves_nested_dirs():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "src/app.py": "def main(): pass\n",
                "tests/test_app.py": "def test_main(): pass\n",
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert (dest / "src" / "app.py").exists()
        assert (dest / "tests" / "test_app.py").exists()


# ---------------------------------------------------------------------------
# Blindness fixture: bare vs series-style workspace → byte-identical result view
# ---------------------------------------------------------------------------


def test_blindness_bare_vs_series_identical():
    """A bare and a series-style workspace with identical code yield identical result views.

    The series-style workspace contains all engine artifact types
    (series.toml, prompts/, tracker.jsonl, outputs/, logs/). After extraction
    these are absent, leaving byte-identical content for the verifier.
    """
    solution_code = "def add(a, b):\n    return a + b\n"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        bare_ws = _make_workspace(tmp, "bare", {"solution.py": solution_code})

        series_ws = _make_workspace(
            tmp,
            "series",
            {
                "solution.py": solution_code,
                "series.toml": '[series]\nid = "test-scenario"\n',
                "prompts/pr01.md": "# Prompt for PR01\n",
                "prompts/pr02.md": "# Prompt for PR02\n",
                "tracker.jsonl": '{"event": "SUBAGENT_COMPLETE"}\n',
                "outputs/fix.log": "fix log\n",
                "logs/engine.log": "engine log\n",
            },
        )

        bare_dest = tmp / "bare_result"
        series_dest = tmp / "series_result"
        bare_dest.mkdir()
        series_dest.mkdir()

        extract_result_view(bare_ws, bare_dest)
        extract_result_view(series_ws, series_dest)

        bare_tree = _collect_tree(bare_dest)
        series_tree = _collect_tree(series_dest)

    assert bare_tree == series_tree, (
        f"Result views differ:\n  bare files: {sorted(bare_tree)}"
        f"\n  series files: {sorted(series_tree)}"
    )


# ---------------------------------------------------------------------------
# Scaffolding scrub — plugin process-scaffolding dirs are excluded
# ---------------------------------------------------------------------------


def test_extract_excludes_remember_dir():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                ".remember/now.md": "# buffer\n",
                ".remember/recent.md": "# 7d\n",
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert not (dest / ".remember").exists()
        assert (dest / "main.py").exists()


def test_extract_excludes_plans_dir():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                "plans/plan.md": "# Plan\n",
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert not (dest / "plans").exists()
        assert (dest / "main.py").exists()


def test_extract_excludes_docs_plans_dir():
    """docs/ itself is kept; docs/plans/ (scaffolding subdir) is stripped."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                "docs/README.md": "# Docs\n",
                "docs/plans/design.md": "# Design plan\n",
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert (dest / "docs").exists()
        assert (dest / "docs" / "README.md").exists()
        assert not (dest / "docs" / "plans").exists()
        assert (dest / "main.py").exists()


def test_extract_excludes_journal_dir():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                "journal/session.md": "# Session\n",
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert not (dest / "journal").exists()
        assert (dest / "main.py").exists()


def test_blindness_with_without_scaffolding_identical():
    """Verifier output is identical for workspace with and without scaffolding dirs.

    A verifier keys only on task deliverables; this test confirms that
    scaffolding dirs do not bleed into what the verifier sees (ADR-0003).
    """
    solution_code = "def hello(): return 'world'\n"
    docs_content = "# Project docs\n"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        clean_ws = _make_workspace(
            tmp,
            "clean",
            {
                "solution.py": solution_code,
                "docs/README.md": docs_content,
            },
        )

        scaffolded_ws = _make_workspace(
            tmp,
            "scaffolded",
            {
                "solution.py": solution_code,
                "docs/README.md": docs_content,
                # scaffolding dirs that should be stripped
                ".remember/now.md": "# buffer\n",
                ".remember/core-memories.md": "# memories\n",
                "plans/plan.md": "# Plan\n",
                "docs/plans/design.md": "# Design\n",
                "journal/session.md": "# Session\n",
            },
        )

        verify = _write_verify(tmp, "list_tree.py", _VERIFY_LIST_TREE)

        clean_result = run_verifier(verify, clean_ws)
        scaffolded_result = run_verifier(verify, scaffolded_ws)

    assert clean_result.outcome == "pass"
    assert scaffolded_result.outcome == "pass"
    assert clean_result.stdout == scaffolded_result.stdout, (
        f"Verifier output differs with scaffolding present:"
        f"\n  clean:      {clean_result.stdout}"
        f"\n  scaffolded: {scaffolded_result.stdout}"
    )


# ---------------------------------------------------------------------------
# End-to-end: verifier sees only the result view, engine artifacts absent
# ---------------------------------------------------------------------------


def test_verifier_sees_excluded_artifacts_removed():
    """verify.py only sees the result view; engine artifacts are not present."""
    verify_src = """\
import json, os, sys
result_view = sys.argv[1]
files = sorted(
    os.path.relpath(os.path.join(d, f), result_view).replace(os.sep, "/")
    for d, _, fs in os.walk(result_view)
    for f in fs
)
print(json.dumps({"files": files}))
sys.exit(0)
"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "solution.py": "x = 1\n",
                "tracker.jsonl": "junk\n",
                "series.toml": "[series]\n",
                "prompts/pr01.md": "prompt\n",
                "outputs/fix.log": "fix log\n",
            },
        )
        verify = _write_verify(tmp, "verify.py", verify_src)
        result = run_verifier(verify, ws)

    assert result.outcome == "pass"
    data = json.loads(result.stdout)
    assert data["files"] == ["solution.py"], f"Unexpected files in result view: {data['files']}"


# ---------------------------------------------------------------------------
# Criteria recovery from a noisy stdout
#
# A verifier that checks behaviour-preservation has to IMPORT the agent's modified
# package, so whatever that package prints at import time lands on the verifier's
# stdout ahead of its answer. Requiring the WHOLE of stdout to parse threw away
# trials whose criteria had been computed correctly — and threw them away in an
# ARM-CORRELATED way, since whether the agent adds a print is a property of the arm
# being measured. That is a silent bias, not merely a lost trial.
#
# Solution: scan lines back-to-front and take the LAST line that parses as JSON.
# Noise before the criteria does not interfere; the criteria line is the last thing
# a verifier emits, so a debug dict printed earlier never wins.
# ---------------------------------------------------------------------------


def test_a_leading_print_does_not_destroy_the_result():
    stdout = 'loading config\n{"behavior_preserved": true, "uv": false}\n'
    assert extract_criteria(stdout) == {"behavior_preserved": True, "uv": False}


def test_trailing_noise_is_tolerated():
    assert extract_criteria('{"a": true}\nteardown complete\n') == {"a": True}


def test_plain_json_still_works():
    assert extract_criteria('{"a": true}') == {"a": True}
    assert extract_criteria('  {"a": false}  \n') == {"a": False}


def test_the_last_object_wins_when_several_are_printed():
    # The criteria line is the last thing a verifier emits, so a debug dict printed
    # earlier must never be mistaken for the answer.
    stdout = '{"debug": true}\n{"a": true, "b": false}\n'
    assert extract_criteria(stdout) == {"a": True, "b": False}


def test_genuinely_absent_json_is_still_an_error():
    # The tolerance must not degrade into "find something, anything": a verifier
    # that crashed before printing has to stay unscoreable.
    assert extract_criteria("Traceback (most recent call last):\n  boom\n") is None
    assert extract_criteria("") is None


def test_a_non_dict_json_document_is_still_an_error():
    assert extract_criteria("[1, 2, 3]") is None
    assert extract_criteria('"just a string"') is None


def test_a_brace_inside_a_log_line_does_not_confuse_it():
    assert extract_criteria('loaded config {broken: yes}\n{"a": true}\n') == {"a": True}


def test_run_verifier_recovers_criteria_past_an_import_time_print():
    """End to end through the real subprocess boundary, not just the parser."""
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        ws = _make_workspace(t, "ws", {"a.txt": "x"})
        verify = _write_verify(
            t,
            "verify_noisy.py",
            "import json, sys\n"
            "print('configuring something')\n"
            'print(json.dumps({"criterion_a": True}))\n'
            "sys.exit(0)\n",
        )
        result = run_verifier(verify, ws)
        assert result.outcome == "pass", result
        assert result.criteria == {"criterion_a": True}


# ---------------------------------------------------------------------------
# stdlib runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_a_leading_print_does_not_destroy_the_result,
        test_trailing_noise_is_tolerated,
        test_plain_json_still_works,
        test_the_last_object_wins_when_several_are_printed,
        test_genuinely_absent_json_is_still_an_error,
        test_a_non_dict_json_document_is_still_an_error,
        test_a_brace_inside_a_log_line_does_not_confuse_it,
        test_run_verifier_recovers_criteria_past_an_import_time_print,
        test_pass_with_criteria,
        test_fail_with_criteria,
        test_error_on_crash,
        test_error_on_garbage_output,
        test_error_nonzero_with_garbage_output,
        test_argv_is_script_plus_result_view_only,
        test_env_does_not_inherit_scenario_vars,
        test_the_verifier_does_not_start_in_the_data_root,
        test_extract_excludes_tracker_jsonl,
        test_extract_excludes_outputs_dir,
        test_extract_excludes_logs_dir,
        test_extract_excludes_stray_series_toml,
        test_extract_excludes_stray_prompts_dir,
        test_extract_strips_the_automation_block_from_gitignore,
        test_a_gitignore_holding_only_the_automation_block_is_left_out,
        test_a_fixture_gitignore_reads_the_same_whether_or_not_an_engine_appended_to_it,
        test_the_verifier_path_names_no_withheld_directory,
        test_extract_preserves_gitignore_without_automation_marker,
        test_extract_does_not_modify_workspace,
        test_extract_skips_git_dir,
        test_extract_preserves_nested_dirs,
        test_blindness_bare_vs_series_identical,
        test_verifier_sees_excluded_artifacts_removed,
        test_extract_excludes_remember_dir,
        test_extract_excludes_plans_dir,
        test_extract_excludes_docs_plans_dir,
        test_extract_excludes_journal_dir,
        test_blindness_with_without_scaffolding_identical,
    ]

    failures = []
    for test_fn in tests:
        try:
            test_fn()
        except Exception:
            failures.append(test_fn.__name__)
            traceback.print_exc()
            print()

    if failures:
        print(f"FAILED: {len(failures)}/{len(tests)} — {', '.join(failures)}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"All {len(tests)} tests passed!")
