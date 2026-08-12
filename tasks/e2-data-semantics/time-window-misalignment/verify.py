"""Blind verifier for time-window-misalignment.

Reads ONLY argv[1] (the result-view path). Runs the candidate's `monthly_volume`
against a CANONICAL June 2026 ledger carried by this file.

The trap: the transform makes every time-based decision on `load_date`, the local
warehouse load day, while the contract defines both the window and the rate key on
event time in UTC. Repairing the window is the visible half; the rate lookup is a
different function that also keys on `load_date`, and it goes on converting any
order whose local load day differs from its UTC event day at the wrong day's rate.

- easy   `orders_in_window_correct` -- exactly the right orders are in the month.
- subtle `metric_correct_under_consistent_join` -- the converted total is right,
  which needs BOTH sides of the join on the same clock.

Fails closed on any error.
"""

import importlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

CANONICAL_ORDERS = [
    # UTC event day 2026-05-31, loaded locally on 06-01: outside June.
    {
        "order_id": "V1",
        "event_ts": "2026-05-31T23:15:00+00:00",
        "load_date": "2026-06-01",
        "amount_local": "150.00",
        "currency": "EUR",
    },
    {
        "order_id": "V2",
        "event_ts": "2026-06-02T09:00:00+00:00",
        "load_date": "2026-06-02",
        "amount_local": "240.00",
        "currency": "EUR",
    },
    {
        "order_id": "V3",
        "event_ts": "2026-06-10T12:00:00+00:00",
        "load_date": "2026-06-10",
        "amount_local": "360.00",
        "currency": "EUR",
    },
    # UTC event day 2026-06-30, loaded locally on 07-01: inside June.
    {
        "order_id": "V4",
        "event_ts": "2026-06-30T21:45:00+00:00",
        "load_date": "2026-07-01",
        "amount_local": "480.00",
        "currency": "EUR",
    },
    # Inside June on either clock, but the two clocks name different days, so the
    # rate key decides the number.
    {
        "order_id": "V5",
        "event_ts": "2026-06-18T02:00:00+00:00",
        "load_date": "2026-06-17",
        "amount_local": "600.00",
        "currency": "EUR",
    },
]

CANONICAL_FX = [
    {"rate_date": "2026-05-31", "currency": "EUR", "rate": "1.02"},
    {"rate_date": "2026-06-01", "currency": "EUR", "rate": "1.05"},
    {"rate_date": "2026-06-02", "currency": "EUR", "rate": "1.10"},
    {"rate_date": "2026-06-10", "currency": "EUR", "rate": "1.25"},
    {"rate_date": "2026-06-17", "currency": "EUR", "rate": "1.30"},
    {"rate_date": "2026-06-18", "currency": "EUR", "rate": "1.45"},
    {"rate_date": "2026-06-30", "currency": "EUR", "rate": "1.60"},
    {"rate_date": "2026-07-01", "currency": "EUR", "rate": "1.65"},
]

EXPECTED_IDS = ["V2", "V3", "V4", "V5"]
# 240*1.10 + 360*1.25 + 480*1.60 + 600*1.45
EXPECTED_TOTAL = Decimal("2352.00")

CRITERIA = ("orders_in_window_correct", "metric_correct_under_consistent_join")
GATE = "metric_correct_under_consistent_join"


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


def main():
    result = dict.fromkeys(CRITERIA, False)
    if len(sys.argv) != 2:
        print(json.dumps(result, sort_keys=True))
        return 1

    view = Path(sys.argv[1])
    try:
        func = _load_func(view, "settled_volume.py", "settled_volume", "monthly_volume")
        if func is not None:
            produced = func(
                [dict(row) for row in CANONICAL_ORDERS],
                [dict(row) for row in CANONICAL_FX],
                2026,
                6,
            )
            if isinstance(produced, dict):
                ids = produced.get("order_ids")
                if isinstance(ids, (list, tuple, set)):
                    result["orders_in_window_correct"] = sorted(str(i) for i in ids) == EXPECTED_IDS
                try:
                    total = Decimal(str(produced.get("total")))
                except (InvalidOperation, ValueError, TypeError):
                    total = None
                if total is not None:
                    result["metric_correct_under_consistent_join"] = total == EXPECTED_TOTAL
    except Exception:
        pass

    print(json.dumps(result, sort_keys=True))
    return 0 if result[GATE] else 1


if __name__ == "__main__":
    sys.exit(main())
