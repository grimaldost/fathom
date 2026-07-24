"""Customer roster helpers for the CRM export."""

import csv
from pathlib import Path


def total_customers(rows):
    """How many customer records are in the roster (one per row)."""
    return len(rows)


def load_rows(path):
    """Read customer rows (each with a "name") from a CSV file."""
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    here = Path(__file__).resolve().parent
    rows = load_rows(here / "customers.csv")
    print(f"customer records: {total_customers(rows)}")


if __name__ == "__main__":
    main()
