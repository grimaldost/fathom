# paginator

Helpers for splitting a result set into fixed-size pages.

- `total_pages(total_items, per_page)` — number of pages.
- `page_slice(total_items, per_page, page)` — `(start, end)` indices for a 1-indexed page.

Run the tests: `python -m unittest discover -s tests -t .`
