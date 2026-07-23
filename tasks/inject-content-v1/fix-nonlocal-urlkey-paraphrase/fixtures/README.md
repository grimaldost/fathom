# urlstats

Count page visits from a stream of request URLs.

A "page" is identified by its path **without the query string and without a trailing
slash**: `/home`, `/home/`, and `/home?ref=promo` are all the **same page** (`/home`).

- `page_counts(urls)` — a Counter of visits per page
- `top_page(urls)` — the most-visited page (ties: first seen), or `None` if empty

Run the tests: `python -m unittest discover -s tests -t .`
