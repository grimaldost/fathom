import unittest

from textnorm.core import strip_accents


class TestAccents(unittest.TestCase):
    def test_latin_accents_are_folded(self):
        self.assertEqual(strip_accents("café"), "cafe")
        self.assertEqual(strip_accents("naïve"), "naive")


if __name__ == "__main__":
    unittest.main()
