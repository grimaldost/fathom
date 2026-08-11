# rollup

`rows_per_partition(rows, partitions)` returns `{partition: count}` covering
every partition in `partitions`, with 0 for the empty ones. A row whose
partition is `None` counts under the `"__unpartitioned__"` key.
