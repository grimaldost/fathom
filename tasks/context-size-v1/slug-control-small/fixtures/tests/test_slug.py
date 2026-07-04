import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textkit.slug import slugify


class TestSlug(unittest.TestCase):
    def test_returns_str(self):
        self.assertIsInstance(slugify("Hello"), str)

    def test_single_word(self):
        self.assertEqual(slugify("hello"), "hello")


if __name__ == "__main__":
    unittest.main()
