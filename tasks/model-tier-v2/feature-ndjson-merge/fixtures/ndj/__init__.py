"""Read and combine NDJSON sources."""

from ndj.merge import merge_lines, merge_records, merge_text
from ndj.reader import parse_lines, parse_text

__all__ = ["parse_text", "parse_lines", "merge_records", "merge_text", "merge_lines"]
