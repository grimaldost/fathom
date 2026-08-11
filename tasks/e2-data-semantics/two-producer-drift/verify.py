"""Blind verifier for two-producer-drift.

Reads ONLY argv[1] (the result-view path). Loads the two producers and the
reconciler from the candidate workspace and runs them against a CANONICAL raw
input carried by this file.

The trap: two producers write the same contract column `period`. The settlement
producer derives it from a timestamp on the streaming path and emits a
`datetime` there while emitting a `date` on the batch path; the order producer
always emits a `date`. Each producer's own suite is green, and the join in
`reconcile()` silently drops the streaming days.

- easy   `reconciliation_covers_all_periods` — the assembled rows cover every
  (region, day) both sides produced, with the right amounts. Coercing the key at
  the join site satisfies this while the producers keep disagreeing.
- subtle `both_producers_reconciled` — this verifier joins the two producers'
  RAW output itself, with no coercion, and additionally requires the shared key
  column to carry ONE type across both producers. Only a repair at the producer
  passes.

Fails closed on any error; restores sys.path/sys.modules after loading candidate
code.
"""

import importlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

RAW_ORDERS = [
    {"region": "north", "order_date": "2026-03-02", "amount": "120.00"},
    {"region": "north", "order_date": "2026-03-02", "amount": "30.00"},
    {"region": "north", "order_date": "2026-03-03", "amount": "60.00"},
    {"region": "south", "order_date": "2026-03-02", "amount": "40.00"},
    {"region": "south", "order_date": "2026-03-03", "amount": "80.00"},
    {"region": "east", "order_date": "2026-03-03", "amount": "10.00"},
]

RAW_SETTLEMENTS = [
    {"region": "north", "settled_at": "2026-03-02", "amount": "150.00", "source": "batch"},
    {
        "region": "north",
        "settled_at": "2026-03-03T09:12:00",
        "amount": "60.00",
        "source": "streaming",
    },
    {"region": "south", "settled_at": "2026-03-02", "amount": "40.00", "source": "batch"},
    {
        "region": "south",
        "settled_at": "2026-03-03T14:05:00",
        "amount": "80.00",
        "source": "streaming",
    },
]

# (region, day, gross, settled) — east has orders but no settlement, so it is
# correctly absent from an inner join.
EXPECTED = {
    ("north", "2026-03-02", Decimal("150.00"), Decimal("150.00")),
    ("north", "2026-03-03", Decimal("60.00"), Decimal("60.00")),
    ("south", "2026-03-02", Decimal("40.00"), Decimal("40.00")),
    ("south", "2026-03-03", Decimal("80.00"), Decimal("80.00")),
}

CRITERIA = ("reconciliation_covers_all_periods", "both_producers_reconciled")
GATE = "both_producers_reconciled"


def _iter_module_paths(view, hint):
    """Candidate module files, the hinted path first."""
    preferred = view / hint
    if preferred.is_file():
        yield preferred
    for path in sorted(view.rglob("*.py")):
        if path.name == "verify.py" or "test" in path.name.lower():
            continue
        if path != preferred:
            yield path


def _load_attr(view, hint, dotted, func_name, name_filter=None):
    """Return *func_name* from the candidate's module, or None."""
    saved_path = list(sys.path)
    saved_modules = dict(sys.modules)
    sys.path.insert(0, str(view))
    try:
        try:
            module = importlib.import_module(dotted)
            attr = getattr(module, func_name, None)
            if callable(attr):
                return attr
        except Exception:
            pass
        for path in _iter_module_paths(view, hint):
            if name_filter and name_filter not in path.as_posix().lower():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if f"def {func_name}(" not in text:
                continue
            try:
                rel = path.relative_to(view).with_suffix("")
                module = importlib.import_module(".".join(rel.parts))
            except Exception:
                continue
            attr = getattr(module, func_name, None)
            if callable(attr):
                return attr
        return None
    finally:
        sys.path[:] = saved_path
        sys.modules.clear()
        sys.modules.update(saved_modules)


def _day(value):
    """The calendar day of a period value, as an ISO string, or None."""
    for attr in ("date",):
        method = getattr(value, attr, None)
        if callable(method):
            try:
                return method().isoformat()
            except Exception:
                return None
    try:
        return value.isoformat()[:10]
    except Exception:
        return None


def _amount(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _assembled_set(rows):
    out = set()
    for row in rows or []:
        if not isinstance(row, dict):
            return None
        day = _day(row.get("period"))
        gross = _amount(row.get("gross_amount"))
        settled = _amount(row.get("settled_amount"))
        if day is None or gross is None or settled is None:
            return None
        out.add((str(row.get("region")), day, gross, settled))
    return out


def _natural_join(order_rows, settlement_rows):
    """Join on the raw (region, period) key with NO coercion, as reconcile does."""
    settled = {(r["region"], r["period"]): r["settled_amount"] for r in settlement_rows}
    joined = set()
    for row in order_rows:
        key = (row["region"], row["period"])
        if key in settled:
            joined.add(
                (
                    str(row["region"]),
                    _day(row["period"]),
                    _amount(row["gross_amount"]),
                    _amount(settled[key]),
                )
            )
    return joined


def main():
    result = dict.fromkeys(CRITERIA, False)
    if len(sys.argv) != 2:
        print(json.dumps(result, sort_keys=True))
        return 1

    view = Path(sys.argv[1])
    try:
        orders_emit = _load_attr(
            view, "producers/orders_producer.py", "producers.orders_producer", "emit", "order"
        )
        settlements_emit = _load_attr(
            view,
            "producers/settlements_producer.py",
            "producers.settlements_producer",
            "emit",
            "settle",
        )
        reconcile = _load_attr(view, "reconcile.py", "reconcile", "reconcile")

        if orders_emit and settlements_emit and reconcile:
            order_rows = orders_emit(list(RAW_ORDERS))
            settlement_rows = settlements_emit(list(RAW_SETTLEMENTS))

            assembled = _assembled_set(reconcile(list(order_rows), list(settlement_rows)))
            result["reconciliation_covers_all_periods"] = assembled == EXPECTED

            key_types = {type(r["period"]).__name__ for r in order_rows} | {
                type(r["period"]).__name__ for r in settlement_rows
            }
            result["both_producers_reconciled"] = (
                len(key_types) == 1 and _natural_join(order_rows, settlement_rows) == EXPECTED
            )
    except Exception:
        pass

    print(json.dumps(result, sort_keys=True))
    return 0 if result[GATE] else 1


if __name__ == "__main__":
    sys.exit(main())
