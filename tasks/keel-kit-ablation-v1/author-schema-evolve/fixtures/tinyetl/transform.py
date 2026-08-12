"""Normalizing and de-duplicating order rows."""

from __future__ import annotations

SUPPORTED_CURRENCIES = ("EUR", "GBP", "USD")

SCHEMA_VERSION = 1


class TransformError(ValueError):
    """Raised when a row cannot be turned into a record."""


def normalize_currency(currency_code: str) -> str:
    """Return the canonical upper-case currency code.

    Only the exact upper-case forms in SUPPORTED_CURRENCIES are accepted today;
    a feed that emits `eur` raises, which is the behaviour the callers rely on.
    """
    if currency_code not in SUPPORTED_CURRENCIES:
        raise TransformError(f"unsupported currency: {currency_code!r}")
    return currency_code


def dedupe_orders(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Drop rows whose `order_id` was already seen, keeping the first."""
    seen: set[str] = set()
    kept: list[dict[str, str]] = []
    for row in rows:
        order_id = row.get("order_id", "")
        if not order_id:
            raise TransformError("row carries no order_id")
        if order_id in seen:
            continue
        seen.add(order_id)
        kept.append(row)
    return kept


def to_record(row: dict[str, str]) -> dict[str, object]:
    """Turn one raw order row into the serialized record shape."""
    return {
        "order_id": row["order_id"],
        "region": row["region"],
        "amount_cents": int(round(float(row["amount"]) * 100)),
        "currency": normalize_currency(row["currency"]),
        "schema_version": SCHEMA_VERSION,
    }
