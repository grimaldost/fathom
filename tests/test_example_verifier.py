"""The example data root's verifier: the one the authoring guide shows, and blind as it asks.

The authoring guide (section 7) shows a complete verifier and says it is the one in the
example data root, and asks every verifier to run the agent's code in a child process
started in the result view. Code imported into the verifier's own process shares its
``sys.argv``, whose first entry is the verifier's path in the data root, so it could walk up
to the ledger, the kept streams and each task's ``solution/``. New banks start from this
example, so these tests hold the file to the guide.

Stdlib only; runs without uv as ``python tests/test_example_verifier.py``.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE / "src"))

from fathom.grading.verifier import run_verifier  # noqa: E402

GUIDE = ENGINE / "skills" / "fathom-eval" / "reference" / "authoring.md"
TASK = ENGINE / "examples" / "data-root" / "tasks" / "example" / "add"
VERIFY = TASK / "verify.py"

_GUIDE_INTRO = "A complete verifier (the one in the example data root):\n\n```python\n"


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _guide_block() -> bytes:
    text = _lf(GUIDE.read_bytes()).decode("utf-8")
    start = text.index(_GUIDE_INTRO) + len(_GUIDE_INTRO)
    end = text.index("```\n", start)
    return text[start:end].encode("utf-8")


class ExampleVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _workspace(self, source: Path) -> Path:
        workspace = self.tmp / "workspace"
        shutil.copytree(source, workspace)
        return workspace

    def test_the_guide_shows_the_example_verifier_as_it_is(self) -> None:
        self.assertEqual(_guide_block(), _lf(VERIFY.read_bytes()))

    def test_the_fixture_fails_and_the_solution_passes(self) -> None:
        fixture = run_verifier(VERIFY, TASK / "fixtures")
        self.assertEqual((fixture.outcome, fixture.criteria), ("fail", {"correctness": False}))
        solution = run_verifier(VERIFY, TASK / "solution")
        self.assertEqual((solution.outcome, solution.criteria), ("pass", {"correctness": True}))

    def test_the_agent_code_does_not_see_the_verifier_path(self) -> None:
        """The agent's calc.py runs in a child whose argv names no file of the data root."""
        seen = self.tmp / "seen.txt"
        workspace = self._workspace(TASK / "solution")
        calc = workspace / "calc.py"
        calc.write_text(
            "import sys\n"
            "from pathlib import Path\n"
            f"Path({str(seen)!r}).write_text(repr(sys.argv), encoding='utf-8')\n"
            + calc.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        result = run_verifier(VERIFY, workspace)

        self.assertEqual(result.outcome, "pass", result.stdout + result.stderr)
        argv = seen.read_text(encoding="utf-8")
        self.assertEqual(argv, repr(["-c"]))
        self.assertNotIn("verify.py", argv)


if __name__ == "__main__":
    unittest.main()
