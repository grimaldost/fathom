import unittest

from tagkit import normalize_tags


class TestNormalizeTags(unittest.TestCase):
    def test_splits_and_trims(self):
        self.assertEqual(normalize_tags("red, green, blue"), ["red", "green", "blue"])

    def test_lowercases(self):
        self.assertEqual(normalize_tags("Red, GREEN"), ["red", "green"])

    def test_drops_blank_pieces(self):
        self.assertEqual(normalize_tags("red, , blue"), ["red", "blue"])


if __name__ == "__main__":
    unittest.main()
