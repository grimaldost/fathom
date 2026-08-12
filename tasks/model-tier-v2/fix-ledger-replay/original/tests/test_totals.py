import unittest

from book.live import fold
from book.replay import replay

POSTS = [
    {"kind": "post", "id": "a", "amount": 100},
    {"kind": "post", "id": "b", "amount": 50},
    {"kind": "post", "id": "c", "amount": 25},
]


class TestTotals(unittest.TestCase):
    def test_fold_adds_up_the_posts(self):
        self.assertEqual(fold(POSTS), {"total": 175, "count": 3})

    def test_the_two_paths_agree_on_a_log_of_posts(self):
        self.assertEqual(fold(POSTS), replay(POSTS))

    def test_replay_drops_a_voided_entry(self):
        log = POSTS + [{"kind": "void", "id": "b"}]
        self.assertEqual(replay(log), {"total": 125, "count": 2})


if __name__ == "__main__":
    unittest.main()
