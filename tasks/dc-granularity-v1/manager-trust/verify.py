"""Blind verifier for `manager-trust` (scenario-blind, deterministic).

Reads ONLY the result-view path in argv[1] and scores `answers.json` against
ground truth frozen from EXECUTED drives of both arm servers over the frozen
treasury-prod corpus snapshot (2026-07-11): equity_fundamentals carries no
FRESHNESS assertion, so its verdict is `unknown` with reason
`no_freshness_assertion` (the honest-freshness contract); di_curve's assertion
is FIXED_INTERVAL 1 DAY, so an observation at 2026-01-01T00:00:00Z yields
`stale` (deterministic for any run after 2026-01-02); the snapshot manifest
carries source_version `treasuryutils@v1.8.0-7-gfcd1b126` and max_age_days 30.
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "verdict_unknown",
    "reason_no_assertion",
    "stale_correct",
    "interval_1_day",
    "source_version_correct",
    "max_age_30",
)


def _norm(value):
    return value.strip().lower() if isinstance(value, str) else None


def _as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _criteria(root: str) -> dict[str, bool]:
    results = dict.fromkeys(_ALL, False)
    try:
        data = json.loads((Path(root) / "answers.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return results
    if not isinstance(data, dict):
        return results

    eq_verdict = _norm(data.get("equity_fundamentals_verdict"))
    eq_reason = _norm(data.get("equity_fundamentals_reason"))
    di_verdict = _norm(data.get("di_curve_verdict_if_observed"))
    interval = _norm(data.get("di_curve_expected_interval"))
    version = _norm(data.get("snapshot_source_version"))
    max_age = _as_int(data.get("snapshot_max_age_days"))

    results["answers_valid"] = None not in (
        eq_verdict,
        eq_reason,
        di_verdict,
        interval,
        version,
        max_age,
    )
    results["verdict_unknown"] = eq_verdict == "unknown"
    if eq_reason:
        results["reason_no_assertion"] = "assertion" in eq_reason and any(
            marker in eq_reason for marker in ("no_", "no ", "none", "missing", "without", "not ")
        )
    results["stale_correct"] = di_verdict == "stale"
    if interval:
        compact = interval.replace(" ", "")
        results["interval_1_day"] = "1" in compact and "day" in compact
    if version:
        results["source_version_correct"] = "1.8.0-7-gfcd1b126" in version
    results["max_age_30"] = max_age == 30
    return results


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    results = _criteria(sys.argv[1])
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
