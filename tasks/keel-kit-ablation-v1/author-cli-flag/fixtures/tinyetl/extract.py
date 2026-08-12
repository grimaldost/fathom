"""Reading raw order rows off disk."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

REQUIRED_COLUMNS = ("order_id", "region", "amount", "currency")


class ExtractError(ValueError):
    """Raised when the source cannot be read as an order feed."""


def read_orders(source_uri: str) -> list[dict[str, str]]:
    """Read every order row from a local CSV feed.

    The feed is required to carry REQUIRED_COLUMNS; a missing column is an
    ExtractError rather than a silently empty column, because a downstream
    de-duplication that never sees `order_id` looks like a clean run.
    """
    path = Path(source_uri)
    if not path.is_file():
        raise ExtractError(f"source feed not found: {source_uri}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or ())]
        if missing:
            raise ExtractError(f"source feed is missing columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def iter_batches(rows: list[dict[str, str]], batch_size: int) -> Iterator[list[dict[str, str]]]:
    """Yield `rows` in slices of at most `batch_size`."""
    if batch_size <= 0:
        raise ExtractError("batch_size must be positive")
    for start in range(0, len(rows), batch_size):
        yield rows[start : start + batch_size]
