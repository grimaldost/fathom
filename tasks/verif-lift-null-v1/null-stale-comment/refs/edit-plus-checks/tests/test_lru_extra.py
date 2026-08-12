import unittest


class ExtraChecks(unittest.TestCase):
    def test_module_imports(self):
        import cachekit.lru  # noqa: F401


if __name__ == "__main__":
    unittest.main()
