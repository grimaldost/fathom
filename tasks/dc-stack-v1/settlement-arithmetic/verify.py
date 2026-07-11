"""Blind verifier for `settlement-arithmetic` (scenario-blind, deterministic).

Ground truth frozen from EXECUTED calendartools runs over the served (cached)
calendar (2026-07-11, cache synced 2026-06-07): locator calendar_brazil,
producer treasuryutils; net_workdays 2026-07-13..2026-07-31 = 14; D+1 from
Friday 2026-09-04 = 2026-09-07 per the SERVED calendar (stale-cache artifact);
BUS/252 year fraction 2026-07-01..2027-07-01 = 261/252 = 1.035714...; the
platform's freshness surface says the calendar is stale, so the values are
not trustworthy without a refresh.
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "locator_correct",
    "producer_correct",
    "workdays_14",
    "d1_sep7",
    "year_fraction_correct",
    "not_trustworthy",
)

_YF = 261.0 / 252.0


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


def _as_float(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", "."))
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

    locator = _norm(data.get("calendar_locator"))
    producer = _norm(data.get("producer_id"))
    workdays = _as_int(data.get("net_workdays_jul13_jul31"))
    d1 = _norm(data.get("d1_settlement_from_sep4"))
    year_fraction = _as_float(data.get("bus252_year_fraction"))
    trustworthy = _as_bool(data.get("served_calendar_trustworthy"))

    results["answers_valid"] = None not in (
        locator,
        producer,
        workdays,
        d1,
        year_fraction,
        trustworthy,
    )
    results["locator_correct"] = locator == "calendar_brazil"
    results["producer_correct"] = producer == "treasuryutils"
    results["workdays_14"] = workdays == 14
    if d1:
        results["d1_sep7"] = "2026-09-07" in d1
    if year_fraction is not None:
        results["year_fraction_correct"] = abs(year_fraction - _YF) <= 0.002
    results["not_trustworthy"] = trustworthy is False
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
