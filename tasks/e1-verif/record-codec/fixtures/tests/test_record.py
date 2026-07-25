import unittest

from codec import dump, load


class TestRecord(unittest.TestCase):
    def test_roundtrip_plain(self):
        rec = {"name": "bob", "note": "hello world"}
        self.assertEqual(load(dump(rec)), rec)

    def test_roundtrip_empty_note(self):
        rec = {"name": "amy", "note": ""}
        self.assertEqual(load(dump(rec)), rec)


if __name__ == "__main__":
    unittest.main()
