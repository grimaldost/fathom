import unittest

from textnorm.core import strip_accents


class TestStripAccents(unittest.TestCase):
    def test_plain_text_is_unchanged(self):
        self.assertEqual(strip_accents("hello world 42"), "hello world 42")

    def test_empty_string(self):
        self.assertEqual(strip_accents(""), "")


if __name__ == "__main__":
    unittest.main()
