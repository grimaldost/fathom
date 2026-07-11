"""Blind verifier for `analyst-lineage` (scenario-blind, deterministic).

Reads ONLY the result-view path in argv[1] and scores `answers.json` against
ground truth frozen from EXECUTED drives of both arm servers over the frozen
treasury-prod corpus snapshot (2026-07-11): cupom_cambial's 1-hop upstream
serving locators are {di_pre, market_fixings, frc_raw}; its distinct upstream
set within 2 hops has 5 members; market_fixings has 7 direct downstream
consumers; the cupom cambial rate convention is ACT/360 with linear (simple)
compounding (glossary term `cupom-cambial`); the name `cdi_daily` is an alias
resolving to canonical serving locator `di_curve`.
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "upstream_locators_exact",
    "count_2hop_correct",
    "downstream_count_correct",
    "convention_act360_linear",
    "alias_resolved",
)

_EXPECTED_LOCATORS = {"di_pre", "market_fixings", "frc_raw"}


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

    locators = _as_str_list(data.get("cupom_upstream_locators"))
    count_2hop = _as_int(data.get("cupom_upstream_count_2hop"))
    down_count = _as_int(data.get("fixings_direct_downstream_count"))
    convention = _norm(data.get("cupom_rate_convention"))
    alias_target = _norm(data.get("cdi_daily_resolves_to"))

    results["answers_valid"] = None not in (
        locators,
        count_2hop,
        down_count,
        convention,
        alias_target,
    )
    results["upstream_locators_exact"] = locators is not None and set(locators) == (
        _EXPECTED_LOCATORS
    )
    results["count_2hop_correct"] = count_2hop == 5
    results["downstream_count_correct"] = down_count == 7
    if convention:
        compact = convention.replace(" ", "").replace("-", "")
        results["convention_act360_linear"] = ("act/360" in compact or "act360" in compact) and (
            "linear" in compact or "simple" in compact
        )
    if alias_target:
        results["alias_resolved"] = "di_curve" in alias_target
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
