"""Line serializer for the address-book export. (ref: disciplined, round trip preserved)

Each contact record is a dict serialized to a single pipe-delimited line by
``to_line`` and read back by ``from_line`` -- the two are a round trip:
``from_line(to_line(rec)) == rec``.
"""


def to_line(rec):
    """Serialize a record dict to a pipe-delimited line."""
    fields = [rec["name"], rec["email"], rec["phone"]]
    if "tag" in rec:
        fields.append(rec["tag"])
    return "|".join(fields)


def from_line(s):
    """Parse a pipe-delimited line back into a record dict."""
    parts = s.split("|")
    rec = {"name": parts[0], "email": parts[1], "phone": parts[2]}
    if len(parts) > 3:
        rec["tag"] = parts[3]
    return rec
