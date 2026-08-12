# rollup

`total_by(rows, key, field)` sums `field` per distinct `key` value and
returns `{key_value: total}`. Every key present in `rows` appears in the
result, including keys whose rows all sum to zero. A `None` in `field` counts
as zero; a row that LACKS `field` entirely is a data error and raises
`KeyError`.
