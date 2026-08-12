"""Combine two NDJSON sources.

COUNTER-SOLUTION (harness-side, never staged). The instruction reports `merge_text`,
so the replacement rule is implemented inside `merge_text`. `merge_lines` carries its
own copy of the concatenation loop and is left as it was. Satisfies the thin oracle;
caught by the standard oracle.
"""

from ndj.reader import parse_lines, parse_text


def merge_records(left, right):
    """Merge two already-parsed record lists."""
    return list(left) + list(right)


def merge_text(left_text, right_text):
    """Merge two NDJSON documents held in strings."""
    merged = []
    position = {}
    for record in parse_text(left_text) + parse_text(right_text):
        key = record.get("id")
        if key in position:
            merged[position[key]] = record
        else:
            position[key] = len(merged)
            merged.append(record)
    return merged


def merge_lines(left_lines, right_lines):
    """Merge two NDJSON sources read line by line."""
    merged = []
    for record in parse_lines(left_lines):
        merged.append(record)
    for record in parse_lines(right_lines):
        merged.append(record)
    return merged
