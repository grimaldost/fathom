"""Checks that the files this repository publishes carry no private details.

Two checks run over every published file:

- No file may carry the home-directory path of whoever runs the suite. This needs no list.
- No file may contain a name from a list of names that must not be published. The list is
  not part of this repository in any form, plain or hashed: it is read from the file that
  the FATHOM_PRIVATE_NAMES_FILE environment variable names, and the check is skipped when
  the variable is unset. That file holds one name per line; blank lines and lines starting
  with # are ignored, and matching ignores case. It must live outside this repository.

A report names the file and the offset of each hit, never the text it matched, and masks a
hit where it sits in a path, so a failing run does not print what it was looking for.

"Every file the repository publishes" is what `git ls-files` lists as tracked, plus what it
lists as untracked and not ignored, since the next commit can carry that too. Without git
(not installed, or not a checkout) the tree is walked instead, skipping .git, virtual
environments and caches. A binary file is read one character per byte, so both checks
still see ASCII text inside it.

Stdlib only; runs without uv (`python tests/test_public_tree.py`).
"""

from __future__ import annotations

import functools
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent

NAMES_ENV = "FATHOM_PRIVATE_NAMES_FILE"
SHORTEST_NAME = 3  # a shorter entry would match almost any file

SKIPPED_DIRS = frozenset(
    {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
)

Tree = tuple[tuple[str, str], ...]


def walked_files(root: Path) -> list[str]:
    """Every file under `root` as a POSIX path relative to it, skipping SKIPPED_DIRS and
    *.egg-info."""
    found = []
    for directory, subdirs, names in root.walk():
        subdirs[:] = [d for d in subdirs if d not in SKIPPED_DIRS and not d.endswith(".egg-info")]
        found.extend((directory / name).relative_to(root).as_posix() for name in names)
    return sorted(found)


def public_files(root: Path) -> list[str]:
    """The files the public tree carries, as POSIX paths relative to `root` (see the module
    docstring for what that covers)."""
    try:
        listing = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            check=True,
            timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return walked_files(root)
    return sorted({path for path in listing.decode("utf-8").split("\0") if path})


def _decode(data: bytes) -> str:
    """UTF-8 text as text; anything else one character per byte (latin-1)."""
    if b"\0" not in data:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1")


@functools.cache
def public_tree(root: Path) -> Tree:
    """(path, content) for each listed file that exists on disk."""
    tree = []
    for rel in public_files(root):
        path = root / rel
        if path.is_file():  # a listed path can be deleted in the working tree, or a submodule
            tree.append((rel, _decode(path.read_bytes())))
    return tuple(tree)


def home_path_pattern(name: str) -> re.Pattern[str]:
    """Users/<name> and Users\\<name> in any case, with the separator doubled as in an escaped
    string, or flattened to a hyphen as in a directory name built from a path."""
    return re.compile(r"users(?:[\\/]+|-)" + re.escape(name) + r"(?![0-9a-z])", re.IGNORECASE)


def read_names(path: Path) -> list[str]:
    """The names listed in `path`, lowercased (see the module docstring for the format).

    Raises ValueError for an entry shorter than SHORTEST_NAME; the message gives the line
    number and not the entry.
    """
    names = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        if len(entry) < SHORTEST_NAME:
            raise ValueError(
                f"line {number} of the names file is shorter than {SHORTEST_NAME} characters "
                "and would match almost any file"
            )
        names.append(entry.lower())
    return names


def name_spans(text: str, names: list[str]) -> list[tuple[int, int]]:
    """(offset, length) of every occurrence of a name in `text`, ignoring case.

    Offsets index the lowercased text, which is the same length as `text` for every
    character this repository uses; _shown_path withholds a path where it is not.
    """
    lowered = text.lower()
    spans = set()
    for name in names:
        start = lowered.find(name)
        while start != -1:
            spans.add((start, len(name)))
            start = lowered.find(name, start + 1)
    return sorted(spans)


def home_spans(text: str, pattern: re.Pattern[str]) -> list[tuple[int, int]]:
    return [(m.start(), m.end() - m.start()) for m in pattern.finditer(text)]


def _offsets_note(offsets: list[int]) -> str:
    shown = ", ".join(map(str, offsets[:10]))
    more = f" and {len(offsets) - 10} more" if len(offsets) > 10 else ""
    return f"offsets {shown}{more}"


def _shown_path(rel: str, spans: list[tuple[int, int]]) -> str:
    """`rel` with each (offset, length) span masked, so a report never repeats what it found."""
    if not spans:
        return rel
    if len(rel.lower()) != len(rel):  # the spans index the lowered form; do not guess
        return "<path withheld>"
    chars = list(rel)
    for start, length in spans:
        chars[start : start + length] = "*" * length
    return "".join(chars)


def findings(tree: Tree, spans_of) -> list[str]:
    """One line per file whose path or content has a span `spans_of` reports."""
    found = []
    for rel, content in tree:
        in_path = spans_of(rel)
        in_content = sorted({start for start, _ in spans_of(content)})
        if not in_path and not in_content:
            continue
        parts = []
        if in_path:
            parts.append(f"name at {_offsets_note(sorted({start for start, _ in in_path}))}")
        if in_content:
            parts.append(f"content at {_offsets_note(in_content)}")
        found.append(f"{_shown_path(rel, in_path)}: {'; '.join(parts)}")
    return found


def names_file_problem(path: Path, repo: Path) -> str | None:
    """Why the names file cannot be used, or None. It must exist and lie outside `repo`."""
    if not path.is_file():
        return f"{NAMES_ENV} is set, but the file it names does not exist"
    resolved = path.resolve()
    if resolved.is_relative_to(repo.resolve()):
        return (
            f"{NAMES_ENV} names a file inside the repository, where the next commit could "
            "publish it; keep the list outside the repository"
        )
    return None


class HomePathTests(unittest.TestCase):
    def test_the_home_path_forms_are_recognised(self):
        pattern = home_path_pattern("example")
        for text in (
            "C:\\Users\\example\\src",
            "/Users/Example/src",
            '"C:\\\\USERS\\\\EXAMPLE\\\\src"',
            "C--Users-example-Documents",
            "users/example",
        ):
            with self.subTest(text=text):
                self.assertIsNotNone(pattern.search(text))
        for text in ("/Users/examples/src", "/home/example/src", "Users/exampl", "users' example"):
            with self.subTest(text=text):
                self.assertIsNone(pattern.search(text))

    def test_a_finding_gives_the_place_and_not_the_text(self):
        content = "see C:\\Users\\example\\notes"
        tree = (
            ("docs/notes.md", content),
            ("Users/example/a.txt", "nothing here"),
            ("clean.md", "nothing here"),
        )
        pattern = home_path_pattern("example")
        found = findings(tree, functools.partial(home_spans, pattern=pattern))
        self.assertEqual(
            found,
            [
                f"docs/notes.md: content at offsets {content.index('Users')}",
                "*************/a.txt: name at offsets 0",
            ],
        )
        for line in found:
            self.assertNotIn("example", line.lower())


class NamesTests(unittest.TestCase):
    def _names_file(self, text: str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "names.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def test_blank_lines_and_comments_are_ignored_and_names_are_lowercased(self):
        path = self._names_file("# a comment\n\n  Invented-Name  \nOTHER-NAME\n")
        self.assertEqual(read_names(path), ["invented-name", "other-name"])

    def test_a_short_entry_is_refused_without_repeating_it(self):
        path = self._names_file("invented-name\nqz\n")
        with self.assertRaises(ValueError) as caught:
            read_names(path)
        self.assertIn("line 2", str(caught.exception))
        self.assertNotIn("qz", str(caught.exception))

    def test_a_name_is_found_in_any_case_and_masked_in_a_path(self):
        names = ["invented-planted-name"]
        text = "# Notes\n\nThis uses Invented-Planted-NAME here.\n"
        offset = text.lower().index(names[0])
        self.assertEqual(name_spans(text, names), [(offset, len(names[0]))])
        self.assertEqual(name_spans("# Notes\n\nNothing to see.\n", names), [])
        tree = (("docs/INVENTED-PLANTED-NAME.md", text), ("clean.md", "nothing"))
        found = findings(tree, functools.partial(name_spans, names=names))
        masked = "docs/" + "*" * len(names[0]) + ".md"
        self.assertEqual(found, [f"{masked}: name at offsets 5; content at offsets {offset}"])

    def test_the_names_file_must_exist_and_lie_outside_the_repository(self):
        outside = self._names_file("invented-name\n")
        self.assertIsNone(names_file_problem(outside, REPO))
        self.assertIn("does not exist", names_file_problem(outside.with_name("absent"), REPO))
        inside = REPO / "pyproject.toml"
        self.assertIn("inside the repository", names_file_problem(inside, REPO))


class ListingTests(unittest.TestCase):
    def test_without_git_the_walk_skips_git_environments_and_caches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (
                "README.md",
                "src/pkg/mod.py",
                ".git/config",
                ".venv/lib/site.py",
                "src/pkg/__pycache__/mod.cpython-312.pyc",
                ".pytest_cache/v/cache/lastfailed",
                ".ruff_cache/content",
                "pkg.egg-info/PKG-INFO",
            ):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text("x", encoding="utf-8")
            for failure in (FileNotFoundError("git"), subprocess.CalledProcessError(128, "git")):
                with (
                    self.subTest(failure=type(failure).__name__),
                    mock.patch.object(subprocess, "run", side_effect=failure),
                ):
                    self.assertEqual(public_files(root), ["README.md", "src/pkg/mod.py"])

    def test_the_listing_covers_the_tree(self):
        """An empty or partial listing would make every tree test below pass vacuously."""
        paths = {rel for rel, _ in public_tree(REPO)}
        self.assertIn("pyproject.toml", paths)
        self.assertIn("tests/test_public_tree.py", paths)


class PublicTreeTests(unittest.TestCase):
    def test_no_file_carries_the_home_directory_path(self):
        name = Path.home().name
        if len(name) < 3:
            self.skipTest("the home directory name is too short to search for")
        pattern = home_path_pattern(name)
        found = findings(public_tree(REPO), functools.partial(home_spans, pattern=pattern))
        if found:
            self.fail(
                "these files carry the home directory path (matched text withheld):\n"
                + "\n".join(found)
            )

    def test_no_file_contains_a_listed_name(self):
        setting = os.environ.get(NAMES_ENV, "").strip()
        if not setting:
            self.skipTest(f"{NAMES_ENV} is not set; the list is kept outside the repository")
        path = Path(setting).expanduser()
        problem = names_file_problem(path, REPO)
        if problem:
            self.fail(problem)
        names = read_names(path)
        if not names:
            self.fail(f"the file {NAMES_ENV} names lists no names")
        found = findings(public_tree(REPO), functools.partial(name_spans, names=names))
        if found:
            self.fail(
                "these files contain a listed name (matched text withheld):\n" + "\n".join(found)
            )

    def test_the_tree_check_fails_when_a_listed_name_is_present(self):
        """List a harmless word the tree is known to hold: the check must fail, name the
        file and its offsets, and still not print the word."""
        word = "pytest"
        with tempfile.TemporaryDirectory() as tmp:
            names_file = Path(tmp) / "names.txt"
            names_file.write_text(f"# test\n{word}\n", encoding="utf-8")
            with (
                mock.patch.dict(os.environ, {NAMES_ENV: str(names_file)}),
                self.assertRaises(self.failureException) as caught,
            ):
                self.test_no_file_contains_a_listed_name()
        report = str(caught.exception)
        pyproject = (REPO / "pyproject.toml").read_bytes().decode("utf-8")
        expected = sorted({start for start, _ in name_spans(pyproject, [word])})
        self.assertTrue(expected)
        self.assertIn(f"pyproject.toml: content at {_offsets_note(expected)}", report)
        self.assertNotIn(word, report.lower())


if __name__ == "__main__":
    unittest.main()
