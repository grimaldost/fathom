"""Verifier for the example task: reads only argv[1], the scored result view."""

import json
import subprocess
import sys
from pathlib import Path

# Run in a child process started in the result view, so the agent's code shares neither
# this file's path nor its argv, both of which lie in the data root.
CHECK = "import calc; print(calc.add(2, 3) == 5 and calc.add(-1, 1) == 0)"


def correct(view: Path) -> bool:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", CHECK],
            cwd=view,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False
    lines = proc.stdout.splitlines()
    return proc.returncode == 0 and lines[-1:] == ["True"]


def main() -> int:
    criteria = {"correctness": correct(Path(sys.argv[1]))}
    print(json.dumps(criteria))
    return 0 if criteria["correctness"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
