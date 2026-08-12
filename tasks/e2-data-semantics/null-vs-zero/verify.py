"""Blind verifier for null-vs-zero.

Reads ONLY argv[1] (the result-view path). Runs the candidate's `build_report`
against a CANONICAL region list and refund ledger carried by this file.

The trap: the report tests the computed total for truth, so `Decimal("0.00")`
falls through the same branch as "no rows at all" and both come back null. The
sum of the non-null totals is identical to the correct sum, so an abs-diff parity
check over the numeric column reports no drift; only the null column moves.

- easy   `absent_regions_report_zero` -- a region with no refund rows reports
  `0.00` and a count of `0`. Special-casing the missing region satisfies this.
- subtle `null_semantics_preserved` -- every region reports a non-null total and
  a non-null count, including the region whose refund and reversal net to zero
  while its row count is 2.

Fails closed on any error.
"""

import importlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

CANONICAL_REGIONS = ["north", "south", "east", "west"]

CANONICAL_REFUNDS = [
    {"refund_id": "R1", "region": "north", "amount": "80.00"},
    {"refund_id": "R2", "region": "north", "amount": "40.00"},
    {"refund_id": "R3", "region": "south", "amount": "45.00"},
    # A refund and its reversal: nets to zero, but two rows happened.
    {"refund_id": "R4", "region": "east", "amount": "30.00"},
    {"refund_id": "R5", "region": "east", "amount": "-30.00"},
    # west has no refund activity at all.
]

KNOWN_GOOD = {
    "north": (Decimal("120.00"), 2),
    "south": (Decimal("45.00"), 1),
    "east": (Decimal("0.00"), 2),
    "west": (Decimal("0.00"), 0),
}

# The region with no refund rows: the visible half of the defect.
ABSENT_REGION = "west"

CRITERIA = ("absent_regions_report_zero", "null_semantics_preserved")
GATE = "null_semantics_preserved"


def _load_func(view, hint, dotted, func_name):
    saved_path = list(sys.path)
    saved_modules = dict(sys.modules)
    sys.path.insert(0, str(view))
    try:
        try:
            attr = getattr(importlib.import_module(dotted), func_name, None)
            if callable(attr):
                return attr
        except Exception:
            pass
        preferred = view / hint
        candidates = [preferred] if preferred.is_file() else []
        candidates += [
            p
            for p in sorted(view.rglob("*.py"))
            if p != preferred and p.name != "verify.py" and "test" not in p.name.lower()
        ]
        for path in candidates:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if f"def {func_name}(" not in text:
                continue
            try:
                rel = path.relative_to(view).with_suffix("")
                attr = getattr(importlib.import_module(".".join(rel.parts)), func_name, None)
            except Exception:
                continue
            if callable(attr):
                return attr
        return None
    finally:
        sys.path[:] = saved_path
        sys.modules.clear()
        sys.modules.update(saved_modules)


def _cell(row):
    """(total, count) for one report row, or None when either is null/unusable."""
    total = row.get("refund_total")
    count = row.get("refund_count")
    if total is None or count is None or isinstance(count, bool):
        return None
    try:
        total = Decimal(str(total))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not isinstance(count, int):
        return None
    return (total, count)


def _as_mapping(report):
    if not isinstance(report, list):
        return None
    out = {}
    for row in report:
        if not isinstance(row, dict) or "region" not in row:
            return None
        out[str(row["region"])] = _cell(row)
    return out


def main():
    result = dict.fromkeys(CRITERIA, False)
    if len(sys.argv) != 2:
        print(json.dumps(result, sort_keys=True))
        return 1

    view = Path(sys.argv[1])
    try:
        func = _load_func(view, "refund_report.py", "refund_report", "build_report")
        if func is not None:
            produced = func(
                list(CANONICAL_REGIONS),
                [dict(row) for row in CANONICAL_REFUNDS],
            )
            mapping = _as_mapping(produced)
            if mapping is not None:
                result["absent_regions_report_zero"] = (
                    mapping.get(ABSENT_REGION) == KNOWN_GOOD[ABSENT_REGION]
                )
                result["null_semantics_preserved"] = mapping == KNOWN_GOOD
    except Exception:
        pass

    print(json.dumps(result, sort_keys=True))
    return 0 if result[GATE] else 1


if __name__ == "__main__":
    sys.exit(main())
