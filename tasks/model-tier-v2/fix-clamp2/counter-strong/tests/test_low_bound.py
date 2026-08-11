import unittest

from rangekit.core import clamp


class TestLowBound(unittest.TestCase):
    def test_value_below_the_range_is_lifted(self):
        self.assertEqual(clamp(-5, 0, 10), 0)


if __name__ == "__main__":
    unittest.main()
