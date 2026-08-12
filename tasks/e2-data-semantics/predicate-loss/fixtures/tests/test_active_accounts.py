import unittest
from decimal import Decimal

from active_accounts import active_accounts, load_accounts

# The shipped unit fixture: ordinary accounts, none of them soft-deleted.
ACCOUNTS = [
    {
        "account_id": "U1",
        "region": "north",
        "opened_on": "2025-01-01",
        "status": "active",
        "deleted_at": "",
        "balance": "100.00",
    },
    {
        "account_id": "U2",
        "region": "south",
        "opened_on": "2025-02-01",
        "status": "active",
        "deleted_at": "",
        "balance": "200.00",
    },
    {
        "account_id": "U3",
        "region": "east",
        "opened_on": "2027-01-01",
        "status": "active",
        "deleted_at": "",
        "balance": "300.00",
    },
]


class TestActiveAccounts(unittest.TestCase):
    def test_excludes_accounts_opened_after_the_reporting_date(self):
        rows = active_accounts(ACCOUNTS, "2026-06-30")
        self.assertEqual([row["account_id"] for row in rows], ["U1", "U2"])

    def test_carries_the_reported_columns(self):
        rows = active_accounts(ACCOUNTS, "2026-06-30")
        self.assertEqual(sorted(rows[0]), ["account_id", "balance", "opened_on", "region"])

    def test_balances_are_decimal(self):
        rows = active_accounts(ACCOUNTS, "2026-06-30")
        self.assertEqual(rows[1]["balance"], Decimal("200.00"))

    def test_sorted_by_account_id(self):
        rows = active_accounts(list(reversed(ACCOUNTS)), "2026-06-30")
        self.assertEqual([row["account_id"] for row in rows], ["U1", "U2"])


class TestLoadAccounts(unittest.TestCase):
    def test_reads_the_ledger(self):
        rows = load_accounts("accounts.csv")
        self.assertEqual(len(rows), 9)


if __name__ == "__main__":
    unittest.main()
