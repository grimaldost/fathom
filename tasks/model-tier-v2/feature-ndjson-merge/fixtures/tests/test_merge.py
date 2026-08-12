import unittest

from ndj.merge import merge_lines, merge_text

LEFT = '{"id": "a", "v": 1}\n{"id": "b", "v": 2}\n'
RIGHT = '{"id": "c", "v": 3}\n'


class TestMerge(unittest.TestCase):
    def test_merge_text_keeps_every_distinct_id_in_order(self):
        self.assertEqual(
            merge_text(LEFT, RIGHT),
            [{"id": "a", "v": 1}, {"id": "b", "v": 2}, {"id": "c", "v": 3}],
        )

    def test_merge_lines_keeps_every_distinct_id_in_order(self):
        self.assertEqual(
            merge_lines(LEFT.splitlines(), RIGHT.splitlines()),
            [{"id": "a", "v": 1}, {"id": "b", "v": 2}, {"id": "c", "v": 3}],
        )

    def test_blank_lines_are_skipped(self):
        self.assertEqual(merge_text('\n{"id": "a", "v": 1}\n\n', ""), [{"id": "a", "v": 1}])


if __name__ == "__main__":
    unittest.main()
