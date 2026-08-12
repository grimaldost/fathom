The `ndj` package README states that merging keeps one record per id — a record on
the right replaces the record with the same id on the left, in the replaced
record's position. `merge_text` does not do that: merging a document containing
`{"id": "a", "v": 1}` with one containing `{"id": "a", "v": 9}` returns both
records instead of just the newer one. Make the package behave as the README
documents. Preserve the existing public API, and keep the shipped test suite
passing.
