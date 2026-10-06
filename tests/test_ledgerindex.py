"""The ledger index: rendered from a data root's ledgers, checked and re-stamped from there.

The index is compared byte-for-byte, so the properties worth pinning are the ones that
would make that comparison lie: a render that does not move when a ledger does (the gate
goes vacuous), and a digest that moves when only the checkout's line endings do (the gate
accuses an operator of an append that never happened).  The entry points are pinned too:
``python -m fathom.ledgerindex`` is how a data root re-stamps, since ``tools/`` is not
installed with the engine, and ``tools/ledger_index.py`` stays as a shim over it.

Stdlib-only; runs without uv as ``python tests/test_ledgerindex.py``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
FIXTURE = ENGINE / "examples" / "data-root"
sys.path.insert(0, str(ENGINE / "src"))

from fathom import ledgerindex  # noqa: E402

SEEDED = '{"kind": "trial", "scenario": "seeded", "status": "completed"}\n'


def _copy_fixture(tmp: str) -> Path:
    root = Path(tmp) / "data-root"
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("__pycache__"))
    return root


def _ledger(root: Path) -> Path:
    return root / "ledger" / "example.jsonl"


def _append(root: Path, text: str = SEEDED) -> None:
    with _ledger(root).open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _python(
    cwd: Path, *args: str, fathom_home: str | None = None
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    # The developer's own FATHOM_HOME must not steer the child; a test sets its own.
    env.pop("FATHOM_HOME", None)
    if fathom_home is not None:
        env["FATHOM_HOME"] = fathom_home
    env["PYTHONPATH"] = str(ENGINE / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


class RenderTests(unittest.TestCase):
    def test_the_committed_fixture_index_is_current(self) -> None:
        self.assertTrue(ledgerindex.is_current(FIXTURE))

    def test_the_index_moves_when_a_ledger_does(self) -> None:
        """A renderer that silently dropped rows would keep the freshness gate green forever."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            before = ledgerindex.render(root / "ledger")
            _append(root)
            after = ledgerindex.render(root / "ledger")
            self.assertNotEqual(before, after, "the index does not move when a ledger does")
            self.assertIn("seeded:1", after)
            self.assertFalse(ledgerindex.is_current(root))

    def test_the_digest_is_of_canonical_lf_bytes_not_the_checkouts_line_endings(self) -> None:
        """A CRLF checkout must not move the stamp: the digest is of the committed bytes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            lf_render = ledgerindex.render(root / "ledger")
            ledgers = ledgerindex.ledger_files(root / "ledger")
            self.assertTrue(ledgers, "no ledgers copied — the test would be vacuous")
            for path in ledgers:
                canonical = path.read_bytes().replace(b"\r\n", b"\n")
                path.write_bytes(canonical.replace(b"\n", b"\r\n"))
            self.assertEqual(
                lf_render,
                ledgerindex.render(root / "ledger"),
                "converting every ledger to CRLF moved the index: the digest is being taken "
                "over the checkout's line endings rather than the canonical LF bytes git stores",
            )

    def test_archived_ledgers_are_not_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            archive = root / "ledger" / "archive"
            archive.mkdir()
            (archive / "old.jsonl").write_text(SEEDED, encoding="utf-8", newline="\n")
            self.assertTrue(ledgerindex.is_current(root))

    def test_currency_without_ledgers(self) -> None:
        """No ledgers and no index is current; ledgers without an index are not."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(ledgerindex.is_current(root))
            ledgerindex.write(root)
            self.assertTrue(ledgerindex.is_current(root), "a header-only index of no ledgers")
            (root / ledgerindex.INDEX_PATH).unlink()
            (root / "ledger").mkdir()
            (root / "ledger" / "b.jsonl").write_text(SEEDED, encoding="utf-8", newline="\n")
            self.assertFalse(ledgerindex.is_current(root))

    def test_the_header_names_a_command_a_data_root_has(self) -> None:
        """A data root carries no tools/, so the re-render instruction must name the module."""
        self.assertIn("python -m fathom.ledgerindex --write", ledgerindex.HEADER)
        self.assertNotIn("tools/", ledgerindex.HEADER)


