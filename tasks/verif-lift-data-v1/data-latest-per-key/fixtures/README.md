# dedupe

`latest_per_key(rows, key)` keeps the row with the greatest `ts` per key.
When two rows share the greatest `ts`, the one appearing LAST in the input
wins, so the result is defined for ties.
