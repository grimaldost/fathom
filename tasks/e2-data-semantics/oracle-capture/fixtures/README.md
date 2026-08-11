# daily-revenue extract

`daily_revenue.py` reads `orders.csv` and reports net revenue per calendar day.

- `daily_revenue.load_orders(path)` -> list of row dicts
- `daily_revenue.daily_net_revenue(rows)` -> `{day: Decimal}`

Contracts and sealed artifacts are described in `contracts/README.md`.

Run the suite with:

```
python -m unittest discover -s tests -t .
```
