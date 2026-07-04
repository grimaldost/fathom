"""Tests for the skill-pyeng-v1 bank and its verifier — stdlib-runnable."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.taskbank import load_bank

BANK_DIR = Path(__file__).parent.parent / "tasks" / "skill-pyeng-v1"
TASK_DIR = BANK_DIR / "modernize-timeflow"


class TestBank(unittest.TestCase):
    def test_bank_loads_one_task(self):
        bank = load_bank(BANK_DIR)
        self.assertEqual(bank.name, "skill-pyeng-v1")
        self.assertEqual(bank.dataset_version, "1")
        self.assertEqual([t.id for t in bank.tasks], ["modernize-timeflow"])
        self.assertEqual(bank.holdout, [])


def _run_verifier(view: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(TASK_DIR / "verify.py"), str(view)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(proc.stdout)


class TestVerifier(unittest.TestCase):
    def test_untouched_fixture_is_noncompliant_but_correct(self):
        view = TASK_DIR / "fixtures"
        results = _run_verifier(view)
        self.assertTrue(results["behavior_preserved"])
        for crit in ("src-layout", "uv", "ruff-single-quote", "dependency-groups", "pip-audit"):
            self.assertFalse(results[crit], f"{crit} should be False on the legacy fixture")

    def test_modernized_copy_flips_compliance(self):
        with tempfile.TemporaryDirectory() as td:
            view = Path(td)
            pkg = view / "src" / "timeflow"
            pkg.mkdir(parents=True)
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "parser.py").write_text(
                (TASK_DIR / "fixtures" / "timeflow" / "parser.py").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (view / "uv.lock").write_text("", encoding="utf-8")
            (view / "pyproject.toml").write_text(
                '[tool.ruff.format]\nquote-style = "single"\n\n[dependency-groups]\n'
                'dev = ["pytest", "pip-audit"]\n',
                encoding="utf-8",
            )
            results = _run_verifier(view)
            self.assertTrue(results["behavior_preserved"])
            self.assertTrue(results["src-layout"])
            self.assertTrue(results["uv"])
            self.assertTrue(results["ruff-single-quote"])
            self.assertTrue(results["dependency-groups"])
            self.assertTrue(results["pip-audit"])

    def test_behavior_preserved_handles_relative_import_refactor(self):
        """A correctly modernized solution may split parser.py and use a relative
        import (`from ._util import ...`) — idiomatic under src-layout, and exactly
        what python-engineering encourages. The verifier must import timeflow as a
        package so such a valid refactor is graded behavior-preserved, not failed
        (failing it would bias the measurement against the treatment arm)."""
        with tempfile.TemporaryDirectory() as td:
            view = Path(td)
            pkg = view / "src" / "timeflow"
            pkg.mkdir(parents=True)
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "_util.py").write_text(
                "from datetime import datetime, timezone\n\n\n"
                "def to_utc(text):\n"
                "    text = text.strip()\n"
                "    if text.endswith('Z'):\n"
                "        text = text[:-1] + '+00:00'\n"
                "    dt = datetime.fromisoformat(text)\n"
                "    if dt.tzinfo is None:\n"
                "        dt = dt.replace(tzinfo=timezone.utc)\n"
                "    return dt.astimezone(timezone.utc)\n",
                encoding="utf-8",
            )
            (pkg / "parser.py").write_text(
                "from ._util import to_utc\n\n\n"
                "def parse_timestamp(text):\n"
                "    return to_utc(text)\n\n\n"
                "def normalize(text):\n"
                "    return parse_timestamp(text).strftime('%Y-%m-%dT%H:%M:%SZ')\n",
                encoding="utf-8",
            )
            results = _run_verifier(view)
            self.assertTrue(
                results["behavior_preserved"],
                "relative-import refactor must not be graded a behavior failure",
            )


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
