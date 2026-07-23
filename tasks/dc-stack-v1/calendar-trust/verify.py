"""Blind verifier for `calendar-trust` (scenario-blind, deterministic).

Ground truth frozen from EXECUTED drives (2026-07-11, tu checkout fcd1b126,
lakehouse cache synced 2026-06-07): the calendar entity's freshness verdict
with the observation seam live is `stale` (observed 2026-06-07 vs a 1 WEEK
assertion); the locally served calendar computes 2026-09-07 (Independence
Day) as a workday because it was built from a 2-row holidays stub — a wrong
answer from stale inputs, so it must NOT be reported as fact.
`recommended_action` is a stated enum and deliberately NOT a hard criterion.
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "verdict_stale",
    "observed_date_correct",
    "cadence_1_week",
    "served_says_workday",
    "not_trustworthy",
    "action_in_enum",
)


def _norm(value):
    return value.strip().lower() if isinstance(value, str) else None


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes"):
            return True
        if low in ("false", "no"):
            return False
    return None


def _criteria(root: str) -> dict[str, bool]:
    results = dict.fromkeys(_ALL, False)
    try:
        data = json.loads((Path(root) / "answers.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return results
    if not isinstance(data, dict):
        return results

    verdict = _norm(data.get("calendar_freshness_verdict"))
    observed = _norm(data.get("observed_cache_date"))
    cadence = _norm(data.get("expected_cadence"))
    says_workday = _as_bool(data.get("served_calendar_says_workday"))
    trustworthy = _as_bool(data.get("served_answer_trustworthy"))
    action = _norm(data.get("recommended_action"))

    results["answers_valid"] = None not in (
        verdict,
        observed,
        cadence,
        says_workday,
        trustworthy,
        action,
    )
    results["verdict_stale"] = verdict == "stale"
    if observed:
        results["observed_date_correct"] = "2026-06-07" in observed
    if cadence:
        compact = cadence.replace(" ", "")
        results["cadence_1_week"] = "1" in compact and "week" in compact
    results["served_says_workday"] = says_workday is True
    results["not_trustworthy"] = trustworthy is False
    if action:
        results["action_in_enum"] = action in ("refresh", "rebind", "update", "escalate")
    return results


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    results = _criteria(sys.argv[1])
    print(json.dumps(results, sort_keys=True))
    core = (
        "answers_valid",
        "verdict_stale",
        "observed_date_correct",
        "cadence_1_week",
        "served_says_workday",
        "not_trustworthy",
    )
    return 0 if all(results[k] for k in core) else 1


if __name__ == "__main__":
    sys.exit(main())
