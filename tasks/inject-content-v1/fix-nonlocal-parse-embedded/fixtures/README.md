# logparse

Parse and report over application log lines.

A log line is space-separated: `LEVEL MESSAGE CODE [TAG ...]`. The **MESSAGE may be
wrapped in double quotes** so that it can contain spaces — for example
`ERROR "disk full" 500 urgent`. The quotes are not part of the message. After the
numeric `CODE` there may be zero or more single-word tags.

- `parse_line(line)` — the fields of one line
- `messages(lines)` — the message of each line
- `codes(lines)` — the integer code of each line

Run the tests: `python -m unittest discover -s tests -t .`
