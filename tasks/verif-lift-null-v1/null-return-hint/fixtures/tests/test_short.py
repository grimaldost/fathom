import unittest

from idkit.short import is_short_id, shorten


class ShortIdTests(unittest.TestCase):
    def test_shorten_is_stable(self):
        self.assertEqual(shorten("hello"), shorten("hello"))

    def test_is_short_id_rejects_uppercase(self):
        self.assertFalse(is_short_id("ABC"))


if __name__ == "__main__":
    unittest.main()
