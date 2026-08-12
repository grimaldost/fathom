# region-daily reconciliation

Two producers write different columns of the same `region_daily` row:

- `producers/orders_producer.py` — `emit(raw_orders)` → `region`, `period`, `gross_amount`
- `producers/settlements_producer.py` — `emit(raw_settlements)` → `region`, `period`, `settled_amount`

`reconcile.py` — `reconcile(order_rows, settlement_rows)` joins the two on
`(region, period)` and returns the assembled `region_daily` rows.

The declared contract is in `contracts/region_daily.md`.

Settlement records arrive by two upstream paths: an overnight `batch` export and
a `streaming` feed. Both carry the same fields.

Run the suite with:

```
python -m unittest discover -s tests -t .
```
