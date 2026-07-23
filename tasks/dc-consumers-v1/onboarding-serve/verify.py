"""Blind verifier for `onboarding-serve` (scenario-blind, deterministic).

Ground truth frozen from EXECUTED drives of the mock-payments server
(2026-07-11): alias "receivables" resolves to fct_receivables and "tpv" to
mart_tpv_monthly, both served by producer id `dataplatform`; resolving a
dashboard returns the structured error code `unresolved_locator`; the curated
decimal-BRL deduplicated transactions dataset is stg_transactions; the table
name `transactions` exists on exactly {postgres, bigquery}; the raw
chargebacks table's verdict is unknown with reason no_freshness_assertion.
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "receivables_correct",
    "tpv_correct",
    "producer_correct",
    "error_code_correct",
    "curated_correct",
    "platforms_exact",
    "verdict_unknown",
    "reason_no_assertion",
)


def _norm(value):
    return value.strip().lower() if isinstance(value, str) else None


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

    receivables = _norm(data.get("receivables_locator"))
    tpv = _norm(data.get("tpv_locator"))
    producer = _norm(data.get("producer_id"))
    error_code = _norm(data.get("dashboard_serve_error_code"))
    curated = _norm(data.get("curated_brl_transactions"))
    platforms = _as_str_list(data.get("transactions_table_platforms"))
    verdict = _norm(data.get("chargebacks_verdict"))
    reason = _norm(data.get("chargebacks_reason"))

    results["answers_valid"] = None not in (
        receivables,
        tpv,
        producer,
        error_code,
        curated,
        platforms,
        verdict,
        reason,
    )
    results["receivables_correct"] = receivables == "fct_receivables"
    results["tpv_correct"] = tpv == "mart_tpv_monthly"
    results["producer_correct"] = producer == "dataplatform"
    if error_code:
        results["error_code_correct"] = "unresolved_locator" in error_code
    if curated:
        results["curated_correct"] = "stg_transactions" in curated
    results["platforms_exact"] = platforms is not None and set(platforms) == {
        "postgres",
        "bigquery",
    }
    results["verdict_unknown"] = verdict == "unknown"
    if reason:
        results["reason_no_assertion"] = "assertion" in reason and any(
            marker in reason for marker in ("no_", "no ", "none", "missing", "without", "not ")
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
