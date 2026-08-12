import unittest

from ndj.merge import merge_text


class TestReplacement(unittest.TestCase):
    def test_merge_text_replaces_in_place(self):
        self.assertEqual(
            merge_text('{"id": "a", "v": 1}\n', '{"id": "a", "v": 9}\n'), [{"id": "a", "v": 9}]
        )


if __name__ == "__main__":
    unittest.main()
