"""An answer key kept beside the verifier.

The guide describes the pattern in
`bank-design.md`, section 9, "An answer key beside the verifier".
A verifier that checks an exact result, such as the set of places the agent had to find or a
file that must match byte for byte, keeps the expected result in a `truth.json` beside
`verify.py`. The guide says the agent's workspace does not hold it, because only
`fixtures/` is staged, and that the verifier reads it through its own path, because it starts
in an empty working directory. These tests hold the engine to both statements.

Stdlib only; runs without uv as ``python tests/test_answer_key.py``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fathom.grading.verifier import run_verifier
from fathom.taskbank import Task, stage_task

REPORT = b"2 call sites\r\n"

VERIFY = """\
import hashlib
import json
import sys
from pathlib import Path

TRUTH = json.loads(Path(__file__).with_name("truth.json").read_text(encoding="utf-8"))


def main() -> int:
    view = Path(sys.argv[1])
    found = view / "found.json"
    report = view / "report.txt"
    criteria = {
        "sites_exact": found.is_file()
        and set(json.loads(found.read_text(encoding="utf-8"))) == set(TRUTH["sites"]),
        "report_identical": report.is_file()
        and hashlib.sha256(report.read_bytes()).hexdigest() == TRUTH["report_sha256"],
    }
    print(json.dumps(criteria))
    return 0 if all(criteria.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
"""


class AnswerKeyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.task_dir = self.tmp / "tasks" / "example" / "sites"
        fixtures = self.task_dir / "fixtures"
        fixtures.mkdir(parents=True)
        (fixtures / "app.py").write_text("def a():\n    b()\n\n\ndef b():\n    a()\n")
        (self.task_dir / "verify.py").write_text(VERIFY, encoding="utf-8")
        truth = {
            "sites": ["app.py:2", "app.py:6"],
            "report_sha256": hashlib.sha256(REPORT).hexdigest(),
        }
        (self.task_dir / "truth.json").write_text(json.dumps(truth), encoding="utf-8")
        self.task = Task(
            id="sites",
            instruction="List the call sites in found.json and write report.txt.",
            limits={},
            verify={"entry": "verify.py"},
            task_dir=self.task_dir,
        )

    def _score(self, sites: list[str], report: bytes) -> dict[str, bool] | None:
        with stage_task(self.task, "main") as workspace:
            (workspace / "found.json").write_text(json.dumps(sites), encoding="utf-8")
            (workspace / "report.txt").write_bytes(report)
            return run_verifier(self.task_dir / "verify.py", workspace).criteria

    def test_the_workspace_holds_the_fixture_and_not_the_answer_key(self) -> None:
        with stage_task(self.task, "main") as workspace:
            staged = sorted(p.name for p in workspace.iterdir() if p.name != ".git")
        self.assertEqual(staged, ["app.py"])

    def test_the_verifier_reads_the_key_beside_it_and_checks_the_exact_answer(self) -> None:
        self.assertEqual(
            self._score(["app.py:6", "app.py:2"], REPORT),
            {"sites_exact": True, "report_identical": True},
        )

    def test_an_extra_site_or_a_changed_byte_fails_its_criterion(self) -> None:
        self.assertEqual(
            self._score(["app.py:2", "app.py:6", "app.py:1"], REPORT.replace(b"\r\n", b"\n")),
            {"sites_exact": False, "report_identical": False},
        )


if __name__ == "__main__":
    unittest.main()
