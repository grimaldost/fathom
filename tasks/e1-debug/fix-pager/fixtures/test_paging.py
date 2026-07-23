import unittest

from paging import page_numbers


class TestPaging(unittest.TestCase):
    def test_two_full_pages(self):
        self.assertEqual(page_numbers(20, 10), [1, 2])

    def test_three_full_pages(self):
        self.assertEqual(page_numbers(30, 10), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
