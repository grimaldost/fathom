"""Run: python test_sales.py  ->  prints an ok: line if top_month is correct."""

from sales import top_month

CASES = [
    (
        [
            {"month": "Jan", "amount": "10.00"},
            {"month": "Feb", "amount": "25.00"},
            {"month": "Mar", "amount": "15.00"},
            {"month": "Jan", "amount": "20.00"},
            {"month": "Feb", "amount": "20.00"},
        ],
        "Feb",
    ),
    (
        [
            {"month": "Jul", "amount": "5.00"},
            {"month": "Aug", "amount": "9.00"},
        ],
        "Aug",
    ),
]


def main():
    for rows, expected in CASES:
        got = top_month(rows)
        assert got == expected, f"top_month(...) = {got!r}, want {expected!r}"
    print("ok: all top_month cases pass")


if __name__ == "__main__":
    main()
