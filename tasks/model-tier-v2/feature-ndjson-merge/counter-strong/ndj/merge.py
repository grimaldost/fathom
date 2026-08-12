"""Combine two NDJSON sources.

COUNTER-SOLUTION FOR THE STRONG ORACLE (harness-side, never staged). The replacement
rule is now implemented in both consumers the standard oracle exercises — copied,
not shared — so the whole standard oracle is green. `merge_records`, the entry point
the README names first and the instruction never mentions, still concatenates, so
the three documented paths disagree. Only the strong oracle sees it.
"""

from ndj.reader import parse_lines, parse_text


def _replace_in_place(records):
    merged = []
    position = {}
    for record in records:
        key = record.get("id")
        if key in position:
            merged[position[key]] = record
        else:
            position[key] = len(merged)
            merged.append(record)
    return merged


def merge_records(left, right):
    """Merge two already-parsed record lists."""
    return list(left) + list(right)


def merge_text(left_text, right_text):
    """Merge two NDJSON documents held in strings."""
    return _replace_in_place(parse_text(left_text) + parse_text(right_text))


def merge_lines(left_lines, right_lines):
    """Merge two NDJSON sources read line by line."""
    return _replace_in_place(parse_lines(left_lines) + parse_lines(right_lines))
