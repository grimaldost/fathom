"""Blind verifier for `governance-serving` (scenario-blind, deterministic).

Reads ONLY the result-view path in argv[1] and scores `answers.json` against
ground truth frozen from EXECUTED drives of both arm servers over the frozen
treasury-prod corpus snapshot (2026-07-11): look-ahead bias in fundamentals is
governed by the glossary term `PIT discipline`, whose definition names
`filing_date` as the visibility control; fx_casado is quoted in BRL per 1000
USD; fx_spot is derived as (first_future - casado) / 1000; fx_casado is served
by producer `treasuryutils` under locator `fx_casado`; the Brazilian holiday
data carries two serving locators — `holidays_brazil` (raw table) and
`calendar_brazil` (derived business-day calendar).
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "term_pit",
    "field_filing_date",
    "unit_brl_per_1000",
    "spot_uses_casado_and_first",
    "producer_treasuryutils",
    "locator_fx_casado",
    "holiday_locators_exact",
)

_EXPECTED_HOLIDAY_LOCATORS = {"holidays_brazil", "calendar_brazil"}


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

    term = _norm(data.get("lookahead_bias_term"))
    field = _norm(data.get("pit_visibility_field"))
    unit = _norm(data.get("fx_casado_unit"))
    derivation = _norm(data.get("fx_spot_derivation"))
    producer = _norm(data.get("fx_casado_producer"))
    locator = _norm(data.get("fx_casado_locator"))
    holiday_locators = _as_str_list(data.get("brazil_holiday_locators"))

    results["answers_valid"] = None not in (
        term,
        field,
        unit,
        derivation,
        producer,
        locator,
        holiday_locators,
    )
    if term:
        results["term_pit"] = "pit" in term or "point-in-time" in term or "point in time" in term
    if field:
        results["field_filing_date"] = "filing_date" in field.replace(" ", "_")
    if unit:
        results["unit_brl_per_1000"] = "1000" in unit and "brl" in unit and "usd" in unit
    if derivation:
        results["spot_uses_casado_and_first"] = "casado" in derivation and (
            "first" in derivation or "dol1" in derivation
        )
    results["producer_treasuryutils"] = producer == "treasuryutils"
    results["locator_fx_casado"] = locator == "fx_casado"
    results["holiday_locators_exact"] = holiday_locators is not None and (
        set(holiday_locators) == _EXPECTED_HOLIDAY_LOCATORS
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
