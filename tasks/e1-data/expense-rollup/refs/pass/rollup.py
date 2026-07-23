"""Roll a list of transactions up into a per-category expense summary."""

import csv
import json
from decimal import Decimal
from pathlib import Path


def summarize(rows):
    """Summarize transaction rows.

    Each row is a mapping with a "category" and an "amount". Returns a dict
    with "by_category" (a mapping of category name to total) and a
    "grand_total" across every category.
    """
    by_category = {}
    for row in rows:
        category = row["category"].strip()
        if not category:
            category = "Uncategorized"
        amount = Decimal(row["amount"])
        by_category[category] = by_category.get(category, Decimal("0")) + amount
    grand_total = sum(by_category.values(), Decimal("0"))
    return {"by_category": by_category, "grand_total": grand_total}


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    here = Path(__file__).resolve().parent
    rows = load_rows(here / "transactions.csv")
    summary = summarize(rows)
    payload = {
        "by_category": {name: str(total) for name, total in summary["by_category"].items()},
        "grand_total": str(summary["grand_total"]),
    }
    (here / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
