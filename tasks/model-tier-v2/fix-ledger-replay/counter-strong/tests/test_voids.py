import unittest

from book.live import fold
from book.replay import replay


def post(entry_id, amount):
    return {"kind": "post", "id": entry_id, "amount": amount}


def void(entry_id):
    return {"kind": "void", "id": entry_id}


class TestVoids(unittest.TestCase):
    def test_a_voided_entry_counts_for_nothing(self):
        log = [post("a", 100), post("b", 50), void("a")]
        self.assertEqual(fold(log), {"total": 50, "count": 1})
        self.assertEqual(fold(log), replay(log))

    def test_voiding_twice_changes_nothing(self):
        log = [post("a", 100), void("a"), void("a")]
        self.assertEqual(fold(log), replay(log))


if __name__ == "__main__":
    unittest.main()
