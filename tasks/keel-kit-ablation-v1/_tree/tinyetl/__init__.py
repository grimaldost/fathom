"""tinyetl — a very small batch loader for order records.

The package is deliberately flat: `tinyetl.extract` reads raw orders,
`tinyetl.transform` normalizes and de-duplicates them, `tinyetl.load` writes
records out, and `tinyetl.cli` wires the three together.
"""

__all__ = ["__version__"]

__version__ = "0.3.0"
