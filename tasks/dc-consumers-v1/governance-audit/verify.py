"""Blind verifier for `governance-audit` (scenario-blind, deterministic).

Ground truth frozen from EXECUTED drives of the mock-payments server
(2026-07-11): of the six marts, only mart_revenue_legacy lacks a freshness
assertion; its deprecation.replaced_by is mart_revenue_daily; the liquidity
mart's owner team is treasury-ops and the risk mart's is risk-analytics; the
merchant history's SCD-2 rule marks the current version with valid_to NULL;
the snapshot's source version is mockgen@v1.0.0, it declares NO max-age
policy, and its staleness verdict carries reason no_max_age_policy.
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "marts_no_assertion_exact",
    "replacement_correct",
    "liquidity_team_correct",
    "risk_team_correct",
    "scd2_marker_correct",
    "source_version_correct",
    "policy_not_declared",
    "reason_no_policy",
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


def _as_str_list(value):
    if isinstance(value, list):
        items = [_norm(item) for item in value]
        return items if all(items) else None
    if isinstance(value, str):
        items = [part.strip().lower() for part in value.split(",") if part.strip()]
        return items or None
    return None


def _criteria(root: str) -> dict[str, bool]:
    results = dict.fromkeys(_ALL, False)
    try:
        data = json.loads((Path(root) / "answers.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return results
    if not isinstance(data, dict):
        return results

    no_assertion = _as_str_list(data.get("marts_without_assertion"))
    replacement = _norm(data.get("deprecated_mart_replacement"))
    liquidity_team = _norm(data.get("liquidity_owner_team"))
    risk_team = _norm(data.get("risk_owner_team"))
    scd2 = _norm(data.get("scd2_current_marker"))
    version = _norm(data.get("snapshot_source_version"))
    declared = _as_bool(data.get("snapshot_policy_declared"))
    reason = _norm(data.get("snapshot_verdict_reason"))

    results["answers_valid"] = None not in (
        no_assertion,
        replacement,
        liquidity_team,
        risk_team,
        scd2,
        version,
        declared,
        reason,
    )
    results["marts_no_assertion_exact"] = no_assertion is not None and set(no_assertion) == {
        "mart_revenue_legacy"
    }
    results["replacement_correct"] = replacement == "mart_revenue_daily"
    results["liquidity_team_correct"] = liquidity_team == "treasury-ops"
    results["risk_team_correct"] = risk_team == "risk-analytics"
    if scd2:
        compact = scd2.replace(" ", "_")
        results["scd2_marker_correct"] = "valid_to" in compact and (
            "null" in compact or "none" in compact
        )
    if version:
        results["source_version_correct"] = "mockgen@v1.0.0" in version
    results["policy_not_declared"] = declared is False
    if reason:
        results["reason_no_policy"] = "no_max_age" in reason.replace(" ", "_") or (
            "policy" in reason and ("no" in reason or "none" in reason)
        )
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
