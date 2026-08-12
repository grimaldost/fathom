"""Incremental load for the regional daily marts.

Public API:
    run_load(source_rows, state) -> dict
"""


def run_load(source_rows, state):
    """Load everything newer than the last run's cursor."""
    cursor = state.get("watermark")
    loaded = []
    high = cursor

    for row in source_rows:
        if cursor is not None and row["event_ts"] <= cursor:
            continue
        loaded.append(row["row_id"])
        if high is None or row["event_ts"] > high:
            high = row["event_ts"]

    return {
        "status": "success",
        "state": {"watermark": high},
        "stale_partitions": [],
        "loaded": loaded,
    }
