# csvcoalesce

A tiny typed-CSV reader. The starting project ships the `Column` model only.

The feature to implement is specified in **[SPEC.md](SPEC.md)**: a `parse_csv`
function that reads positional CSV records into typed dicts, coalescing empty
cells and ragged rows to `None`.

Run the tests from the project root:

```sh
python -m unittest discover -s tests -t .
```
