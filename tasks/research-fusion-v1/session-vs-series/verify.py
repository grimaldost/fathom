"""Acceptance verifier for session-vs-series (harness-side, scenario-blind).

Delegates to the bank-level ``fusion_verify``; see that module for what this bank
does and does not claim to measure.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import fusion_verify` resolves

import fusion_verify as fv  # noqa: E402

if __name__ == "__main__":
    sys.exit(fv.main(sys.argv))
