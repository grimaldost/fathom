"""Blind verifier for `incident-recon` (scenario-blind, deterministic).

Ground truth frozen from EXECUTED drives of the mock-payments server
(2026-07-11): mart_settlement_recon's direct upstreams are {fct_settlements,
raw_slc}; the raw clearing-file tables within 3 hops are exactly {raw_slc,
raw_visa_clearing, raw_mc_clearing} (raw_pix_events is also in the closure but
is an instant-payment event feed, excluded by the question's wording);
raw_slc's interval is 1 DAY, so an observation ~20 minutes old is fresh and
one 3 days old is stale (run-time-relative per the spec's clock-decay
discipline — the verifier pins verdicts only); stg_clearing_unified fans in 3
raw tables; PIX is a transitive, not direct, recon input.
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "direct_upstreams_exact",
    "clearing_feeds_exact",
    "interval_1_day",
    "recent_fresh",
    "old_stale",
    "fan_in_three",
    "pix_not_direct",
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

    direct = _as_str_list(data.get("recon_direct_upstreams"))
    clearing = _as_str_list(data.get("clearing_raw_feeds"))
    interval = _norm(data.get("raw_slc_expected_interval"))
    recent = _norm(data.get("verdict_if_updated_20min_ago"))
    old = _norm(data.get("verdict_if_updated_3days_ago"))
    fan_in = _as_int(data.get("clearing_unification_fan_in"))
    pix_direct = _as_bool(data.get("pix_direct_recon_input"))

    results["answers_valid"] = None not in (
        direct,
        clearing,
        interval,
        recent,
        old,
        fan_in,
        pix_direct,
    )
    results["direct_upstreams_exact"] = direct is not None and set(direct) == {
        "fct_settlements",
        "raw_slc",
    }
    results["clearing_feeds_exact"] = clearing is not None and set(clearing) == {
        "raw_slc",
        "raw_visa_clearing",
        "raw_mc_clearing",
    }
    if interval:
        compact = interval.replace(" ", "")
        results["interval_1_day"] = "1" in compact and "day" in compact
    results["recent_fresh"] = recent == "fresh"
    results["old_stale"] = old == "stale"
    results["fan_in_three"] = fan_in == 3
    results["pix_not_direct"] = pix_direct is False
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
