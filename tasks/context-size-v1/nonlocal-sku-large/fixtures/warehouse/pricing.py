"""Price lookups."""

from .keys import sku_key


def price_for(sku, table):
    """Look up the price for a SKU (table is keyed by canonical SKU)."""
    return table.get(sku_key(sku))
