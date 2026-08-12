"""Regression checks added with the fix."""

import unittest

from tablekit.width import column_widths


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(column_widths(['id'], [['12345']]), [5])

        self.assertEqual(column_widths(['ab'], [['xyz']]), [3])


if __name__ == "__main__":
    unittest.main()
