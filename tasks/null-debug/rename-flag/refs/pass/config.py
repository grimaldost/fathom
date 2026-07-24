"""Feature-flag registry for the app. (ref: minimal correct fix)"""

FLAGS = {
    "darkmode": True,
    "beta_search": True,
    "compact_sidebar": False,
}


def is_enabled(name):
    """Return whether the named feature flag is on (default off)."""
    return FLAGS.get(name, False)
