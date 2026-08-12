"""Writing records out, and reporting what was written."""

from __future__ import annotations

import json
from pathlib import Path


class LoadError(OSError):
    """Raised when the destination cannot be written."""


def write_records(records: list[dict[str, object]], dest_path: str | Path) -> int:
    """Write `records` as JSON lines and return the row_count written."""
    path = Path(dest_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError as exc:
        raise LoadError(f"could not write {dest_path}: {exc}") from exc
    return len(records)


def summary(row_count: int, dest_path: str | Path) -> dict[str, object]:
    """The run summary every caller of tinyetl reads."""
    return {
        "row_count": row_count,
        "dest_path": str(dest_path),
        "status": "ok" if row_count else "empty",
    }
