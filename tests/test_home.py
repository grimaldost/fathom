"""The data-root marker, its schema, and what ``fathom init`` may touch (:mod:`fathom.home`).

The marker is a ``fathom.toml`` whose ``[data_root]`` table says ``schema = 1``. A marker
that declares another schema, or none, is an error wherever it is met: an engine that read a
later layout with this one's rules would read and write it wrongly, and one that walked past
it would pick another data root. An empty ``--home`` is an error too, because it is what a
script's unset variable looks like. ``fathom init`` refuses a directory inside an engine
checkout, where a commit to the engine could publish the data, and notes one inside another
data root.

Stdlib only; runs without uv as ``python tests/test_home.py``.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
EXAMPLE = ENGINE / "examples" / "data-root"
sys.path.insert(0, str(ENGINE / "src"))

# A developer's own FATHOM_HOME must not steer these tests (tests/conftest.py does the same
# under pytest; this covers a bare run).
os.environ.pop("FATHOM_HOME", None)

from fathom import home, ledgerindex  # noqa: E402

GOOD = "[data_root]\nschema = 1\n"
# Markers this fathom refuses, each with a phrase its refusal must carry.
BAD = {
    "a later schema": ("[data_root]\nschema = 2\n", "Upgrade fathom"),
    "no schema": ("[data_root]\n", "has no schema"),
    "the string '1'": ('[data_root]\nschema = "1"\n', "must be the integer 1"),
    "a boolean": ("[data_root]\nschema = true\n", "must be the integer 1"),
    "schema 0": ("[data_root]\nschema = 0\n", "no fathom writes"),
}


def _root(path: Path, marker: str | None = GOOD) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if marker is not None:
        (path / "fathom.toml").write_text(marker, encoding="utf-8")
    for sub in ("tasks", "scenarios", "ledger"):
        (path / sub).mkdir(exist_ok=True)
    return path


def _engine(path: Path) -> Path:
    """A directory fathom recognises as an engine checkout."""
    (path / "src" / "fathom").mkdir(parents=True)
    (path / "pyproject.toml").write_text(
        '[project]\nname = "fathom"\nversion = "0.0.0"\n', encoding="utf-8"
    )
    return path


class SchemaTests(unittest.TestCase):
    """schema = 1 passes; anything else is named and stops the search."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_schema_one_is_a_marker(self) -> None:
        root = _root(self.base / "good")
        self.assertTrue(home.has_marker(root))
        self.assertEqual(home.resolve(None, env={}, cwd=root / "tasks").path, root)
        self.assertEqual(ledgerindex.root_kind(root), "data root")

    def test_every_other_schema_is_refused_by_name(self) -> None:
        for label, (marker, phrase) in BAD.items():
            with self.subTest(label):
                root = _root(self.base / label.replace(" ", "-").replace("'", ""), marker)
                with self.assertRaises(home.SchemaError) as caught:
                    home.has_marker(root)
                self.assertIn(phrase, str(caught.exception))
                self.assertIn(str(root / "fathom.toml"), str(caught.exception))
                for named in ({"home": root, "env": {}}, {"env": {"FATHOM_HOME": str(root)}}):
                    with self.assertRaises(home.DataRootError) as refused:
                        home.resolve(**named, cwd=self.base)
                    self.assertIn(phrase, str(refused.exception))
                self.assertFalse(ledgerindex.is_data_root(root))
                problem = home.init_problem(root)
                self.assertIsNotNone(problem)
                self.assertIn(phrase, problem or "")

    def test_a_later_schema_stops_the_walk_up_instead_of_being_walked_past(self) -> None:
        outer = _root(self.base / "outer")
        newer = _root(outer / "newer", "[data_root]\nschema = 2\n")
        with self.assertRaises(home.DataRootError) as caught:
            home.resolve(None, env={}, cwd=newer / "tasks")
        self.assertIn("schema = 2", str(caught.exception))
        self.assertIn("Upgrade fathom", str(caught.exception))
        self.assertFalse(caught.exception.found_nothing)

    def test_check_root_names_the_schema_of_a_named_root(self) -> None:
        newer = _root(self.base / "newer", "[data_root]\nschema = 2\n")
        with self.assertRaises(ledgerindex.RootError) as caught:
            ledgerindex.check_root(str(newer), command="fathom reconcile", cwd=self.base)
        self.assertIn("schema = 2", str(caught.exception))


