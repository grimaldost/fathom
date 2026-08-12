# Contract — `settlement_export`

Consumer: the treasury base-currency ledger.

`export_rows(records, fx_rates)` returns one row per settlement record whose
currency has a rate in `fx_rates`, in input order:

| Field | Type | Notes |
|---|---|---|
| `settlement_id` | `str` | as given |
| `region` | `str` | as given |
| `amount_base` | `Decimal` | `amount_local * rate`, quantised to `0.01` |

A record whose currency has no rate is omitted. Nothing about this contract is
changing.
