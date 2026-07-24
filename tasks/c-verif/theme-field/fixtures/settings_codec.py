"""Codec for user settings for the preferences export.

Each settings dict is serialized to a single semicolon-delimited line by ``dump``
and read back by ``load`` -- the two are a round trip: ``load(dump(s)) == s``.
"""


def dump(settings):
    """Serialize a settings dict to a semicolon-delimited line."""
    return f"{settings['user']};{settings['lang']}"


def load(line):
    """Parse a settings line back into a dict."""
    user, lang = line.split(";")
    return {"user": user, "lang": lang}
