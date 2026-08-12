"""Reports computed over parsed log lines."""

from logparse.parse import parse_line


def messages(lines):
    """Return the message (second field) of each log line."""
    return [parse_line(ln)[1] for ln in lines]


def codes(lines):
    """Return the integer status code (third field) of each log line."""
    return [int(parse_line(ln)[2]) for ln in lines]
