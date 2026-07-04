import unittest

from intervals.core import merge


class TestMerge(unittest.TestCase):
    def test_simple_overlap(self):
        self.assertEqual(merge([(1, 4), (3, 6)]), [(1, 6)])

    def test_disjoint_with_gap(self):
        self.assertEqual(merge([(1, 2), (5, 7)]), [(1, 2), (5, 7)])

    def test_empty(self):
        self.assertEqual(merge([]), [])


if __name__ == "__main__":
    unittest.main()
