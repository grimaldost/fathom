# book

Totals over an append-only ledger of events.

## Events

Each event is a mapping:

- `{"kind": "post", "id": <str>, "amount": <int>}` — an entry is added.
- `{"kind": "void", "id": <str>}` — the entry with that id is cancelled. A void
  carries **no amount**: it names the entry it cancels.

The log is append-only and may be replayed from any point, so events do not always
arrive in a tidy order:

> A voided entry contributes to **neither** the total **nor** the count, wherever the
> void appears in the log — before or after the post it cancels. Voiding the same id
> twice changes nothing beyond the first void. A void for an id that never appears as
> a post affects nothing.

## The two ways to get the totals

- `live.LiveTotals` / `live.fold(events)` — totals maintained **incrementally**, one
  `apply` per event, for a process that is following the log.
- `replay.replay(events)` — totals recomputed **from the whole log**, for a process
  that is starting cold.

Both return `{"total": ..., "count": ...}`, and **they must agree**: for the same
log, `fold(events) == replay(events)`. Cheaper is not a licence to be different.

Run the tests: `python -m unittest discover -s tests -t .`
