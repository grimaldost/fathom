# settlement export

`settlement_export.py` converts settlement records to the base currency.

- `settlement_export.export_rows(records, fx_rates)` -> `list[dict]`

Each record is `{"settlement_id": str, "region": str, "amount_local": str,
"currency": str}`; `fx_rates` maps a currency code to a rate string.

The declared contract is in `contracts/settlement_export.md`.

Run the suite with:

```
python -m unittest discover -s tests -t .
```
