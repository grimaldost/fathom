"""Regression checks added with the fix."""

import unittest

from textkit.wrap import wrap_words


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(wrap_words('ok unbreakablewordhere ok', 6), ['ok', 'unbreakablewordhere', 'ok'])

        self.assertEqual(wrap_words('supercalifragilistic', 5), ['supercalifragilistic'])


if __name__ == "__main__":
    unittest.main()
