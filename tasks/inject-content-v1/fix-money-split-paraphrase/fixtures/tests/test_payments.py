import unittest

from payments.core import split_amount


class TestSplitAmount(unittest.TestCase):
    def test_even_split(self):
        self.assertEqual(split_amount(90, 3), [30, 30, 30])

    def test_single_recipient(self):
        self.assertEqual(split_amount(100, 1), [100])

    def test_requires_positive_n(self):
        with self.assertRaises(ValueError):
            split_amount(100, 0)


if __name__ == "__main__":
    unittest.main()
