# incremental load

`incremental_load.py` loads new source rows into the regional daily marts.

- `incremental_load.run_load(source_rows, state)` -> report dict

The caller persists `report["state"]` and passes it back on the next run. The
declared contract is in `contracts/incremental_load.md`.

Run the suite with:

```
python -m unittest discover -s tests -t .
```
