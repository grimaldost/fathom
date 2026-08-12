"""Added by the root-cause patch, for the two views it reached."""

import unittest

from feedcache.api import summary
from feedcache.report import daily_report
from feedcache.store import Store


class TestAcrossMidnight(unittest.TestCase):
    def test_summary_does_not_serve_yesterday(self):
        store = Store()
        summary(store, "acme", "2026-03-01", [1, 2, 3])
        self.assertEqual(summary(store, "acme", "2026-03-02", [7])["total"], 7)

    def test_report_does_not_serve_yesterday(self):
        store = Store()
        daily_report(store, "acme", "2026-03-01", [1, 2, 3])
        self.assertEqual(daily_report(store, "acme", "2026-03-02", [7])["rows"], 1)


if __name__ == "__main__":
    unittest.main()
