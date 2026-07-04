# numkit

Clamp a numeric value into an inclusive range.

- `clamp(x, lo, hi)` — return `lo` if `x < lo`, `hi` if `x > hi`, otherwise `x`.
  Assumes `lo <= hi`. See the `clamp` docstring for the full contract.

Run the tests: `python -m unittest discover -s tests -t .`
