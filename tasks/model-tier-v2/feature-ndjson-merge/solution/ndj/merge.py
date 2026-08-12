"""Combine two NDJSON sources."""

from ndj.reader import parse_lines, parse_text


def merge_records(left, right):
    """Merge two already-parsed record lists."""
    merged = []
    position = {}
    for record in list(left) + list(right):
        key = record.get("id")
        if key in position:
            merged[position[key]] = record
        else:
            position[key] = len(merged)
            merged.append(record)
    return merged


def merge_text(left_text, right_text):
    """Merge two NDJSON documents held in strings."""
    return merge_records(parse_text(left_text), parse_text(right_text))


def merge_lines(left_lines, right_lines):
    """Merge two NDJSON sources read line by line."""
    return merge_records(parse_lines(left_lines), parse_lines(right_lines))
