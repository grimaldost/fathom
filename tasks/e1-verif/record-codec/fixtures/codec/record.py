"""One-line record serialization for the codec package.

See the package README for the round-trip contract that ``dump`` and ``load``
are meant to satisfy.
"""

DELIM = "|"


def dump(record):
    """Serialize ``record`` (a dict with 'name' and 'note') to a one-line string."""
    return DELIM.join([record["name"], record["note"]])


def load(line):
    """Parse a line produced by ``dump`` back into a record dict."""
    name, note = line.split(DELIM)
    return {"name": name, "note": note}
