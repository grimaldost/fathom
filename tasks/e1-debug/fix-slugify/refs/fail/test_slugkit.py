import unittest

from slugkit import slug


class TestSlug(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slug("Hello World"), "hello-world")

    def test_lowercases(self):
        self.assertEqual(slug("Python Tips"), "python-tips")


if __name__ == "__main__":
    unittest.main()
