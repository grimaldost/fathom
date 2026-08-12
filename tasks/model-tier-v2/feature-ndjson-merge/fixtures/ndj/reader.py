"""Parse NDJSON from a string or from a line source."""

import json


def parse_text(text):
    """Parse a whole NDJSON document held in one string."""
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def parse_lines(lines):
    """Parse NDJSON from any iterable of lines."""
    return [json.loads(line) for line in lines if line.strip()]
