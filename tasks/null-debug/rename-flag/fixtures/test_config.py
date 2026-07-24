"""Run: python test_config.py  ->  prints an ok: line if the flags are correct."""

from config import is_enabled

CASES = [
    ("darkmode", True),
    ("beta_search", True),
    ("compact_sidebar", False),
    ("nonexistent", False),
]


def main():
    for name, expected in CASES:
        got = is_enabled(name)
        assert got == expected, f"is_enabled({name!r}) = {got!r}, want {expected!r}"
    print("ok: all flag cases pass")


if __name__ == "__main__":
    main()
