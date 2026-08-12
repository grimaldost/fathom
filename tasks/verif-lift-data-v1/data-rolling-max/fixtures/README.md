# series2

`rolling_max(values, size)` returns the maximum of each full window of `size`
consecutive values, so a series of n values yields `n - size + 1` entries.
A window larger than the series yields an empty list.
