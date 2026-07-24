"""Run: python test_roundtrip.py  ->  prints an ok: line if the round trip holds."""

from settings_codec import dump, load

CASES = [
    {"user": "ana", "lang": "en"},
    {"user": "bob", "lang": "pt"},
]


def main():
    for settings in CASES:
        restored = load(dump(settings))
        assert restored == settings, f"round trip broke for {settings}: got {restored!r}"
    print("ok: round trip holds")


if __name__ == "__main__":
    main()
