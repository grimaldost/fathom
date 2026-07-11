"""Blind verifier for `manager-numbers-off` (scenario-blind, deterministic).

Ground truth frozen from EXECUTED drives of the mock-payments server
(2026-07-11): dashboards/tpv_executive fans in mart_tpv_monthly and
mart_revenue_daily, both descending from fct_transactions (the diamond's
shared ancestor); its 2-hop distinct upstream set has 4 members; the
authoritative revenue dashboard is dashboards/revenue_daily (the legacy one
sits over a deprecated mart whose deprecation.replaced_by is
mart_revenue_daily, deprecated because it double-counts refunded
transactions); mart_tpv_monthly's freshness verdict is unknown with reason
unsupported_schedule (MONTH-unit assertion).
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "shared_ancestor_correct",
    "count_2hop_correct",
    "authoritative_correct",
    "replacement_correct",
    "reason_refunds",
    "verdict_unknown",
    "reason_unsupported",
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

    ancestor = _norm(data.get("shared_ancestor"))
    count = _as_int(data.get("tpv_executive_upstream_count_2hop"))
    dashboard = _norm(data.get("authoritative_revenue_dashboard"))
    replaced_by = _norm(data.get("legacy_replaced_by"))
    reason = _norm(data.get("legacy_reason"))
    verdict = _norm(data.get("tpv_monthly_verdict"))
    freshness_reason = _norm(data.get("tpv_monthly_reason"))

    results["answers_valid"] = None not in (
        ancestor,
        count,
        dashboard,
        replaced_by,
        reason,
        verdict,
        freshness_reason,
    )
    if ancestor:
        results["shared_ancestor_correct"] = "fct_transactions" in ancestor
    results["count_2hop_correct"] = count == 4
    if dashboard:
        results["authoritative_correct"] = "revenue_daily" in dashboard and (
            "legacy" not in dashboard
        )
    results["replacement_correct"] = replaced_by == "mart_revenue_daily"
    if reason:
        results["reason_refunds"] = "refund" in reason
    results["verdict_unknown"] = verdict == "unknown"
    if freshness_reason:
        results["reason_unsupported"] = "unsupported" in freshness_reason
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
