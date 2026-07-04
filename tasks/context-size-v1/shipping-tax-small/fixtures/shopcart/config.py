"""Store configuration constants (canonical source of truth)."""

from decimal import Decimal

# Orders at or above this subtotal ship for free.
FREE_SHIPPING_OVER = Decimal("50.00")

# Flat fee charged when an order does not qualify for free shipping.
SHIPPING_FEE = Decimal("4.99")
