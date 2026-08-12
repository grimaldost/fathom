# Contract — `daily_revenue`

Consumers: the finance monthly close and the revenue dashboard.

| Column | Type | Notes |
|---|---|---|
| `day` | `str` (`YYYY-MM-DD`) | calendar day |
| `net_revenue` | `Decimal` | **sales minus refunds** for that day |

`orders.csv` records refunds as their own rows: `kind = "refund"` with a
**positive** `amount` (the amount given back). Net revenue for a day is the sum
of that day's `sale` amounts less the sum of its `refund` amounts.

Every day present in the order ledger appears exactly once. Amounts are
`Decimal`, two places, never `float`.
