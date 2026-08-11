import unittest

from rangekit.core import clamp


class TestClamp(unittest.TestCase):
    def test_value_inside_the_range_is_returned(self):
        self.assertEqual(clamp(5, 0, 10), 5)

    def test_value_above_the_range_is_capped(self):
        self.assertEqual(clamp(20, 0, 10), 10)


if __name__ == "__main__":
    unittest.main()
