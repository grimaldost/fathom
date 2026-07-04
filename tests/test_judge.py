"""Tests for src/fathom/grading/judge.py — stdlib-runnable.

Covers: agreement → win; disagreement → tie; repeat-index pairing;
diff payload with size cap + truncation marker; judge prompt contains A/B
result-view diffs but no scenario names; grading records carry judge model
and judge config hash.
"""

import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.adapters.base import ExitStatus, RunRecord
from fathom.grading.judge import (
    JudgeConfig,
    build_judge_prompt,
    decide_pairwise,
    extract_verdict,
    judge_pairs,
    render_result_diff,
)
from fathom.scenario import (
    LimitsOverride,
    ResolvedScenario,
    ToolsConfig,
    compute_config_hash,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scenario(name: str = "judge-test") -> ResolvedScenario:
    return ResolvedScenario(
        name=name,
        adapter="claude-cli",
        model="claude-test-1",
        strategy="single-session",
        effort="normal",
        tools=ToolsConfig(source="none"),
        limits=LimitsOverride(),
        model_id="claude-test-1",
        tool_repo_sha=None,
        tool_invocation_cmd=None,
        config_hash="abc123",
    )


class StubRunner:
    """Captures calls and returns pre-canned RunRecord responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def execute(self, prompt, workspace, scenario):
        self.calls.append({"prompt": prompt, "workspace": workspace, "scenario": scenario})
        resp = self._responses.pop(0)
        return RunRecord(
            status=ExitStatus.OK,
            result_text=resp.get("result_text", "{}"),
            model_id=resp.get("model_id", "claude-test-1"),
            cli_version=resp.get("cli_version", "1.0.0"),
        )


def _resp(winner: str, model_id: str = "claude-test-1", cli_version: str = "1.0.0") -> dict:
    return {
        "result_text": f'{{"winner": "{winner}", "reason": "test"}}',
        "model_id": model_id,
        "cli_version": cli_version,
    }


def _make_dir(tmp: Path, name: str, files: dict) -> Path:
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return d


_BASELINE = {"main.py": "def foo():\n    pass\n"}
_VIEW_A = {"main.py": "def foo():\n    return 42\n"}
_VIEW_B = {"main.py": "def foo():\n    return 99\n"}

_DEFAULT_CFG = JudgeConfig(model="claude-test-1", max_bytes=65536)
_DEFAULT_SCENARIO = _make_scenario()


def _run_judge(tmp, runner, view_a_files=None, view_b_files=None, *, config=None, scenario=None):
    """Create dirs and run judge_pairs with one pair."""
    baseline = _make_dir(tmp, "baseline", _BASELINE)
    view_a = _make_dir(tmp, "view_a", view_a_files or _VIEW_A)
    view_b = _make_dir(tmp, "view_b", view_b_files or _VIEW_B)
    return judge_pairs(
        pairs=[(view_a, view_b)],
        baseline=baseline,
        runner=runner,
        judge_scenario=scenario or _DEFAULT_SCENARIO,
        judge_config=config or _DEFAULT_CFG,
        bank="test-bank",
        task_id="task-1",
        dataset_version="v1",
        config_hash_a="hash-a",
        config_hash_b="hash-b",
        tool_git_sha="sha-abc",
        pin_level="strong",
    )


# ---------------------------------------------------------------------------
# Pure: decide_pairwise
# ---------------------------------------------------------------------------


def test_decide_pairwise_agreement_a():
    result = decide_pairwise("A", "A")
    assert result["winner"] == "A"
    assert result["agreement"] is True


def test_decide_pairwise_agreement_b():
    result = decide_pairwise("B", "B")
    assert result["winner"] == "B"
    assert result["agreement"] is True


def test_decide_pairwise_disagreement():
    result = decide_pairwise("A", "B")
    assert result["winner"] == "tie"


def test_decide_pairwise_explicit_tie():
    result = decide_pairwise("tie", "tie")
    assert result["winner"] == "tie"


def test_decide_pairwise_mixed_tie():
    result = decide_pairwise("A", "tie")
    assert result["winner"] == "tie"


# ---------------------------------------------------------------------------
# Pure: extract_verdict
# ---------------------------------------------------------------------------


def test_extract_verdict_plain_json():
    result = extract_verdict('{"winner": "first", "reason": "better"}')
    assert result == {"winner": "first", "reason": "better"}


def test_extract_verdict_fenced():
    result = extract_verdict('```json\n{"winner": "first"}\n```')
    assert result == {"winner": "first"}


def test_extract_verdict_none_on_empty():
    assert extract_verdict("") is None
    assert extract_verdict("no json here") is None


# ---------------------------------------------------------------------------
# Payload: render_result_diff
# ---------------------------------------------------------------------------


def test_render_result_diff_shows_changes():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        baseline = _make_dir(tmp, "baseline", {"main.py": "x = 1\n"})
        result_view = _make_dir(tmp, "result", {"main.py": "x = 2\n"})
        diff, truncated = render_result_diff(result_view, baseline, max_bytes=65536)
    assert "x = 1" in diff
    assert "x = 2" in diff
    assert not truncated


def test_render_result_diff_new_file():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        baseline = _make_dir(tmp, "baseline", {})
        result_view = _make_dir(tmp, "result", {"new.py": "def new(): pass\n"})
        diff, truncated = render_result_diff(result_view, baseline, max_bytes=65536)
    assert "new.py" in diff
    assert not truncated


def test_render_result_diff_deleted_file():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        baseline = _make_dir(tmp, "baseline", {"old.py": "x = 1\n"})
        result_view = _make_dir(tmp, "result", {})
        diff, truncated = render_result_diff(result_view, baseline, max_bytes=65536)
    assert "old.py" in diff
    assert not truncated


def test_render_result_diff_size_cap():
    big_content = "x = " + "a" * 500 + "\n"
    many_lines = big_content * 200
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        baseline = _make_dir(tmp, "baseline", {"big.py": ""})
        result_view = _make_dir(tmp, "result", {"big.py": many_lines})
        diff, truncated = render_result_diff(result_view, baseline, max_bytes=100)
    assert truncated
    assert "TRUNCATED" in diff


def test_render_result_diff_identical_no_diff():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        baseline = _make_dir(tmp, "baseline", {"main.py": "x = 1\n"})
        result_view = _make_dir(tmp, "result", {"main.py": "x = 1\n"})
        diff, truncated = render_result_diff(result_view, baseline, max_bytes=65536)
    assert diff == ""
    assert not truncated


def test_render_result_diff_truncation_marker_format():
    """Truncated diff ends with a marker recording bytes omitted."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        baseline = _make_dir(tmp, "baseline", {"f.py": ""})
        result_view = _make_dir(tmp, "result", {"f.py": "x\n" * 1000})
        diff, truncated = render_result_diff(result_view, baseline, max_bytes=50)
    assert truncated
    assert "bytes omitted" in diff


# ---------------------------------------------------------------------------
# Judge prompt
# ---------------------------------------------------------------------------


def test_build_judge_prompt_contains_diffs():
    prompt = build_judge_prompt("--- diff content A ---", "--- diff content B ---")
    assert "diff content A" in prompt
    assert "diff content B" in prompt


def test_build_judge_prompt_strict_json_instruction():
    prompt = build_judge_prompt("diff a", "diff b")
    assert "JSON" in prompt or "json" in prompt


def test_build_judge_prompt_no_hardcoded_scenario_names():
    """No v1 scenario names embedded in the static rubric text."""
    for scenario_name in ("bare", "series", "single-long-session"):
        prompt = build_judge_prompt("some changes", "other changes")
        assert scenario_name not in prompt.lower(), (
            f"Hardcoded scenario name '{scenario_name}' found in judge prompt"
        )


# ---------------------------------------------------------------------------
# judge_pairs: swap-order agreement → win
# ---------------------------------------------------------------------------


def test_judge_pairs_agreement_a_wins():
    # Order 1 (A first): judge says "first" → A wins (w1="A")
    # Order 2 (B first): judge says "second" → A wins (w2="A")
    runner = StubRunner([_resp("first"), _resp("second")])
    with tempfile.TemporaryDirectory() as tmp:
        records = _run_judge(Path(tmp), runner)
    assert len(records) == 1
    assert records[0].verdict == "a"


def test_judge_pairs_agreement_b_wins():
    # Order 1 (A first): judge says "second" → B wins (w1="B")
    # Order 2 (B first): judge says "first" → B wins (w2="B")
    runner = StubRunner([_resp("second"), _resp("first")])
    with tempfile.TemporaryDirectory() as tmp:
        records = _run_judge(Path(tmp), runner)
    assert len(records) == 1
    assert records[0].verdict == "b"


def test_judge_pairs_disagreement_tie():
    # Order 1 (A first): judge says "first" → A wins (w1="A")
    # Order 2 (B first): judge says "first" → B wins (w2="B")  — disagreement
    runner = StubRunner([_resp("first"), _resp("first")])
    with tempfile.TemporaryDirectory() as tmp:
        records = _run_judge(Path(tmp), runner)
    assert len(records) == 1
    assert records[0].verdict == "tie"


def test_judge_pairs_explicit_tie_response():
    runner = StubRunner([_resp("tie"), _resp("tie")])
    with tempfile.TemporaryDirectory() as tmp:
        records = _run_judge(Path(tmp), runner)
    assert records[0].verdict == "tie"


def test_judge_pairs_exactly_two_runner_calls_per_pair():
    """Each pair must trigger exactly two runner calls (the two orders)."""
    runner = StubRunner([_resp("first"), _resp("second")])
    with tempfile.TemporaryDirectory() as tmp:
        _run_judge(Path(tmp), runner)
    assert len(runner.calls) == 2


# ---------------------------------------------------------------------------
# Repeat-index pairing
# ---------------------------------------------------------------------------


def test_judge_pairs_repeat_index():
    """Two pairs produce two GradingRecords with correct repeat indices and verdicts."""
    runner = StubRunner(
        [
            _resp("first"),  # pair0, order1: A first → A wins
            _resp("second"),  # pair0, order2: B first → A wins
            _resp("second"),  # pair1, order1: A first → B wins
            _resp("first"),  # pair1, order2: B first → B wins
        ]
    )
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        baseline = _make_dir(tmp, "baseline", _BASELINE)
        a0 = _make_dir(tmp, "a0", _VIEW_A)
        b0 = _make_dir(tmp, "b0", _VIEW_B)
        a1 = _make_dir(tmp, "a1", _VIEW_A)
        b1 = _make_dir(tmp, "b1", _VIEW_B)
        records = judge_pairs(
            pairs=[(a0, b0), (a1, b1)],
            baseline=baseline,
            runner=runner,
            judge_scenario=_DEFAULT_SCENARIO,
            judge_config=_DEFAULT_CFG,
            bank="test-bank",
            task_id="task-1",
            dataset_version="v1",
            config_hash_a="hash-a",
            config_hash_b="hash-b",
            tool_git_sha="sha-abc",
            pin_level="strong",
        )
    assert len(records) == 2
    assert records[0].repeat == 0
    assert records[1].repeat == 1
    assert records[0].verdict == "a"
    assert records[1].verdict == "b"


def test_judge_pairs_four_calls_for_two_pairs():
    runner = StubRunner([_resp("first"), _resp("second"), _resp("first"), _resp("second")])
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        baseline = _make_dir(tmp, "baseline", _BASELINE)
        a0 = _make_dir(tmp, "a0", _VIEW_A)
        b0 = _make_dir(tmp, "b0", _VIEW_B)
        a1 = _make_dir(tmp, "a1", _VIEW_A)
        b1 = _make_dir(tmp, "b1", _VIEW_B)
        judge_pairs(
            pairs=[(a0, b0), (a1, b1)],
            baseline=baseline,
            runner=runner,
            judge_scenario=_DEFAULT_SCENARIO,
            judge_config=_DEFAULT_CFG,
            bank="test-bank",
            task_id="task-1",
            dataset_version="v1",
            config_hash_a="hash-a",
            config_hash_b="hash-b",
            tool_git_sha="sha-abc",
            pin_level="strong",
        )
    assert len(runner.calls) == 4


# ---------------------------------------------------------------------------
# Grading records carry judge model and config hash
# ---------------------------------------------------------------------------


def test_grading_record_judge_model():
    runner = StubRunner(
        [
            _resp("first", model_id="claude-sonnet-resolved"),
            _resp("second", model_id="claude-sonnet-resolved"),
        ]
    )
    with tempfile.TemporaryDirectory() as tmp:
        records = _run_judge(Path(tmp), runner)
    assert records[0].judge_model == "claude-sonnet-resolved"


def test_grading_record_judge_config_hash():
    config = JudgeConfig(model="claude-test-1", max_bytes=65536)
    runner = StubRunner([_resp("first"), _resp("second")])
    with tempfile.TemporaryDirectory() as tmp:
        records = _run_judge(Path(tmp), runner, config=config)
    expected = compute_config_hash(
        {
            "effort": config.effort,
            "max_budget_usd": config.max_budget_usd,
            "max_bytes": config.max_bytes,
            "model": config.model,
            "timeout_s": config.timeout_s,
        }
    )
    assert records[0].judge_config_hash == expected


def test_grading_record_metadata_fields():
    runner = StubRunner([_resp("first"), _resp("second")])
    with tempfile.TemporaryDirectory() as tmp:
        records = _run_judge(Path(tmp), runner)
    r = records[0]
    assert r.bank == "test-bank"
    assert r.task_id == "task-1"
    assert r.dataset_version == "v1"
    assert r.config_hash_a == "hash-a"
    assert r.config_hash_b == "hash-b"
    assert r.tool_git_sha == "sha-abc"
    assert r.pin_level == "strong"
    assert r.kind == "grading"


# ---------------------------------------------------------------------------
# Judge prompt contains A/B result-view diffs but no scenario names
# ---------------------------------------------------------------------------


def test_judge_prompt_contains_result_view_diff():
    """Prompts sent to the runner contain actual diff content from the result views."""
    runner = StubRunner([_resp("first"), _resp("second")])
    view_a = {"main.py": "def foo():\n    return 42\n"}
    view_b = {"main.py": "def foo():\n    return 99\n"}
    with tempfile.TemporaryDirectory() as tmp:
        _run_judge(Path(tmp), runner, view_a_files=view_a, view_b_files=view_b)
    # Order 1 prompt: A diff first, B diff second
    p1 = runner.calls[0]["prompt"]
    assert "return 42" in p1
    assert "return 99" in p1
    # Order 2 prompt: B diff first, A diff second (same content, swapped position)
    p2 = runner.calls[1]["prompt"]
    assert "return 42" in p2
    assert "return 99" in p2


def test_judge_prompt_no_scenario_names():
    """Scenario identity must not appear in judge prompts (ADR-0003 blindness)."""
    SENTINEL = "SCENARIO-SENTINEL-XYZ-9876"
    scenario = _make_scenario(name=SENTINEL)
    runner = StubRunner([_resp("first"), _resp("second")])
    with tempfile.TemporaryDirectory() as tmp:
        _run_judge(Path(tmp), runner, scenario=scenario)
    for call in runner.calls:
        assert SENTINEL not in call["prompt"], (
            f"Scenario name leaked into judge prompt: '{SENTINEL}'"
        )


def test_judge_prompt_swapped_order():
    """Order 1 presents A first; order 2 presents B first (the swap-order check)."""
    runner = StubRunner([_resp("first"), _resp("second")])
    view_a = {"main.py": "UNIQUE_A_MARKER\n"}
    view_b = {"main.py": "UNIQUE_B_MARKER\n"}
    with tempfile.TemporaryDirectory() as tmp:
        _run_judge(Path(tmp), runner, view_a_files=view_a, view_b_files=view_b)
    p1 = runner.calls[0]["prompt"]
    p2 = runner.calls[1]["prompt"]
    # In order 1, A's diff appears before B's diff
    assert p1.index("UNIQUE_A_MARKER") < p1.index("UNIQUE_B_MARKER")
    # In order 2, B's diff appears before A's diff
    assert p2.index("UNIQUE_B_MARKER") < p2.index("UNIQUE_A_MARKER")


# ---------------------------------------------------------------------------
# stdlib runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_decide_pairwise_agreement_a,
        test_decide_pairwise_agreement_b,
        test_decide_pairwise_disagreement,
        test_decide_pairwise_explicit_tie,
        test_decide_pairwise_mixed_tie,
        test_extract_verdict_plain_json,
        test_extract_verdict_fenced,
        test_extract_verdict_none_on_empty,
        test_render_result_diff_shows_changes,
        test_render_result_diff_new_file,
        test_render_result_diff_deleted_file,
        test_render_result_diff_size_cap,
        test_render_result_diff_identical_no_diff,
        test_render_result_diff_truncation_marker_format,
        test_build_judge_prompt_contains_diffs,
        test_build_judge_prompt_strict_json_instruction,
        test_build_judge_prompt_no_hardcoded_scenario_names,
        test_judge_pairs_agreement_a_wins,
        test_judge_pairs_agreement_b_wins,
        test_judge_pairs_disagreement_tie,
        test_judge_pairs_explicit_tie_response,
        test_judge_pairs_exactly_two_runner_calls_per_pair,
        test_judge_pairs_repeat_index,
        test_judge_pairs_four_calls_for_two_pairs,
        test_grading_record_judge_model,
        test_grading_record_judge_config_hash,
        test_grading_record_metadata_fields,
        test_judge_prompt_contains_result_view_diff,
        test_judge_prompt_no_scenario_names,
        test_judge_prompt_swapped_order,
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
