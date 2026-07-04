"""Baseline tests — pass on the unmodified fixture."""

import unittest

from csvcoalesce import Column


class TestColumn(unittest.TestCase):
    def test_column_holds_name_and_type(self):
        col = Column(name="age", type="int")
        self.assertEqual(col.name, "age")
        self.assertEqual(col.type, "int")


if __name__ == "__main__":
    unittest.main()
