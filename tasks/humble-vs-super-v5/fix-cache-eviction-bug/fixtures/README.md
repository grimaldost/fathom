# lru

A fixed-capacity least-recently-used cache.

- `LRUCache(capacity)` — construct with a positive capacity.
- `.get(key, default=None)` — return the value, or `default` if absent.
- `.put(key, value)` — insert or update; evict the least-recently-used entry when full.

Run the tests: `python -m unittest discover -s tests -t .`
