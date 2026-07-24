"""Run: python test_roundtrip.py  ->  prints an ok: line if the round trip holds.

Serializing a record and parsing it back must reproduce the original record.
"""

from record import from_line, to_line

SAMPLES = [
    {"name": "Ada", "email": "ada@example.com", "phone": "555-0100"},
    {"name": "Bo", "email": "bo@example.com", "phone": "555-0177"},
    {"name": "Cy", "email": "cy@example.com", "phone": "555-0199"},
]


def main():
    for rec in SAMPLES:
        got = from_line(to_line(rec))
        assert got == rec, f"round trip for {rec!r} gave {got!r}"
    print("ok: all round-trip cases pass")


if __name__ == "__main__":
    main()
