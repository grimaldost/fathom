# rollup

`top_k(rows, k)` returns the `k` rows with the largest `score`, highest first.
Ties break by `name` ascending, so the output is stable for equal scores.
