"""csvcoalesce — a tiny typed-CSV reader (starting project).

The package currently ships only the column model. The coalescing reader
described in SPEC.md (``parse_csv``) is the feature to implement; once added it
should be exported here so ``from csvcoalesce import parse_csv`` works.
"""

from .model import Column

__all__ = ["Column"]
