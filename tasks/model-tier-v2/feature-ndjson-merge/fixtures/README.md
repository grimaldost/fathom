# ndj

Read and combine NDJSON (newline-delimited JSON) sources.

Every record is a JSON object carrying a string `"id"`.

## Reading

- `reader.parse_text(text)` — parse a whole NDJSON document held in one string.
- `reader.parse_lines(lines)` — parse NDJSON from any iterable of lines (an open
  file, a socket, a generator).

Both skip blank lines and return a list of records.

## Merging

Merging combines a **left** (older) and a **right** (newer) source under one rule:

> The result holds **one record per id**. A record on the right **replaces** the
> record with the same id on the left, and the replacement **keeps the position of
> the record it replaced** — the result is in order of first appearance. Ids that
> appear only on one side are kept in the order they were read.

Three entry points implement that one rule, for the three shapes a caller has:

- `merge.merge_records(left, right)` — two already-parsed lists.
- `merge.merge_text(left_text, right_text)` — two NDJSON documents.
- `merge.merge_lines(left_lines, right_lines)` — two line sources.

They must agree: the same data merged through any of the three gives the same
result.

Run the tests: `python -m unittest discover -s tests -t .`
