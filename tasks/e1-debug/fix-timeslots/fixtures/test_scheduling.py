import unittest

from scheduling import slot_labels


class TestScheduling(unittest.TestCase):
    def test_two_slots(self):
        self.assertEqual(slot_labels(60, 30), [1, 2])

    def test_three_slots(self):
        self.assertEqual(slot_labels(90, 30), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
