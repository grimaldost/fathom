import unittest

from rangekit.core import clamp


class TestBounds(unittest.TestCase):
    def test_value_below_the_range_is_lifted(self):
        self.assertEqual(clamp(-5, 0, 10), 0)
        self.assertEqual(clamp(-1, 2, 8), 2)

    def test_float_inside_the_range_keeps_its_value(self):
        self.assertEqual(clamp(2.5, 0, 10), 2.5)


if __name__ == "__main__":
    unittest.main()
