# Contract — `monthly_volume`

Consumer: the settlement desk's monthly volume statement.

`monthly_volume(orders, fx_rates, year, month)` returns

```
{"total": Decimal, "order_ids": [str, ...]}
```

## Time semantics

Every time-based decision in this transform is made on **event time, in UTC**.

- **Window.** An order belongs to a month when its `event_ts`, converted to UTC,
  falls in `[YYYY-MM-01T00:00Z, next-month-01T00:00Z)` — left-inclusive,
  right-exclusive.
- **Rate.** The rate applied to an order is the `fx_rates` row whose `currency`
  matches and whose `rate_date` equals the order's **event date in UTC**.

Both sides of the join are filtered and keyed on the same clock. `load_date` is
the warehouse's local (UTC-03:00) load day: it records when a row reached us, not
when the order happened, and the two disagree for any order placed near local
midnight or late in a local day. It is not an event-time column and no metric is
defined on it.

## Fields

| Table | Field | Notes |
|---|---|---|
| `orders` | `order_id` | unique |
| `orders` | `event_ts` | ISO 8601, timezone-aware, when the order was placed |
| `orders` | `load_date` | `YYYY-MM-DD`, local warehouse load day |
| `orders` | `amount_local` | `Decimal` string |
| `orders` | `currency` | ISO code |
| `fx_rates` | `rate_date` | `YYYY-MM-DD`, the UTC day the rate applies to |
| `fx_rates` | `currency` | ISO code |
| `fx_rates` | `rate` | `Decimal` string |

`total` is the sum of `amount_local * rate` over the orders in the window.
`order_ids` lists exactly those orders.
