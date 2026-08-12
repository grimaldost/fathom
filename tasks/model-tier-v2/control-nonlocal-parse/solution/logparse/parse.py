"""Parse a log line into its fields."""

import shlex


def parse_line(line):
    """Split a log line into its space-separated fields.

    REFERENCE FIX (harness-side, never staged). The root cause: ``line.split()``
    knows nothing about the quoted MESSAGE the README documents, so every consumer
    downstream sees the wrong fields. Tokenising with ``shlex`` honours the quotes
    and drops them, which is what the README says the fields are — and it fixes both
    reported symptoms at once, because both consumers read the same fields.
    """
    return shlex.split(line)
