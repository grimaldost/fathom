"""Swap-order pairwise judge.

Ported from craft-collection's evals/harness/judge.py to the fathom Runner
protocol (ADR-0001). Both A/B orders are judged per pair; win only when both
orders agree, else tie. Pairs match by repeat index.

The A/B payload is the §7 scored result view rendered as a unified diff against
the task's fixture baseline, size-capped with a recorded truncation marker.

Ships dark in v1: exercised by tests, not by the v1 verdict (spec §8 non-goal).
Stdlib only.
"""

from __future__ import annotations

import dataclasses
import difflib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from fathom.ledger import GradingRecord
from fathom.scenario import compute_config_hash

if TYPE_CHECKING:
    from fathom.adapters.base import Runner
    from fathom.scenario import ResolvedScenario

_TRUNCATION_MARKER = "[TRUNCATED: {omitted} bytes omitted]"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class JudgeConfig:
    """Configuration for the pairwise judge.

    ``max_bytes`` caps each result-view diff in the prompt; the truncation
    marker records the omitted byte count so the judge knows content was cut.
    """

    model: str
    effort: str = "normal"
    max_budget_usd: float = 0.25
    timeout_s: int = 180
    max_bytes: int = 8192


def _config_dict(config: JudgeConfig) -> dict:
    return {
        "effort": config.effort,
        "max_budget_usd": config.max_budget_usd,
        "max_bytes": config.max_bytes,
        "model": config.model,
        "timeout_s": config.timeout_s,
    }


# ---------------------------------------------------------------------------
# Pure helpers — ported from craft-collection judge.py
# ---------------------------------------------------------------------------


def extract_verdict(text: str) -> dict | None:
    """Pull a JSON verdict object out of a judge's (messy) text reply.

    Tries a fenced ```json block first, then the first balanced {…} substring.
    Returns the parsed dict, or None if nothing usable is found.
    """
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except (json.JSONDecodeError, ValueError):
            pass
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except (json.JSONDecodeError, ValueError):
                        break
        start = text.find("{", start + 1)
    return None


def decide_pairwise(winner_order1: str, winner_order2: str) -> dict:
    """Swap-order pairwise decision.

    Each arg is the ACTUAL winner ('A'|'B'|'tie') in one presentation order.
    Win only when both orders agree; any disagreement collapses to 'tie'.
    """
    if winner_order1 == winner_order2 and winner_order1 in ("A", "B"):
        return {"winner": winner_order1, "agreement": True}
    return {"winner": "tie", "agreement": winner_order1 == winner_order2}


# ---------------------------------------------------------------------------
# Payload: result-view unified diff vs fixture baseline
# ---------------------------------------------------------------------------


def _collect_files(root: Path) -> dict[str, list[str]]:
    """Return {rel_posix_path: lines} for all files under *root*."""
    files: dict[str, list[str]] = {}
    if not root.exists():
        return files
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            try:
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            except OSError:
                lines = []
            files[rel] = lines
    return files


def render_result_diff(result_view: Path, baseline: Path, max_bytes: int) -> tuple[str, bool]:
    """Render a unified diff of *result_view* vs *baseline*, size-capped.

    Returns ``(diff_text, was_truncated)``.  Files present in only one tree are
    diffed against an empty counterpart (new or deleted files).  When the
    combined diff exceeds ``max_bytes``, it is truncated and a marker recording
    the omitted byte count is appended.
    """
    baseline_files = _collect_files(baseline)
    result_files = _collect_files(result_view)
    all_paths = sorted(set(baseline_files) | set(result_files))

    chunks: list[str] = []
    for path in all_paths:
        before = baseline_files.get(path, [])
        after = result_files.get(path, [])
        diff = list(
            difflib.unified_diff(
                before,
                after,
                fromfile=f"baseline/{path}",
                tofile=f"result/{path}",
            )
        )
        if diff:
            chunks.append("".join(diff))

    combined = "\n".join(chunks)

    if len(combined) <= max_bytes:
        return combined, False

    truncated = combined[:max_bytes]
    omitted = len(combined) - max_bytes
    return truncated + "\n" + _TRUNCATION_MARKER.format(omitted=omitted), True


# ---------------------------------------------------------------------------
# Judge prompt — no scenario identity (ADR-0003)
# ---------------------------------------------------------------------------


