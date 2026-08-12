"""Acceptance verifier for trunc-date-range (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result view).  All logic lives
in the bank's shared ``_lib/proxy.py`` so every task in a class is scored by the same
instrument; the per-task detail is the declarative ``spec.json`` beside this file.
Both are task-constant -- identical for every arm -- so reading them leaks no
scenario identity (ADR-0003).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_lib"))

import proxy  # noqa: E402

if __name__ == "__main__":
    sys.exit(proxy.main(Path(__file__).resolve().parent, sys.argv))
