"""Shared SKU key helper."""


def sku_key(sku):
    """Normalize a SKU for lookups."""
    return sku.strip().upper()
