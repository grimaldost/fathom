"""Combine two NDJSON sources."""

from ndj.reader import parse_lines, parse_text


def merge_records(left, right):
    """Merge two already-parsed record lists."""
    return list(left) + list(right)


def merge_text(left_text, right_text):
    """Merge two NDJSON documents held in strings."""
    return merge_records(parse_text(left_text), parse_text(right_text))


def merge_lines(left_lines, right_lines):
    """Merge two NDJSON sources read line by line."""
    merged = []
    for record in parse_lines(left_lines):
        merged.append(record)
    for record in parse_lines(right_lines):
        merged.append(record)
    return merged
