"""Inventory stock lookups."""

from .keys import sku_key


def stock_for(sku, ledger):
    """Total stock for a SKU across ledger entries (which may use code variants)."""
    total = 0
    for entry_sku, qty in ledger:
        if sku_key(entry_sku) == sku_key(sku):
            total += qty
    return total
