"""Shipped suite. Green on the current source: the migration set is data and the
suite checks only that it is well formed - it says nothing about any order."""

import unittest

from schema.migrations import MIGRATIONS, by_id


class TestMigrationSet(unittest.TestCase):
    def test_every_migration_has_a_unique_id(self):
        ids = [m["id"] for m in MIGRATIONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_dependency_exists(self):
        known = by_id()
        for migration in MIGRATIONS:
            for dep in migration["depends_on"]:
                self.assertIn(dep, known)

    def test_every_kind_is_known(self):
        for migration in MIGRATIONS:
            self.assertIn(migration["kind"], ("add", "backfill"))


if __name__ == "__main__":
    unittest.main()
