# Brief — split the transform module into a package

`tinyetl/transform.py` has grown three unrelated responsibilities and every new rule lands in the
same file.

What is wanted:

1. The module becomes a `tinyetl/transforms/` package: currency normalization, de-duplication and
   record shaping each get their own module inside it.
2. `normalize_currency`, `dedupe_orders` and `to_record` stay importable under the names callers
   use today — nothing outside the package changes its imports.
3. The test suite keeps passing unchanged.

This is a move, not a rewrite: no behaviour changes.
