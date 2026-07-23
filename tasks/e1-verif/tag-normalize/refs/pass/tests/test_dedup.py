import unittest

from tagkit import normalize_tags


class TestDeduplication(unittest.TestCase):
    def test_keeps_first_occurrence_in_order(self):
        self.assertEqual(normalize_tags("b, a, B, a, c"), ["b", "a", "c"])

    def test_case_insensitive_repeat_collapses(self):
        self.assertEqual(normalize_tags("Red, red, RED"), ["red"])

    def test_repeat_after_whitespace_collapses(self):
        self.assertEqual(normalize_tags("x,  x , x"), ["x"])


if __name__ == "__main__":
    unittest.main()
