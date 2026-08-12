"""Command line entry point for a tinyetl batch run."""

from __future__ import annotations

import argparse
import json
import sys

from tinyetl.config import load_config
from tinyetl.extract import read_orders
from tinyetl.load import summary, write_records
from tinyetl.transform import dedupe_orders, to_record


def build_parser() -> argparse.ArgumentParser:
    """The argument surface of `python -m tinyetl.cli`."""
    parser = argparse.ArgumentParser(prog="tinyetl", description="Run one order batch")
    parser.add_argument("--config", required=True, help="path to the JSON run config")
    parser.add_argument("--limit", type=int, default=0, help="stop after N rows (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="read and transform, write nothing")
    return parser


def run(argv: list[str]) -> int:
    """Read, transform and write one batch; print the run summary as JSON."""
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    rows = read_orders(config.source_uri)
    if args.limit:
        rows = rows[: args.limit]
    records = [to_record(row) for row in dedupe_orders(rows)]
    row_count = 0 if args.dry_run else write_records(records, config.dest_path)
    print(json.dumps(summary(row_count, config.dest_path), sort_keys=True))
    return 0


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
