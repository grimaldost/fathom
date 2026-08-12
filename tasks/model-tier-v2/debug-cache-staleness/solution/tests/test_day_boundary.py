"""Added by the reference solution: the axis the shipped suite never crossed."""

import unittest

from feedcache.api import summary
from feedcache.report import daily_report
from feedcache.store import Store
from feedcache.trend import trend


class TestAcrossMidnight(unittest.TestCase):
    def test_summary_does_not_serve_yesterday(self):
        store = Store()
        summary(store, "acme", "2026-03-01", [1, 2, 3])
        self.assertEqual(summary(store, "acme", "2026-03-02", [7])["total"], 7)

    def test_report_does_not_serve_yesterday(self):
        store = Store()
        daily_report(store, "acme", "2026-03-01", [1, 2, 3])
        self.assertEqual(daily_report(store, "acme", "2026-03-02", [7])["rows"], 1)

    def test_trend_does_not_serve_yesterday(self):
        store = Store()
        trend(store, "acme", "2026-03-01", [5, 1])
        self.assertEqual(trend(store, "acme", "2026-03-02", [1, 5])["direction"], "up")


if __name__ == "__main__":
    unittest.main()
