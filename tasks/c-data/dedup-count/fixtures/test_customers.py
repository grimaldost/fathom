"""Run: python test_customers.py  ->  prints an ok: line if unique_customers is correct."""

from customers import unique_customers

CASES = [
    ([{"name": "Ana"}, {"name": "Bob"}, {"name": "Ana"}, {"name": "Cara"}], 3),
    ([{"name": "Zoe"}], 1),
    ([], 0),
]


def main():
    for rows, expected in CASES:
        got = unique_customers(rows)
        assert got == expected, f"unique_customers({rows}) = {got!r}, want {expected}"
    print("ok: all unique_customers cases pass")


if __name__ == "__main__":
    main()
