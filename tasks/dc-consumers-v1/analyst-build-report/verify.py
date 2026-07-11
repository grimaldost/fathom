"""Blind verifier for `analyst-build-report` (scenario-blind, deterministic).

Ground truth frozen from EXECUTED drives of the mock-payments server
(2026-07-11): the authoritative revenue mart is mart_revenue_daily; its direct
upstream locators are {fct_transactions, dim_merchants}; the centavos->BRL
conversion happens at stg_transactions (raw unit: BRL centavos); the report
day field is event_date_brt, derived in America/Sao_Paulo; the mart's
freshness interval is 1 DAY.
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "mart_correct",
    "upstreams_exact",
    "conversion_at_stg",
    "unit_centavos",
    "day_field_correct",
    "tz_correct",
    "cadence_1_day",
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

    mart = _norm(data.get("authoritative_revenue_mart"))
    upstreams = _as_str_list(data.get("mart_direct_upstream_locators"))
    conversion = _norm(data.get("unit_conversion_dataset"))
    unit = _norm(data.get("raw_amount_unit"))
    day_field = _norm(data.get("report_day_field"))
    timezone = _norm(data.get("report_day_timezone"))
    interval = _norm(data.get("mart_expected_interval"))

    results["answers_valid"] = None not in (
        mart,
        upstreams,
        conversion,
        unit,
        day_field,
        timezone,
        interval,
    )
    if mart:
        results["mart_correct"] = "mart_revenue_daily" in mart and "legacy" not in mart
    results["upstreams_exact"] = upstreams is not None and set(upstreams) == {
        "fct_transactions",
        "dim_merchants",
    }
    if conversion:
        results["conversion_at_stg"] = "stg_transactions" in conversion
    if unit:
        results["unit_centavos"] = "centavo" in unit
    if day_field:
        results["day_field_correct"] = "event_date_brt" in day_field
    if timezone:
        compact = timezone.replace(" ", "_")
        results["tz_correct"] = "sao_paulo" in compact or compact in ("brt", "america/sao_paulo")
    if interval:
        compact = interval.replace(" ", "")
        results["cadence_1_day"] = "1" in compact and "day" in compact
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
