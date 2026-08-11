# Contract — `region_daily`

Consumers: the regional settlement report and the finance monthly close.

`region_daily` is assembled by `reconcile.reconcile()` from two producers that
each write part of the same row.

| Column | Type | Producer | Notes |
|---|---|---|---|
| `region` | `str` | both | one of `north`, `south`, `east`, `west` |
| `period` | `datetime.date` | **both** | calendar day, no time component |
| `gross_amount` | `Decimal` | `producers.orders_producer` | sum of order amounts for the day |
| `settled_amount` | `Decimal` | `producers.settlements_producer` | sum of settled amounts for the day |

`period` is the shared key. Both producers commit to the **same** representation
of it: a `datetime.date`. `reconcile()` joins on `(region, period)` with no
coercion, so a producer that emits some other representation of the same day
drops out of the join rather than failing loudly.

Row cardinality: one row per `(region, period)` present in **both** producers'
output. Amounts are `Decimal`, never `float`.
