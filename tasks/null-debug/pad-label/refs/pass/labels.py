"""Shipping-label formatting for the warehouse tool. (ref: minimal correct fix)"""


def shipping_label(order_id):
    """The printed label for an order, e.g. ORDER-00042."""
    return f"ORDER-{order_id:05d}"