def build_judge_prompt(diff_a: str, diff_b: str) -> str:
    """Build a strict-JSON rubric prompt presenting two result-view diffs.

    Contains only diff content and static rubric text — no scenario identifiers,
    strategy names, or arm labels, satisfying the scenario-blind scoring
    invariant (ADR-0003).
    """
    return (
        "You are a strict, fair judge. Two candidates completed a software task. "
        "Below are their changes against the original baseline. "
        "Decide which result better satisfies the task requirements.\n\n"
        "--- RESPONSE 1 CHANGES ---\n"
        f"{diff_a}\n\n"
        "--- RESPONSE 2 CHANGES ---\n"
        f"{diff_b}\n\n"
        "Reply with ONLY this JSON object and nothing else:\n"
        '{"winner":"first","reason":"<one sentence>"}\n'
        '(winner must be "first", "second", or "tie".)'
    )


# ---------------------------------------------------------------------------
# Single-pair judge: two ordered calls, swap-order decision
# ---------------------------------------------------------------------------


def _judge_pair(
    diff_a: str,
    diff_b: str,
    runner: Runner,
    judge_scenario: ResolvedScenario,
    workspace: Path,
) -> tuple[str, str, str]:
    """Judge one (A, B) pair in both orders.

    Returns ``(winner, judge_model, cli_version)`` where *winner* is
    ``'A'|'B'|'tie'``, *judge_model* is the model_id from the first RunRecord
    (the resolved model as reported by the CLI), and *cli_version* likewise.
    """
    # Order 1: A presented first, B second.
    prompt1 = build_judge_prompt(diff_a, diff_b)
    record1 = runner.execute(prompt1, workspace, judge_scenario)
    v1 = extract_verdict(record1.result_text) or {}
    raw1 = str(v1.get("winner", "tie")).strip().lower()
    if raw1 not in ("first", "second", "tie"):
        raw1 = "tie"
    w1 = {"first": "A", "second": "B", "tie": "tie"}[raw1]

    # Order 2: B presented first, A second (swap).
    prompt2 = build_judge_prompt(diff_b, diff_a)
    record2 = runner.execute(prompt2, workspace, judge_scenario)
    v2 = extract_verdict(record2.result_text) or {}
    raw2 = str(v2.get("winner", "tie")).strip().lower()
    if raw2 not in ("first", "second", "tie"):
        raw2 = "tie"
    w2 = {"first": "B", "second": "A", "tie": "tie"}[raw2]

    decision = decide_pairwise(w1, w2)
    return decision["winner"], record1.model_id, record1.cli_version


# ---------------------------------------------------------------------------
# Batch: judge all pairs by repeat index
# ---------------------------------------------------------------------------


def judge_pairs(
    *,
    pairs: list[tuple[Path, Path]],
    baseline: Path,
    runner: Runner,
    judge_scenario: ResolvedScenario,
    judge_config: JudgeConfig,
    bank: str,
    task_id: str,
    dataset_version: str,
    config_hash_a: str,
    config_hash_b: str,
    tool_git_sha: str,
    pin_level: str,
) -> list[GradingRecord]:
    """Judge all (treatment, bare-anchor) pairs by repeat index.

    Each pair is judged in both A/B orders (swap-order pairwise, ADR-0003).
    The A/B payload is the result view as a unified diff vs the fixture baseline,
    size-capped per ``judge_config.max_bytes``.

    Returns one :class:`~fathom.ledger.GradingRecord` per pair, ordered by
    repeat index, each carrying the resolved judge model and judge config hash.
    """
    judge_config_hash = compute_config_hash(_config_dict(judge_config))

    tmp_dir = tempfile.mkdtemp(prefix="fathom-judge-")
    workspace = Path(tmp_dir)
    try:
        records: list[GradingRecord] = []
        for repeat, (result_view_a, result_view_b) in enumerate(pairs):
            diff_a, _ = render_result_diff(result_view_a, baseline, judge_config.max_bytes)
            diff_b, _ = render_result_diff(result_view_b, baseline, judge_config.max_bytes)

            winner, judge_model, cli_version = _judge_pair(
                diff_a, diff_b, runner, judge_scenario, workspace
            )

            verdict = winner.lower() if winner in ("A", "B") else "tie"

            records.append(
                GradingRecord(
                    bank=bank,
                    task_id=task_id,
                    repeat=repeat,
                    verdict=verdict,
                    dataset_version=dataset_version,
                    config_hash_a=config_hash_a,
                    config_hash_b=config_hash_b,
                    tool_git_sha=tool_git_sha,
                    cli_version=cli_version,
                    judge_config_hash=judge_config_hash,
                    judge_model=judge_model,
                    pin_level=pin_level,
                )
            )
        return records
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
