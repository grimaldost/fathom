# paging

`page_bounds(total, per_page)` returns the `(start, end)` half-open index
pair of every page needed to cover `total` items, including a final partial
page. `end` never exceeds `total`.
