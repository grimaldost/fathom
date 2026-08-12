# monthly settled volume

`settled_volume.py` converts the order ledger to the reporting currency and
totals it per calendar month.

- `settled_volume.monthly_volume(orders, fx_rates, year, month)`
  -> `{"total": Decimal, "order_ids": [str, ...]}`

`sample_data.py` holds a small March 2026 sample (`ORDERS`, `FX_RATES`) for local
runs. The declared contract is in `contracts/monthly_volume.md`.

Run the suite with:

```
python -m unittest discover -s tests -t .
```
