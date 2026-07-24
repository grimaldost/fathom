"""Run: python test_pricing.py  ->  prints an ok: line if quote_line is correct."""

from pricing import quote_line

CASES = [
    (10, 2.00, "10 x 2.00 = 19.00"),
    (100, 1.00, "100 x 1.00 = 90.00"),
    (9, 2.00, "9 x 2.00 = 18.00"),
    (50, 4.00, "50 x 4.00 = 190.00"),
]


def main():
    for qty, unit_price, expected in CASES:
        got = quote_line(qty, unit_price)
        assert got == expected, f"quote_line({qty},{unit_price}) = {got!r}, want {expected!r}"
    print("ok: all quote_line cases pass")


if __name__ == "__main__":
    main()
