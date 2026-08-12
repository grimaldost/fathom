import unittest

from lru.cache import LRUCache


class TestLRUCache(unittest.TestCase):
    def test_get_and_put(self):
        c = LRUCache(2)
        c.put("a", 1)
        self.assertEqual(c.get("a"), 1)
        self.assertIsNone(c.get("missing"))
        self.assertEqual(c.get("missing", -1), -1)

    def test_eviction_on_insert_overflow(self):
        c = LRUCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)  # over capacity: the oldest entry "a" is evicted
        self.assertIsNone(c.get("a"))
        self.assertEqual(c.get("b"), 2)
        self.assertEqual(c.get("c"), 3)

    def test_capacity_must_be_positive(self):
        with self.assertRaises(ValueError):
            LRUCache(0)


if __name__ == "__main__":
    unittest.main()
