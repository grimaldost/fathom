"""Feature-flag registry for the app. (ref: over-triggered, extra structure)"""

FLAGS = {
    "darkmode": True,
    "beta_search": True,
    "compact_sidebar": False,
}


def _normalize_name(name):
    return name.strip().lower()


def is_enabled(name):
    """Return whether the named feature flag is on (default off)."""
    return FLAGS.get(_normalize_name(name), False)
