# moneykit

`sum_amounts(rows)` sums minor units (integers) and returns
`{"currency": c, "minor": n}`. Rows of mixed currency cannot be summed and
raise `ValueError`. An empty input raises `ValueError` too -- there is no
currency to report.
