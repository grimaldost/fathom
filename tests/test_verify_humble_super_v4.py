"""Tests for the humble-vs-super-v4 (non-local root-cause) bank and its verifiers.

Stdlib-runnable. v4's claim is sharper than v3's: the bug is non-local, so a fix applied
at the *symptom site* (a consumer) is not enough — only fixing the shared root-cause
helper passes. These tests prove that against reference sources, before any spend:

* ``TestUntouchedFixtures`` — the buggy fixture fails the correctness criteria, keeps
  ``no_regression`` green, has no regression test.
* ``TestRootFix`` — fixing the root-cause helper (+ a bug-covering test) passes every
  criterion; without the test, only ``regression_test_present`` is false.
* ``TestBandAidFailsSecondConsumer`` — THE key v4 check: a plausible consumer-local
  band-aid (leaving the root cause untouched) fails a correctness criterion — the second
  consumer / tagged-line case it cannot reach. This is what makes the task reward
  root-cause-tracing rather than symptom-patching.
* ``TestBankIntegrity`` — two live tasks, no holdout; the ``original/`` stash of the
  root-cause module is byte-identical to its fixture (so the swap reintroduces the bug).

Run directly: ``python tests/test_verify_humble_super_v4.py`` (exit 0 on success).
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BANK = REPO / "tasks" / "humble-vs-super-v4"
sys.path.insert(0, str(REPO / "src"))


# --- task 1: fix-nonlocal-parse ------------------------------------------------------

PARSE_ROOT_FIX = '''"""Parse a log line into its fields."""

import shlex


def parse_line(line):
    return shlex.split(line)
'''
# A plausible consumer-local band-aid: rejoin the middle for messages, use the last
# field for codes. Leaves parse_line (the root cause) untouched; fails the tagged cases.
PARSE_BAND_AID = '''"""Reports computed over parsed log lines."""

from logparse.parse import parse_line


def messages(lines):
    out = []
    for ln in lines:
        fields = parse_line(ln)
        msg = " ".join(fields[1:-1]) if len(fields) > 3 else fields[1]
        out.append(msg.strip('"'))
    return out


def codes(lines):
    return [int(parse_line(ln)[-1]) for ln in lines]
'''
PARSE_REG = (
    "import unittest\n\n"
    "from logparse.report import codes, messages\n\n\n"
    "class TestQuoted(unittest.TestCase):\n"
    "    def test_quoted_message_and_code(self):\n"
    "        self.assertEqual(messages(['ERROR \"disk full\" 500 urgent']), ['disk full'])\n"
    "        self.assertEqual(codes(['ERROR \"disk full\" 500 urgent']), [500])\n"
)

# --- task 2: fix-nonlocal-urlkey -----------------------------------------------------

URL_ROOT_FIX = '''"""URL helpers."""


def page_key(url):
    """Return the key identifying the page a URL points to."""
    return url.split("?", 1)[0].rstrip("/")
'''
# Band-aid: canonicalize inside page_counts only; top_page still calls page_key raw.
URL_BAND_AID = '''"""Visit reports over a stream of page URLs."""

from collections import Counter

from urlstats.normalize import page_key


def _canon(u):
    return u.split("?", 1)[0].rstrip("/")


def page_counts(urls):
    return Counter(_canon(u) for u in urls)


def top_page(urls):
    counts = Counter()
    for u in urls:
        counts[page_key(u)] += 1
    return counts.most_common(1)[0][0] if counts else None
'''
URL_REG = (
    "import unittest\n\n"
    "from urlstats.report import page_counts, top_page\n\n\n"
    "class TestCanonical(unittest.TestCase):\n"
    "    def test_query_and_slash_merge(self):\n"
    "        self.assertEqual(dict(page_counts(['/x', '/x/', '/x?a=1'])), {'/x': 3})\n"
    "        self.assertEqual(top_page(['/b', '/x', '/x/', '/x?a=1']), '/x')\n"
)

TASKS = {
    "fix-nonlocal-parse": {
        "root_path": "logparse/parse.py",  # the swapped root-cause module
        "root_fix": PARSE_ROOT_FIX,
        "band_aid_path": "logparse/report.py",  # a DIFFERENT file (consumer)
        "band_aid": PARSE_BAND_AID,
        "regtest": PARSE_REG,
        "reg_name": "test_quoted.py",
        "buggy_true": {"no_regression"},
        "buggy_false": {"messages_quoted", "codes_quoted_tagged"},
        "band_aid_passes": {"no_regression"},
        "band_aid_fails": {"messages_quoted", "codes_quoted_tagged"},
    },
    "fix-nonlocal-urlkey": {
        "root_path": "urlstats/normalize.py",
        "root_fix": URL_ROOT_FIX,
        "band_aid_path": "urlstats/report.py",
        "band_aid": URL_BAND_AID,
        "regtest": URL_REG,
        "reg_name": "test_canonical.py",
        "buggy_true": {"no_regression"},
        "buggy_false": {"page_counts_merge", "top_page_merge"},
        # the band-aid fixes page_counts but NOT top_page (the second consumer)
        "band_aid_passes": {"page_counts_merge", "no_regression"},
        "band_aid_fails": {"top_page_merge"},
    },
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _candidate_view(td: str, task_id: str, overlays: dict, regtest: str | None = None) -> Path:
    """Stage a candidate workspace: the task fixtures with *overlays* applied.

    *overlays* maps a view-relative file path to its replacement source.
    """
    meta = TASKS[task_id]
    view = Path(td) / "view"
    shutil.copytree(BANK / task_id / "fixtures", view)
    for rel, source in overlays.items():
        _write(view / rel, source)
    if regtest:
        _write(view / "tests" / meta["reg_name"], regtest)
    return view


def _run_verify(task_id: str, view: Path) -> tuple[dict, int]:
    proc = subprocess.run(
        [sys.executable, str(BANK / task_id / "verify.py"), str(view)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.stdout.strip(), f"{task_id}: verify emitted no JSON; stderr=\n{proc.stderr}"
    return json.loads(proc.stdout), proc.returncode


class TestUntouchedFixtures(unittest.TestCase):
    def test_buggy_fixture_fails_correctness(self):
        for task_id, meta in TASKS.items():
            with self.subTest(task=task_id):
                crit, code = _run_verify(task_id, BANK / task_id / "fixtures")
                for k in meta["buggy_true"]:
                    self.assertTrue(crit[k], f"{task_id}: {k} should hold on the buggy fixture")
                for k in meta["buggy_false"]:
                    self.assertFalse(crit[k], f"{task_id}: {k} should FAIL on the buggy fixture")
                self.assertFalse(crit["regression_test_present"])
                self.assertNotEqual(code, 0)


class TestRootFix(unittest.TestCase):
    def test_root_fix_with_test_passes_everything(self):
        for task_id, meta in TASKS.items():
            with self.subTest(task=task_id):
                with tempfile.TemporaryDirectory() as td:
                    view = _candidate_view(
                        td, task_id, {meta["root_path"]: meta["root_fix"]}, meta["regtest"]
                    )
                    crit, code = _run_verify(task_id, view)
                    self.assertTrue(all(crit.values()), f"{task_id}: not all true: {crit}")
                    self.assertEqual(code, 0)

    def test_root_fix_without_test_lacks_regression_present(self):
        for task_id, meta in TASKS.items():
            with self.subTest(task=task_id):
                with tempfile.TemporaryDirectory() as td:
                    view = _candidate_view(td, task_id, {meta["root_path"]: meta["root_fix"]})
                    crit, code = _run_verify(task_id, view)
                    self.assertFalse(crit["regression_test_present"])
                    for k, v in crit.items():
                        if k != "regression_test_present":
                            self.assertTrue(v, f"{task_id}: {k} should hold on the root fix")
                    self.assertNotEqual(code, 0)


class TestBandAidFailsSecondConsumer(unittest.TestCase):
    def test_consumer_band_aid_fails_a_correctness_criterion(self):
        for task_id, meta in TASKS.items():
            with self.subTest(task=task_id):
                with tempfile.TemporaryDirectory() as td:
                    view = _candidate_view(td, task_id, {meta["band_aid_path"]: meta["band_aid"]})
                    crit, code = _run_verify(task_id, view)
                    self.assertTrue(
                        meta["band_aid_fails"], f"{task_id}: expected a non-empty fail set"
                    )
                    for k in meta["band_aid_passes"]:
                        self.assertTrue(crit[k], f"{task_id}: band-aid should pass {k}")
                    for k in meta["band_aid_fails"]:
                        self.assertFalse(
                            crit[k],
                            f"{task_id}: band-aid should FAIL {k} (the non-local trap)",
                        )
                    self.assertNotEqual(code, 0, f"{task_id}: band-aid must not pass overall")


class TestBankIntegrity(unittest.TestCase):
    def test_bank_loads_two_live_tasks_no_holdout(self):
        from fathom.taskbank import load_bank

        bank = load_bank(BANK)
        self.assertEqual(bank.name, "humble-vs-super-v4")
        self.assertEqual(bank.dataset_version, "1")
        self.assertEqual(
            sorted(t.id for t in bank.tasks),
            ["fix-nonlocal-parse", "fix-nonlocal-urlkey"],
        )
        self.assertEqual(bank.holdout, [])

    def test_stash_is_byte_identical_to_fixture(self):
        for task_id, meta in TASKS.items():
            with self.subTest(task=task_id):
                fix_src = BANK / task_id / "fixtures" / meta["root_path"]
                stash_src = BANK / task_id / "original" / Path(meta["root_path"]).name
                self.assertEqual(
                    stash_src.read_text(encoding="utf-8"),
                    fix_src.read_text(encoding="utf-8"),
                    f"{task_id}: stashed root-cause module drifted from fixture",
                )
                for shipped in sorted((BANK / task_id / "fixtures" / "tests").glob("*.py")):
                    stashed = BANK / task_id / "original" / "tests" / shipped.name
                    self.assertTrue(stashed.is_file(), f"{task_id}: missing stashed {shipped.name}")
                    self.assertEqual(
                        stashed.read_text(encoding="utf-8"),
                        shipped.read_text(encoding="utf-8"),
                        f"{task_id}: stashed test {shipped.name} drifted from fixture",
                    )


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
