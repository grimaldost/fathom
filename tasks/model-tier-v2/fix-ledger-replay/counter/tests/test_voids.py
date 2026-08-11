import unittest

from book.live import fold
from book.replay import replay


class TestVoids(unittest.TestCase):
    def test_the_two_paths_agree_after_a_void(self):
        log = [
            {"kind": "post", "id": "a", "amount": 100},
            {"kind": "void", "id": "a"},
        ]
        self.assertEqual(fold(log), replay(log))


if __name__ == "__main__":
    unittest.main()
