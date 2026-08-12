"""Regression checks added with the fix."""

import unittest

from textkit.wrap import wrap_words


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(wrap_words('ok unbreakablewordhere ok', 6, strict=True), ['ok', 'unbreakablewordhere', 'ok'])
        self.assertEqual(wrap_words('supercalifragilistic', 5, strict=True), ['supercalifragilistic'])


if __name__ == "__main__":
    unittest.main()
