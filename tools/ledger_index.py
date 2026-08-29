#!/usr/bin/env python
"""Render the ledger index — the committed, always-fresh stamp every report is read against.

The rendering logic moved to :mod:`fathom.ledgerindex` so :mod:`fathom.reconcile` can reach
it; ``src/`` may never import ``tools/``, so the dependency points this way.  This file
stays the operator's entry point and re-exports the names the tests already import.

``python tools/ledger_index.py`` checks (exit 1 when stale); ``--write`` re-renders.  Both
run without uv.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fathom.ledgerindex import (  # noqa: E402
    HEADER,
    INDEX_PATH,
    LEDGER_DIR,
    REPO,
    canonical_bytes,
    ledger_files,
    render,
    summarise,
)

__all__ = [
    "HEADER",
    "INDEX_PATH",
    "LEDGER_DIR",
    "REPO",
    "canonical_bytes",
    "ledger_files",
    "render",
    "summarise",
    "main",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="rewrite the committed index")
    parser.add_argument("--ledger-dir", default=str(LEDGER_DIR))
    args = parser.parse_args(argv)

    text = render(Path(args.ledger_dir))
    if args.write:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        INDEX_PATH.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {INDEX_PATH}")
        return 0
    current = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.is_file() else ""
    if current == text:
        print("ledger index is current")
        return 0
    print("ledger index is STALE — re-render with `python tools/ledger_index.py --write`")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
