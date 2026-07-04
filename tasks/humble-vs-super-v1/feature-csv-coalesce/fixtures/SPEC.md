# Feature: typed CSV coalescing reader

Add a `parse_csv` function to the `csvcoalesce` package, exported at the top
level so it imports as:

```python
from csvcoalesce import Column, parse_csv
```

`Column(name, type)` already exists in `csvcoalesce/model.py`; `type` is one of
`"str"`, `"int"`, or `"float"`.

## Signature

```python
parse_csv(text: str, columns: list[Column]) -> list[dict]
```

`text` is CSV data — comma-separated, one record per line. Parse it with the
standard-library `csv` module. There is **no header row**: each line is a data
record whose cells align **by position** to `columns`. Return one `dict` per
record, mapping each column's `name` to its (coerced) value.

## Required behavior

1. **Type coercion.** Coerce each cell by its column `type`: `"int"` → `int`,
   `"float"` → `float`, `"str"` → the string unchanged.
2. **Empty cells.** A present-but-empty cell (`""`) coalesces to `None` for any
   type — it must never raise (e.g. `int("")` must not be allowed to blow up).
3. **Ragged rows.** If a record has *fewer* cells than there are columns, the
   missing trailing columns coalesce to `None`. If it has *more* cells than
   columns, the extra cells are ignored.
4. **Empty input.** Empty or blank-only `text` returns `[]`. Blank lines never
   produce a record.

## Example

```python
cols = [Column("id", "int"), Column("name", "str"), Column("score", "float")]

parse_csv("1,Alice,9.5\n2,Bob,8.0", cols)
# -> [{"id": 1, "name": "Alice", "score": 9.5},
#     {"id": 2, "name": "Bob",   "score": 8.0}]

parse_csv("3", cols)        # ragged: missing trailing cells -> None
# -> [{"id": 3, "name": None, "score": None}]

parse_csv("4,,", cols)      # empty cells -> None (no crash)
# -> [{"id": 4, "name": None, "score": None}]

parse_csv("", cols)         # empty input
# -> []
```

## Constraints

- Standard library only; add no dependencies.
- Keep the existing `Column` behavior and the baseline tests passing.
- Add unit tests under `tests/` covering the happy path **and** each case above
  (empty input, ragged rows, empty-cell / type coercion).
