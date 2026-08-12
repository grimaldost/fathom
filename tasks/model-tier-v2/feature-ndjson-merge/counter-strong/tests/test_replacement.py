import unittest

from ndj.merge import merge_lines, merge_text

LEFT = '{"id": "a", "v": 1}\n{"id": "b", "v": 2}\n'
RIGHT = '{"id": "a", "v": 9}\n'
EXPECTED = [{"id": "a", "v": 9}, {"id": "b", "v": 2}]


class TestReplacement(unittest.TestCase):
    def test_merge_text_replaces_in_place(self):
        self.assertEqual(merge_text(LEFT, RIGHT), EXPECTED)

    def test_merge_lines_replaces_in_place(self):
        self.assertEqual(merge_lines(LEFT.splitlines(), RIGHT.splitlines()), EXPECTED)


if __name__ == "__main__":
    unittest.main()
