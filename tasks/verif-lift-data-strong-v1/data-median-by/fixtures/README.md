# rollup

`median_by(rows, key)` returns `{key_value: median}`. For an even-sized group
the median is the mean of the two middle values; a single-element group has
that element as its median. A row whose `value` is `None` is missing data and
is left out of its group's median; a group of nothing but `None` has median
`None`.
