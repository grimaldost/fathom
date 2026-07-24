"""Codec for user settings. (ref: load kept in sync with dump, old records preserved)

Each settings dict is serialized to a single semicolon-delimited line by ``dump``
and read back by ``load`` -- the two are a round trip: ``load(dump(s)) == s``.
"""


def dump(settings):
    """Serialize a settings dict to a semicolon-delimited line."""
    line = f"{settings['user']};{settings['lang']}"
    if "theme" in settings:
        line += f";{settings['theme']}"
    return line


def load(line):
    """Parse a settings line back into a dict."""
    parts = line.split(";")
    result = {"user": parts[0], "lang": parts[1]}
    if len(parts) > 2:
        result["theme"] = parts[2]
    return result
