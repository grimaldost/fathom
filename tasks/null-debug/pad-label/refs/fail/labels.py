"""Shipping-label formatting for the warehouse tool. (ref: over-triggered, extra structure)"""


def _pad(order_id):
    return f"{order_id:05d}"


def shipping_label(order_id):
    """The printed label for an order, e.g. ORDER-00042."""
    return f"ORDER-{_pad(order_id)}"
