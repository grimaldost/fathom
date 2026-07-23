# intervals

Merge overlapping or adjacent integer intervals.

- `merge(intervals)` — collapse a start-sorted list of inclusive `(start, end)` pairs
  into the minimal set of non-overlapping, non-adjacent intervals.

Intervals merge when they overlap **or touch** (consecutive integers, e.g. `(1, 3)` and
`(4, 6)` → `(1, 6)`). A merged interval runs to the **greatest** end among its members,
so a short interval contained in a longer one never shortens it. See the `merge`
docstring for the full contract.

Run the tests: `python -m unittest discover -s tests -t .`
