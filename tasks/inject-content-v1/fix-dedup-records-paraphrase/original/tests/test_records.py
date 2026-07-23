import unittest

from records.core import dedupe


class TestDedupe(unittest.TestCase):
    def test_exact_duplicates_removed(self):
        rows = [{"name": "Ada"}, {"name": "Grace"}, {"name": "Ada"}]
        self.assertEqual(dedupe(rows), [{"name": "Ada"}, {"name": "Grace"}])

    def test_order_preserved(self):
        rows = [{"name": "B"}, {"name": "A"}, {"name": "B"}]
        self.assertEqual(dedupe(rows), [{"name": "B"}, {"name": "A"}])

    def test_empty(self):
        self.assertEqual(dedupe([]), [])


if __name__ == "__main__":
    unittest.main()