class StalenessTests(unittest.TestCase):
    """A stale index says whether a ledger moved or only the engine's rendering did."""

    def test_a_current_index_has_no_staleness(self) -> None:
        self.assertIsNone(ledgerindex.staleness(FIXTURE))

    def test_the_stamps_are_read_back_from_the_rows(self) -> None:
        stamps = ledgerindex.stamps((FIXTURE / ledgerindex.INDEX_PATH).read_text("utf-8"))
        self.assertEqual(list(stamps), ["example"])
        self.assertEqual(stamps["example"], ledgerindex.summarise(_ledger(FIXTURE))["sha256"])

    def test_an_append_names_the_ledger_that_moved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            _append(root)
            stale = ledgerindex.staleness(root)
            self.assertIsNotNone(stale)
            assert stale is not None
            self.assertEqual(stale.kind, "ledgers")
            self.assertIn("`example` changed since the index was stamped", stale.detail)
            self.assertIn("python -m fathom.ledgerindex --write", stale.detail)

    def test_an_added_and_a_removed_ledger_are_named(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            _ledger(root).rename(root / "ledger" / "renamed.jsonl")
            stale = ledgerindex.staleness(root)
            assert stale is not None
            self.assertEqual(stale.kind, "ledgers")
            self.assertIn("`example` has a row but no ledger", stale.detail)
            self.assertIn("`renamed` has no row in the index", stale.detail)

    def test_a_header_change_is_not_reported_as_an_append(self) -> None:
        """A new engine version rewording the header moves no ledger, and must not say so."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            index = root / ledgerindex.INDEX_PATH
            table = index.read_text(encoding="utf-8").split("| Bank |", 1)[1]
            index.write_text(
                "# Ledger index\n\nAn older header, worded differently.\n\n| Bank |" + table,
                encoding="utf-8",
                newline="\n",
            )
            self.assertFalse(ledgerindex.is_current(root))
            stale = ledgerindex.staleness(root)
            assert stale is not None
            self.assertEqual(stale.kind, "rendering")
            self.assertIn("no ledger moved", stale.detail)
            self.assertNotIn("changed since the index was stamped", stale.detail)
            self.assertIn("python -m fathom.ledgerindex --write", stale.detail)

    def test_a_missing_index_over_ledgers_is_unrendered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            (root / ledgerindex.INDEX_PATH).unlink()
            stale = ledgerindex.staleness(root)
            assert stale is not None
            self.assertEqual(stale.kind, "unrendered")
            self.assertIn("no index has been rendered", stale.detail)


class RootMarkerTests(unittest.TestCase):
    """How a root is recognised, including a fathom.toml saved in the wrong encoding."""

    def test_the_fixture_is_a_data_root_and_the_engine_a_checkout(self) -> None:
        self.assertEqual(ledgerindex.root_kind(FIXTURE), "data root")
        self.assertEqual(ledgerindex.root_kind(ENGINE), "engine checkout")
        self.assertIsNone(ledgerindex.root_kind(FIXTURE / "docs"))

    def test_a_utf8_bom_is_accepted(self) -> None:
        """Windows PowerShell 5.1's `-Encoding UTF8` writes a BOM; the file is still UTF-8."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fathom.toml").write_bytes(b"\xef\xbb\xbf[data_root]\nschema = 1\n")
            self.assertEqual(ledgerindex.read_config(root), {"data_root": {"schema": 1}})
            self.assertTrue(ledgerindex.is_data_root(root))

    def test_utf16_and_other_non_utf8_files_are_refused_by_name(self) -> None:
        cases = {
            "utf-16": ("[data_root]\nschema = 1\n".encode("utf-16"), "UTF-16"),
            "latin-1": ("# caf\xe9\n[data_root]\nschema = 1\n".encode("latin-1"), "not UTF-8"),
            "not toml": (b"[data_root\n", "not valid TOML"),
        }
        for label, (raw, message) in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "fathom.toml").write_bytes(raw)
                with self.assertRaises(ledgerindex.ConfigError) as caught:
                    ledgerindex.read_config(root)
                self.assertIn(message, str(caught.exception))
                self.assertIn("fathom.toml", str(caught.exception))
                self.assertFalse(ledgerindex.is_data_root(root), "an unreadable marker")


