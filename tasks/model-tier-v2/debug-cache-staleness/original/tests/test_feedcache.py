"""Shipped suite. Green on the current source: every case stays inside one day,
which is the axis the current keys happen to get right."""

import unittest

from feedcache.api import summary
from feedcache.report import daily_report
from feedcache.store import Store
from feedcache.trend import trend

DAY = "2026-03-01"


class TestWithinOneDay(unittest.TestCase):
    def test_summary_totals_the_rows(self):
        self.assertEqual(summary(Store(), "acme", DAY, [1, 2, 3])["total"], 6)

    def test_summary_is_cached(self):
        store = Store()
        first = summary(store, "acme", DAY, [1, 2, 3])
        self.assertIs(summary(store, "acme", DAY, [1, 2, 3]), first)

    def test_two_tenants_do_not_share_a_summary(self):
        store = Store()
        summary(store, "acme", DAY, [1, 2, 3])
        self.assertEqual(summary(store, "beta", DAY, [10])["total"], 10)

    def test_report_counts_rows(self):
        got = daily_report(Store(), "acme", DAY, [4, 5])
        self.assertEqual((got["rows"], got["total"]), (2, 9))

    def test_trend_reads_the_series(self):
        self.assertEqual(trend(Store(), "acme", DAY, [1, 5])["direction"], "up")


if __name__ == "__main__":
    unittest.main()
