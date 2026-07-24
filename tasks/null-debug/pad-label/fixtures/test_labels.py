"""Run: python test_labels.py  ->  prints an ok: line if shipping_label is correct."""

from labels import shipping_label

CASES = [
    (42, "ORDER-00042"),
    (7, "ORDER-00007"),
    (12345, "ORDER-12345"),
]


def main():
    for order_id, expected in CASES:
        got = shipping_label(order_id)
        assert got == expected, f"shipping_label({order_id}) = {got!r}, want {expected!r}"
    print("ok: all label cases pass")


if __name__ == "__main__":
    main()
