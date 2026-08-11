# tinyetl

A very small batch loader for order records.

```sh
python -m tinyetl.cli --config run.json
python -m unittest discover -s tests -t .
```

## Layout

| Module | Responsibility |
|---|---|
| `tinyetl/config.py` | run configuration, read from a JSON file |
| `tinyetl/extract.py` | read raw order rows off disk |
| `tinyetl/transform.py` | normalize, de-duplicate, and shape records |
| `tinyetl/load.py` | write records out and report the row_count |
| `tinyetl/cli.py` | wire the three together |

Architecture decisions live under `docs/adr/`. New ADRs take the next free
number on your base — never a hardcoded guess.
