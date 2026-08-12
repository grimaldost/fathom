"""Incremental load for the regional daily marts.

The cursor is per partition (contract: Cursor grain) -- partitions arrive on
their own schedules, so one global cursor skips a partition as soon as another
runs ahead of it. `status` reports what actually advanced (contract: `status` is
not a self-report): a partition the load has seen before and that produced
nothing this run is named in `stale_partitions` and the run is `partial`.

Public API:
    run_load(source_rows, state) -> dict
"""


def run_load(source_rows, state):
    """Load everything newer than each partition's own cursor."""
    watermarks = dict(state.get("watermarks", {}))
    known = set(state.get("partitions", [])) | set(watermarks)
    # The cursors this run STARTED from: advancing a watermark mid-batch would
    # skip a row of the same partition that arrived out of order.
    incoming = dict(watermarks)

    loaded = []
    advanced = set()
    for row in source_rows:
        partition = row["partition"]
        known.add(partition)
        cursor = incoming.get(partition)
        if cursor is not None and row["event_ts"] <= cursor:
            continue
        loaded.append(row["row_id"])
        current = watermarks.get(partition)
        if current is None or row["event_ts"] > current:
            watermarks[partition] = row["event_ts"]
        advanced.add(partition)

    stale = sorted(known - advanced)
    return {
        "status": "partial" if stale else "success",
        "state": {"watermarks": watermarks, "partitions": sorted(known)},
        "stale_partitions": stale,
        "loaded": loaded,
    }
