"""Customer roster helpers for the CRM export. (ref: disciplined, verified on real data)"""

import csv
from pathlib import Path


def total_customers(rows):
    """How many customer records are in the roster (one per row)."""
    return len(rows)


def unique_customers(rows):
    """Number of distinct customers.

    The roster carries the same customer under casual spellings -- stray
    leading/trailing spaces and inconsistent capitalisation ("Ana", "ana ",
    " ANA" are one customer) -- so names are compared after trimming and
    case-folding.
    """
    return len({row["name"].strip().casefold() for row in rows})


def load_rows(path):
    """Read customer rows (each with a "name") from a CSV file."""
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    here = Path(__file__).resolve().parent
    rows = load_rows(here / "customers.csv")
    print(f"customer records: {total_customers(rows)}")
    print(f"distinct customers: {unique_customers(rows)}")


if __name__ == "__main__":
    main()
