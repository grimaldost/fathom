"""Added by the symptom patch: only the view the report named."""

import unittest

from feedcache.api import summary
from feedcache.store import Store


class TestSummaryAcrossMidnight(unittest.TestCase):
    def test_summary_does_not_serve_yesterday(self):
        store = Store()
        summary(store, "acme", "2026-03-01", [1, 2, 3])
        self.assertEqual(summary(store, "acme", "2026-03-02", [7])["total"], 7)


if __name__ == "__main__":
    unittest.main()
