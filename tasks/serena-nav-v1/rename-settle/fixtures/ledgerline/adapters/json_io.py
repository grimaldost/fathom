"""JSON ingestion (module-attr import shape)."""
from ..core import compute


def total_from_json(data):
    return compute.settle(data["entries"])
