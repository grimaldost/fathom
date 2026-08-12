UNPARTITIONED = "__unpartitioned__"


def rows_per_partition(rows: list[dict], partitions: list[str]) -> dict:
    """Row count per partition, zero-filled over *partitions*."""
    counts = {name: 0 for name in partitions}
    for row in rows:
        name = row["partition"]
        if name is None:
            counts[UNPARTITIONED] = counts.get(UNPARTITIONED, 0) + 1
        elif name in counts:
            counts[name] += 1
    return counts
