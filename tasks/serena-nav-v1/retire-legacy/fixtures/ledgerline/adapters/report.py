"""Reporting (top-level re-export import shape)."""
from ledgerline import settle

from ..core.fx import convert


def build_report(entries, rate):
    total = settle(entries)
    return {"total": total, "converted": convert(total, rate)}