class EmptyHomeTests(unittest.TestCase):
    """An empty --home is an error; an empty FATHOM_HOME means the variable is unset."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.a = _root(base / "a")
        self.b = _root(base / "b")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_an_empty_home_does_not_fall_through(self) -> None:
        for value in ("", "   "):
            with self.subTest(repr(value)), self.assertRaises(home.DataRootError) as caught:
                home.resolve(value, env={"FATHOM_HOME": str(self.a)}, cwd=self.b)
            self.assertIn("--home was given an empty value", str(caught.exception))

    def test_an_empty_fathom_home_counts_as_unset(self) -> None:
        found = home.resolve(None, env={"FATHOM_HOME": "  "}, cwd=self.b / "ledger")
        self.assertEqual((found.path, found.origin), (self.b, "found above"))

    def test_check_root_refuses_an_empty_value_under_its_own_option_name(self) -> None:
        for pointer, option in (("--home DIR", "--home"), ("--root DIR", "--root")):
            with self.subTest(option), self.assertRaises(ledgerindex.RootError) as caught:
                ledgerindex.check_root("", command="x", pointer=pointer, cwd=self.a)
            self.assertIn(f"{option} was given an empty value", str(caught.exception))


class InitPlacementTests(unittest.TestCase):
    """Where ``fathom init`` may create a data root."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_it_refuses_a_directory_inside_an_engine_checkout(self) -> None:
        engine = _engine(self.base / "engine")
        for target in (engine / "my-evals", engine / "docs" / "deep" / "evals"):
            with self.subTest(target=target.relative_to(engine).as_posix()):
                problem = home.init_problem(target)
                self.assertIsNotNone(problem)
                self.assertIn("inside the fathom engine checkout", problem or "")
                self.assertIn(str(engine), problem or "")

    def test_this_engine_checkout_is_refused_too(self) -> None:
        problem = home.init_problem(ENGINE / "my-evals")
        self.assertIn("inside the fathom engine checkout", problem or "")

    def test_it_notes_a_directory_inside_another_data_root(self) -> None:
        outer = _root(self.base / "outer")
        target = outer / "docs" / "second"
        self.assertIsNone(home.init_problem(target))
        notes = home.init_notes(target)
        self.assertEqual(len(notes), 1, notes)
        self.assertIn(f"inside another data root, {outer}", notes[0])
        self.assertEqual(home.init_notes(self.base / "alone"), [])


class LineEndingTests(unittest.TestCase):
    """The .gitattributes init writes pins LF for every text file, not five extensions."""

    def test_the_first_rule_covers_every_file(self) -> None:
        rules = [
            line
            for line in dict(home.LAYOUT_FILES)[".gitattributes"].splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(rules[0], home.LF_RULE)
        self.assertEqual(home.LF_RULE, "* text=auto eol=lf")

    def test_an_existing_file_without_the_rule_is_noted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(home.lacks_lf_rule(root), "no file: init writes one")
            attributes = root / ".gitattributes"
            attributes.write_text("*.md text eol=lf\n", encoding="utf-8")
            self.assertTrue(home.lacks_lf_rule(root))
            self.assertTrue(any(".gitattributes" in n for n in home.init_notes(root)))
            attributes.write_text("# pinned\n* text eol=lf\n", encoding="utf-8")
            self.assertFalse(home.lacks_lf_rule(root))
            attributes.write_text(home.LF_RULE + "\n", encoding="utf-8")
            self.assertFalse(home.lacks_lf_rule(root))
            self.assertEqual(home.init_notes(root), [])


class ExampleRootTests(unittest.TestCase):
    """The example data root is what ``fathom init`` makes, so a copy of it keeps the LF pin."""

    def test_it_carries_the_files_init_writes(self) -> None:
        for name, text in home.LAYOUT_FILES:
            if name == home.CONFIG_FILE:
                continue
            with self.subTest(name):
                self.assertEqual((EXAMPLE / name).read_bytes(), text.encode("utf-8"))
        self.assertTrue(home.has_marker(EXAMPLE))


if __name__ == "__main__":
    unittest.main()
