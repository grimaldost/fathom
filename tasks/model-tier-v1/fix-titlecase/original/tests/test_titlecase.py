import unittest

from textkit.core import title_case


class TestTitleCase(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(title_case("hello world"), "Hello World")


if __name__ == "__main__":
    unittest.main()
