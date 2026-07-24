"""Extra test module the trivial change did not need (over-trigger proxy)."""

import settings


def test_max_retries():
    assert settings.MAX_RETRIES == 5


if __name__ == "__main__":
    test_max_retries()
    print("ok: MAX_RETRIES == 5")
