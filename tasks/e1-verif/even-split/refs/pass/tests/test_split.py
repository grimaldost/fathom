import unittest

from allocate import split_amount


class TestSplitAmount(unittest.TestCase):
    def test_divides_evenly(self):
        self.assertEqual(split_amount(90, 3), [30, 30, 30])

    def test_single_part(self):
        self.assertEqual(split_amount(42, 1), [42])

    def test_zero_total(self):
        self.assertEqual(split_amount(0, 4), [0, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
