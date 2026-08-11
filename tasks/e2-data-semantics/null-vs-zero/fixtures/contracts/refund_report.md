# Contract — `refund_report`

Consumers: the regional scorecard and the refund-rate monitor. Both read
`refund_total` straight into an arithmetic aggregate, so a null there is not the
same value as a zero — it drops the region out of the average instead of pulling
it down.

`build_report(regions, refunds)` returns one row per region in `regions`, in that
order:

| Field | Type | Null? | Notes |
|---|---|---|---|
| `region` | `str` | never | as given in `regions` |
| `refund_total` | `Decimal` | **never** | net refunds for the region; `0.00` when there is nothing to refund |
| `refund_count` | `int` | **never** | number of refund rows for the region, `0` when there are none |

## Zero is a value

Two different regions produce a `refund_total` of `0.00`:

- a region with **no refund rows at all**, whose `refund_count` is `0`; and
- a region whose refund rows **net to zero** — a refund and its reversal — whose
  `refund_count` is the number of rows that netted, not `0`.

Both report `0.00`. Neither reports null. A reversal is a refund row with a
negative `amount`; it is counted like any other row.

Row cardinality: exactly `len(regions)` rows, one per region, including regions
with no refund activity.
