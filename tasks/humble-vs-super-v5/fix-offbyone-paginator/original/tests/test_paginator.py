import unittest

from paginator.core import page_slice, total_pages


class TestPaginator(unittest.TestCase):
    def test_total_pages_exact_multiples(self):
        self.assertEqual(total_pages(20, 10), 2)
        self.assertEqual(total_pages(50, 25), 2)
        self.assertEqual(total_pages(100, 10), 10)

    def test_per_page_must_be_positive(self):
        with self.assertRaises(ValueError):
            total_pages(10, 0)

    def test_page_slice(self):
        self.assertEqual(page_slice(20, 10, 1), (0, 10))
        self.assertEqual(page_slice(20, 10, 2), (10, 20))


if __name__ == "__main__":
    unittest.main()
