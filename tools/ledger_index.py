#!/usr/bin/env python
"""Shim over :mod:`fathom.ledgerindex`, kept so the old entry point still works.

The index is rendered from a data root with ``python -m fathom.ledgerindex [--write]``; this
file runs the same thing from an engine checkout without installing it, and re-exports the
module's names for code that imported ``ledger_index``.  Runs without uv.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fathom.ledgerindex import (
    HEADER,
    INDEX_PATH,
    LEDGER_DIR,
    canonical_bytes,
    is_current,
    ledger_files,
    main,
    render,
    rows,
    summarise,
    write,
)

__all__ = [
    "HEADER",
    "INDEX_PATH",
    "LEDGER_DIR",
    "canonical_bytes",
    "is_current",
    "ledger_files",
    "main",
    "render",
    "rows",
    "summarise",
    "write",
]


if __name__ == "__main__":
    raise SystemExit(main())
