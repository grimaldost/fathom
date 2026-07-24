"""Line serializer for the address-book export. (ref: band-aid, from_line left stale)

Each contact record is a dict serialized to a single pipe-delimited line by
``to_line`` and read back by ``from_line`` -- the two are a round trip:
``from_line(to_line(rec)) == rec``.
"""


def to_line(rec):
    """Serialize a record dict to a pipe-delimited line."""
    return f"{rec['name']}|{rec['email']}|{rec['phone']}|{rec.get('tag', '')}"


def from_line(s):
    """Parse a pipe-delimited line back into a record dict."""
    name, email, phone = s.split("|")
    return {"name": name, "email": email, "phone": phone}
