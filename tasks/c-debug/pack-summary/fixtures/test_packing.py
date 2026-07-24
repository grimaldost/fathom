"""Run: python test_packing.py  ->  prints an ok: line if packing_summary is correct."""

from packing import packing_summary

CASES = [
    (25, 10, "3 boxes (last box holds 5)"),
    (20, 10, "2 boxes (last box holds 10)"),
    (7, 10, "1 box (last box holds 7)"),
]


def main():
    for items, per_box, expected in CASES:
        got = packing_summary(items, per_box)
        assert got == expected, f"packing_summary({items},{per_box}) = {got!r}, want {expected!r}"
    print("ok: all packing_summary cases pass")


if __name__ == "__main__":
    main()
