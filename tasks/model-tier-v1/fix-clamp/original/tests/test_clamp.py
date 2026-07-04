import unittest

from numkit.core import clamp


class TestClamp(unittest.TestCase):
    def test_in_range(self):
        self.assertEqual(clamp(5, 0, 10), 5)

    def test_below_range(self):
        self.assertEqual(clamp(-3, 0, 10), 0)


if __name__ == "__main__":
    unittest.main()
