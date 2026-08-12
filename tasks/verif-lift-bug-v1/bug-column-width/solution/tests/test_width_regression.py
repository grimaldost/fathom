"""Regression checks added with the fix."""

import unittest

from tablekit.width import column_widths


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(column_widths(['identifier'], [['12']]), [10])

        self.assertEqual(column_widths(['a', 'region'], [['xx', 'eu']]), [2, 6])


if __name__ == "__main__":
    unittest.main()
