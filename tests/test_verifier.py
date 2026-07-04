"""Tests for src/fathom/grading/verifier.py — stdlib-runnable."""

import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.grading.verifier import extract_result_view, run_verifier

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
    # Backs the ADR-0008 §5 / FM-8 real-anchor harness, whose venv pytest exceeds 60s.
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


def test_extract_excludes_gitignore_with_automation_marker():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = _make_workspace(
            tmp,
            "ws",
            {
                "main.py": "x = 1\n",
                ".gitignore": "*.pyc\n# PR automation\n.pr-outputs/\n",
            },
        )
        dest = tmp / "result"
        dest.mkdir()
        extract_result_view(ws, dest)
        assert not (dest / ".gitignore").exists()
        assert (dest / "main.py").exists()


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
# Scaffolding scrub (§10) — plugin process-scaffolding dirs are excluded
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

    Phase-1 verifiers key only on task deliverables; this test confirms that
    scaffolding dirs do not bleed into what the verifier sees (§10, ADR-0003).
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
# stdlib runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_pass_with_criteria,
        test_fail_with_criteria,
        test_error_on_crash,
        test_error_on_garbage_output,
        test_error_nonzero_with_garbage_output,
        test_argv_is_script_plus_result_view_only,
        test_env_does_not_inherit_scenario_vars,
        test_extract_excludes_tracker_jsonl,
        test_extract_excludes_outputs_dir,
        test_extract_excludes_logs_dir,
        test_extract_excludes_stray_series_toml,
        test_extract_excludes_stray_prompts_dir,
        test_extract_excludes_gitignore_with_automation_marker,
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
