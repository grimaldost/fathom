"""Acceptance verifier for fathom-v1-design (harness-side, scenario-blind).

Delegates to the bank-level ``premortem_verify`` so all tasks score identically; see
that module for what this bank does and does not claim to measure.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import premortem_verify` resolves

import premortem_verify as pv  # noqa: E402

if __name__ == "__main__":
    sys.exit(pv.main(sys.argv))
