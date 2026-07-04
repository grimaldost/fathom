"""A tiny in-memory query engine over tables (lists of row dicts, int|None values).

Baseline: only equality filtering is (partially) supported. The full engine
(`where` with SQL NULL semantics, `order_by`, `aggregate`) is the feature to add.
"""

from querytable.core import aggregate, order_by, where

__all__ = ["aggregate", "order_by", "where"]
