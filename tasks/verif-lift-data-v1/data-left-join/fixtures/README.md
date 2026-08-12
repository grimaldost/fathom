# joinkit

`left_join(left, right, key)` keeps every left row. A left row with no match
gets `None` for the right fields; a left row matching several right rows
produces one output row per match. Where a right field collides with a field
the left row already carries, the LEFT value wins -- a join never silently
overwrites the driving side.
