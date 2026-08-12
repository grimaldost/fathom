# rollup

`daily_rate(rows)` returns `{day: events/actors}` rounded to 3 decimals.
A day with zero actors has an undefined rate and is reported as `None`, never
dropped and never zero.
