import unittest

from urlstats.report import page_counts, top_page


class TestReport(unittest.TestCase):
    def test_counts_distinct_pages(self):
        self.assertEqual(dict(page_counts(["/a", "/b", "/a"])), {"/a": 2, "/b": 1})

    def test_top_page(self):
        self.assertEqual(top_page(["/a", "/a", "/b"]), "/a")


if __name__ == "__main__":
    unittest.main()
