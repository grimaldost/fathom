# series2

`to_weekly(rows, weeks)` returns one entry per week in `weeks`, in that order,
summing the `amount` of the rows in each week. A week with no rows reports 0,
so the series has no gaps.
