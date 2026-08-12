# category-revenue report

`category_report.py` joins the order ledger to the product lookup and totals
revenue per category.

- `category_report.load_csv(path)` -> list of row dicts
- `category_report.revenue_by_category(orders, lookup)` -> `{category: Decimal}`

Inputs: `orders.csv`, `product_lookup.csv`. The declared contract is in
`contracts/category_revenue.md`.

Run the suite with:

```
python -m unittest discover -s tests -t .
```
