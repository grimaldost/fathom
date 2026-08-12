"""Active-accounts extract, ported from legacy/accounts.sql.

Public API:
    load_accounts(path) -> list[dict]
    active_accounts(accounts, as_of) -> list[dict]
"""

import csv
from decimal import Decimal
from pathlib import Path


def load_accounts(path="accounts.csv"):
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def active_accounts(accounts, as_of):
    """The active-account rows as at *as_of* (YYYY-MM-DD)."""
    rows = []
    for account in accounts:
        if account["opened_on"] > as_of:
            continue
        rows.append(
            {
                "account_id": account["account_id"],
                "region": account["region"],
                "opened_on": account["opened_on"],
                "balance": Decimal(account["balance"]),
            }
        )
    return sorted(rows, key=lambda row: row["account_id"])


def main():
    for row in active_accounts(load_accounts(), "2026-06-30"):
        print(f"{row['account_id']}\t{row['region']}\t{row['balance']}")


if __name__ == "__main__":
    main()
