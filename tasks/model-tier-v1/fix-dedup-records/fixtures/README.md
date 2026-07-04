# records

Collapse duplicate person records.

- `dedupe(rows)` — drop rows that name the same person, keeping the first seen.

A "person" is identified by the row's `name`, compared **case-insensitively** and
**ignoring leading/trailing whitespace** (`"  Ada "` and `"Ada"` are the same person).
The first matching row is kept and the relative order of the kept rows is preserved.
See the `dedupe` docstring for the full contract.

Run the tests: `python -m unittest discover -s tests -t .`
