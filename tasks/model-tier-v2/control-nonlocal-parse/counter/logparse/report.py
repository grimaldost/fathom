"""Reports computed over parsed log lines.

COUNTER-SOLUTION (harness-side, never staged). The symptom-driven band-aid the v1
score rationale names: patch each consumer at its own symptom site and leave the
shared parser alone. Both reported cases come out right and the shipped suite stays
green, but a line with the optional trailing TAG defeats both band-aids — the join
swallows the code, and ``fields[-1]`` is the tag rather than the code. This is the
violability evidence for the control's two hard criteria; it is NOT part of the
bank's `hard_criteria` derivation, which the control is exempt from.
"""

from logparse.parse import parse_line


def messages(lines):
    """Return the message (second field) of each log line."""
    return [" ".join(parse_line(ln)[1:-1]).strip('"') for ln in lines]


def codes(lines):
    """Return the integer status code (third field) of each log line."""
    return [int(parse_line(ln)[-1]) for ln in lines]