class MainTests(unittest.TestCase):
    def test_check_write_and_check_again(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            self.assertEqual(ledgerindex.main(["--root", str(root)]), 0)
            _append(root)
            self.assertEqual(ledgerindex.main(["--root", str(root)]), 1, "stale must exit 1")
            self.assertEqual(ledgerindex.main(["--root", str(root), "--write"]), 0)
            self.assertEqual(ledgerindex.main(["--root", str(root)]), 0)
            written = (root / ledgerindex.INDEX_PATH).read_bytes()
            self.assertNotIn(b"\r\n", written, "the index is written with LF endings")

    def test_python_dash_m_runs_from_the_data_root(self) -> None:
        """The working directory is the root; the engine's location plays no part."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            check = ["-m", "fathom.ledgerindex"]
            self.assertEqual(_python(root, *check).returncode, 0)
            _append(root)
            stale = _python(root, *check)
            self.assertEqual(stale.returncode, 1)
            self.assertIn("python -m fathom.ledgerindex --write", stale.stderr)
            self.assertEqual(_python(root, *check, "--write").returncode, 0)
            self.assertEqual(_python(root, *check).returncode, 0)

    def test_a_directory_that_is_no_root_is_refused_and_nothing_is_written(self) -> None:
        """A directory with no data root at or above it has no index to check.

        Checking there would pass for want of ledgers, and ``--write`` would leave a stray,
        header-only index behind, so both are refused with exit 2. An unmarked directory
        that holds a ledger is refused too: the command line would use it with a warning,
        but an index is a claim about a data root, and it has no marker to make one.
        """
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty"
            empty.mkdir()
            unmarked = Path(tmp) / "unmarked"
            (unmarked / "ledger").mkdir(parents=True)
            _append(unmarked)
            for where in (empty, unmarked):
                with self.subTest(where.name):
                    for extra in ([], ["--write"]):
                        proc = _python(where, "-m", "fathom.ledgerindex", *extra)
                        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                        self.assertIn("neither a fathom data root", proc.stderr)
                    self.assertFalse((where / ledgerindex.INDEX_PATH).exists(), "stray index")

    def test_a_subdirectory_checks_and_writes_its_data_roots_index(self) -> None:
        """Inside a data root, the index is the root's, wherever the command starts."""
        with tempfile.TemporaryDirectory() as tmp:
            data_root = _copy_fixture(tmp)
            nested = data_root / "tasks" / "example"
            _append(data_root)
            self.assertEqual(_python(nested, "-m", "fathom.ledgerindex").returncode, 1)
            proc = _python(nested, "-m", "fathom.ledgerindex", "--write")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse((nested / ledgerindex.INDEX_PATH).exists(), "stray index")
            self.assertTrue(ledgerindex.is_current(data_root))

    def test_fathom_home_names_the_root_from_anywhere(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = _copy_fixture(tmp)
            elsewhere = Path(tmp) / "elsewhere"
            elsewhere.mkdir()
            _append(data_root)
            check = ["-m", "fathom.ledgerindex"]
            home = str(data_root)
            self.assertEqual(_python(elsewhere, *check, fathom_home=home).returncode, 1)
            self.assertEqual(_python(elsewhere, *check, "--write", fathom_home=home).returncode, 0)
            self.assertTrue(ledgerindex.is_current(data_root))
            self.assertFalse((elsewhere / "docs").exists(), "stray index")

    def test_fathom_index_is_the_same_check(self) -> None:
        """`fathom index` is this module's check behind the command every install has."""
        with tempfile.TemporaryDirectory() as tmp:
            data_root = _copy_fixture(tmp)
            elsewhere = Path(tmp) / "elsewhere"
            elsewhere.mkdir()
            _append(data_root)
            fathom = ["-m", "fathom", "--home", str(data_root), "index"]
            stale = _python(elsewhere, *fathom)
            self.assertEqual(stale.returncode, 1, stale.stdout + stale.stderr)
            self.assertIn("fathom index --write", stale.stderr)
            self.assertEqual(_python(elsewhere, *fathom, "--write").returncode, 0)
            self.assertEqual(_python(elsewhere, *fathom).returncode, 0)
            refused = _python(elsewhere, "-m", "fathom", "index")
            self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
            self.assertIn("neither a fathom data root", refused.stderr)

    def test_an_unreadable_fathom_toml_is_named_not_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            (root / "fathom.toml").write_bytes("[data_root]\nschema = 1\n".encode("utf-16"))
            proc = _python(root, "-m", "fathom.ledgerindex")
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("UTF-16", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_an_engine_checkout_is_accepted(self) -> None:
        """The shim runs from an engine checkout, which has no ledgers and no index."""
        self.assertEqual(ledgerindex.main(["--root", str(ENGINE)]), 0)

    def test_the_refusal_says_how_to_create_a_data_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for argv in (["-m", "fathom.ledgerindex"], ["-m", "fathom", "index"]):
                with self.subTest(argv=argv):
                    proc = _python(Path(tmp), *argv)
                    self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                    self.assertIn("fathom init", proc.stderr)


def _fake_engine(path: Path) -> Path:
    """What fathom recognises as an engine checkout: its source tree and plugin manifest."""
    (path / "src" / "fathom").mkdir(parents=True)
    (path / "pyproject.toml").write_text(
        '[project]\nname = "fathom"\nversion = "0.0.0"\n', encoding="utf-8"
    )
    (path / ".claude-plugin").mkdir()
    (path / ".claude-plugin" / "plugin.json").write_text(
        '{"name": "fathom", "version": "0.0.0"}', encoding="utf-8"
    )
    return path


class EngineCheckoutTests(unittest.TestCase):
    """One definition of an engine checkout, shared with :mod:`fathom.home`."""

    def test_another_plugins_repository_is_no_root(self) -> None:
        """A plugin manifest alone does not make a directory the engine: index --write must
        not leave an index there, and reconcile must not call it the engine checkout."""
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "other-plugin"
            (other / ".claude-plugin").mkdir(parents=True)
            (other / ".claude-plugin" / "plugin.json").write_text(
                '{"name": "some-other-plugin", "version": "1.0.0"}', encoding="utf-8"
            )
            elsewhere = Path(tmp) / "elsewhere"
            elsewhere.mkdir()
            self.assertIsNone(ledgerindex.root_kind(other))
            runs = {
                "fathom --home index --write": (
                    elsewhere,
                    ["-m", "fathom", "--home", str(other), "index", "--write"],
                    2,
                ),
                "python -m fathom.ledgerindex --write": (
                    other,
                    ["-m", "fathom.ledgerindex", "--write"],
                    2,
                ),
                "fathom --home reconcile": (
                    elsewhere,
                    ["-m", "fathom", "--home", str(other), "reconcile"],
                    13,
                ),
            }
            for label, (cwd, argv, code) in runs.items():
                with self.subTest(label):
                    proc = _python(cwd, *argv)
                    self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
                    self.assertIn("neither a fathom data root", proc.stderr)
                    self.assertNotIn("reconciling the engine checkout", proc.stdout)
            self.assertFalse((other / "docs").exists(), "stray index")

    def test_the_engine_is_recognised_as_fathom_home_recognises_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = _fake_engine(Path(tmp) / "engine")
            self.assertEqual(ledgerindex.root_kind(engine), "engine checkout")
            (engine / "pyproject.toml").write_text(
                '[project]\nname = "not-fathom"\nversion = "0.0.0"\n', encoding="utf-8"
            )
            self.assertIsNone(ledgerindex.root_kind(engine))
        self.assertEqual(ledgerindex.root_kind(ENGINE), "engine checkout")

    def test_writing_an_index_into_an_engine_checkout_is_refused(self) -> None:
        """An engine checkout holds no ledgers, so an index written there stamps nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = _fake_engine(Path(tmp) / "engine")
            for argv in (
                ["-m", "fathom.ledgerindex", "--write"],
                ["-m", "fathom", "--home", str(engine), "index", "--write"],
            ):
                with self.subTest(argv=argv):
                    proc = _python(engine, *argv)
                    self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                    self.assertIn("holds no ledgers", proc.stderr)
                    self.assertFalse((engine / "docs").exists(), "stray index")
            self.assertEqual(_python(engine, "-m", "fathom.ledgerindex").returncode, 0)

    def test_a_header_change_says_so_on_the_command_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            index = root / ledgerindex.INDEX_PATH
            text = index.read_text(encoding="utf-8")
            index.write_text(text.replace("Do not hand-edit.", "Hand-edited."), encoding="utf-8")
            proc = _python(root, "-m", "fathom.ledgerindex")
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("no ledger moved", proc.stderr)

    def test_the_tools_shim_still_works(self) -> None:
        proc = _python(ENGINE, str(ENGINE / "tools" / "ledger_index.py"), "--root", str(FIXTURE))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        sys.path.insert(0, str(ENGINE / "tools"))
        try:
            import ledger_index
        finally:
            sys.path.remove(str(ENGINE / "tools"))
        self.assertIs(ledger_index.render, ledgerindex.render)
        self.assertIs(ledger_index.main, ledgerindex.main)


if __name__ == "__main__":
    unittest.main()
