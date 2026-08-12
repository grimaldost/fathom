"""Acceptance verifier for repair-bijection (harness-side, scenario-blind).

Delegates to the bank-level ``keelgate_verify``, which scores every task with the same pinned
gate; ``profile.json`` beside this file names the criteria this task emits and the fixture
digests it protects. See that module for what this bank does and does not claim to measure.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import keelgate_verify` resolves

import keelgate_verify as kv  # noqa: E402

if __name__ == "__main__":
    sys.exit(kv.main(sys.argv, HERE / "profile.json"))
