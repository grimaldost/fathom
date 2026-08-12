# regional refund report

`refund_report.py` turns the refund ledger into one row per region.

- `refund_report.build_report(regions, refunds)` -> `list[dict]`

Each refund row is `{"refund_id": str, "region": str, "amount": str}`. A reversal
is a refund row with a negative `amount`.

The declared contract is in `contracts/refund_report.md`.

Run the suite with:

```
python -m unittest discover -s tests -t .
```
