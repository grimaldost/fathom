"""Run: python test_totals.py  ->  prints an ok: line if grand_total is correct."""

from totals import grand_total

ROWS = [
    {"sku": "X-1", "amount": 3.0},
    {"sku": "X-2", "amount": 4.5},
    {"sku": "X-3", "amount": 2.25},
]


def main():
    got = grand_total(ROWS)
    expected = 9.75
    assert abs(got - expected) < 1e-9, f"grand_total = {got!r}, want {expected!r}"
    print("ok: grand_total matches")


if __name__ == "__main__":
    main()
