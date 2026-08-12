# quality

`null_rate(rows, field)` returns the share of rows whose `field` is missing,
`None`, or an empty/whitespace-only string, rounded to 3 decimals. With no
rows the rate is undefined and reported as `None`.
