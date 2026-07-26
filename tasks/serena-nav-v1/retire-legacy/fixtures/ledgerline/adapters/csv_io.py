"""CSV ingestion (aliased import shape)."""
from ..core.compute import settle as _settle


def load_and_settle(rows):
    return _settle([{"amount": float(r)} for r in rows])
