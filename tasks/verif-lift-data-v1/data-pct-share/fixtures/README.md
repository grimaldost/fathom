# rollup

`pct_share(rows)` returns `{name: percent}` rounded to 2 decimals, where the
percentages are each row's `value` over the total. When the total is zero every
share is `0.0` -- never a division error and never a dropped key. A row whose
`value` is `None` counts as zero.
