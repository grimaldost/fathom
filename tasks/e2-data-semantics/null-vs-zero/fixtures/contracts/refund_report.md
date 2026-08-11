# Contract — `refund_report`

Consumers: the regional scorecard and the refund-rate monitor. Both read
`refund_total` straight into an arithmetic aggregate.

`build_report(regions, refunds)` returns one row per region in `regions`, in that
order:

| Field | Type | Null? | Notes |
|---|---|---|---|
| `region` | `str` | never | as given in `regions` |
| `refund_total` | `Decimal` | **never** | net refunds for the region; `0.00` when there is nothing to refund |
| `refund_count` | `int` | **never** | number of refund rows for the region, `0` when there are none |

## Reversals

A reversal is a refund row with a negative `amount`. It is counted in
`refund_count` like any other refund row and netted in `refund_total` like any
other amount.

Row cardinality: exactly `len(regions)` rows, one per region, including regions
with no refund activity.
