"""Checkout total computation."""

from decimal import Decimal


def grand_total(subtotal):
    """Grand total for an order: subtotal + tax + shipping.

    Free shipping kicks in for large enough orders; otherwise a flat fee applies.
    """
    subtotal = Decimal(subtotal)
    tax = subtotal * Decimal("0.05")
    shipping = Decimal("0") if subtotal >= Decimal("100") else Decimal("5.99")
    return subtotal + tax + shipping
