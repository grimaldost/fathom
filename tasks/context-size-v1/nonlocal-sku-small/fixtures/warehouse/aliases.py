"""Canonical SKU aliasing (source of truth)."""

_ALIASES = {"WIDGET-V2": "WIDGET", "WID": "WIDGET", "GADGET-NEW": "GADGET"}


def canonical(sku):
    """Map a SKU (or a known alias) to its canonical SKU."""
    key = sku.strip().upper()
    return _ALIASES.get(key, key)
