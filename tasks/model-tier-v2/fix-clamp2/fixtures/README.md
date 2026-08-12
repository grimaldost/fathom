# rangekit

Small numeric range utilities.

- `clamp(value, low, high)` — return `value` limited to the **inclusive** range
  `[low, high]`: `low` when `value < low`, `high` when `value > high`, and `value`
  itself otherwise. `low <= high` is assumed. The numeric type is preserved — a
  float that is already inside the range comes back as the same float.

Run the tests: `python -m unittest discover -s tests -t .`
