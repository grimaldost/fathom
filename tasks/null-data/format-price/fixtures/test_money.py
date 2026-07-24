"""Run: python test_money.py  ->  prints an ok: line if format_price is correct."""

from money import format_price

CASES = [
    (1050, "$10.50"),
    (7, "$0.07"),
    (0, "$0.00"),
    (999999, "$9999.99"),
]


def main():
    for cents, expected in CASES:
        got = format_price(cents)
        assert got == expected, f"format_price({cents}) = {got!r}, want {expected!r}"
    print("ok: all price cases pass")


if __name__ == "__main__":
    main()
