# Contract — `incremental_load`

Consumers: the regional daily marts, and the freshness monitor that pages when a
partition stops refreshing.

```
run_load(source_rows, state) -> {
    "status": "success" | "partial",
    "state": {...},              # persist this and pass it to the next run
    "stale_partitions": [str],
    "loaded": [row_id, ...],
}
```

Each source row is `{"row_id": str, "partition": str, "event_ts": str}` (ISO
timestamp). `state` is whatever the previous run returned under `"state"`; the
first run is given `{}`.

## Cursor grain

The load is incremental **per partition**. Partitions are loaded from independent
upstreams and their rows arrive on their own schedules, so one partition's rows
routinely arrive after another partition has already produced later timestamps. A
single cursor across all partitions therefore skips a partition's rows as soon as
another partition runs ahead of it, and the skipped rows are never seen again.

Every source row is loaded **exactly once** across the life of the load: none
skipped, none replayed.

## `status` is not a self-report

A run reports `"success"` only when **every** partition it is responsible for
advanced its cursor. A partition that produced no rows this run has not
refreshed, and it is named in `stale_partitions` with `status = "partial"` —
whether or not the run itself completed without error. A run that loaded nothing
for a partition is not a success for that partition, and the freshness monitor
reads `stale_partitions`, not the absence of an exception.

`partitions` in `state` records the partitions the load has ever seen, so a
partition that goes quiet is still known to be its responsibility.
