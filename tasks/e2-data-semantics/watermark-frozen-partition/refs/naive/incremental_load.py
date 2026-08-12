"""Incremental load for the regional daily marts.

NAIVE REFERENCE -- the fix a first pass reaches for: rows from a slow partition
were being skipped because one partition's timestamps advanced the cursor for all
of them, so keep a cursor per partition. Every row now loads exactly once. The
run still declares itself a success, so a partition whose upstream has stopped
producing altogether reports nothing wrong at all -- it just quietly stops
refreshing.

Public API:
    run_load(source_rows, state) -> dict
"""


def run_load(source_rows, state):
    """Load everything newer than each partition's own cursor."""
    watermarks = dict(state.get("watermarks", {}))
    incoming = dict(watermarks)

    loaded = []
    for row in source_rows:
        partition = row["partition"]
        cursor = incoming.get(partition)
        if cursor is not None and row["event_ts"] <= cursor:
            continue
        loaded.append(row["row_id"])
        current = watermarks.get(partition)
        if current is None or row["event_ts"] > current:
            watermarks[partition] = row["event_ts"]

    return {
        "status": "success",
        "state": {"watermarks": watermarks},
        "stale_partitions": [],
        "loaded": loaded,
    }
