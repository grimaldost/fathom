# Contract — `category_revenue`

Consumers: the merchandising dashboard and the category margin model.

| Column | Type | Notes |
|---|---|---|
| `category` | `str` | the product's category **as of the order date** |
| `revenue` | `Decimal` | sum of `amount` over that category's orders |

## Grain

One row per category. Every order contributes to **exactly one** category.
`sum(revenue)` over the report equals the sum of `amount` over the order ledger.
A category with no orders in the period does not appear.

## `product_lookup` is slowly-changing

`product_lookup.csv` carries **one row per `(product_id, effective_from)`**, not
one row per product. A product that has been recategorised has several rows. The
category that applies to an order is the row for that product with the greatest
`effective_from` that is less than or equal to the order's `order_date`.

Joining the order ledger to `product_lookup` on `product_id` alone is a fan-out:
a recategorised product's orders match more than one lookup row.
