"""The authoring guide: three files, each within the line budget its header states, and every
citation of one of its sections resolves.

The guide to building a bank is three files under ``skills/fathom-eval/reference/``:
``authoring.md``, the entry point, then ``arming.md`` and ``bank-design.md``. Each states a
line budget in a comment at its top, so an addition that would pass it has to displace
something first. These tests hold each file to its budget.

Sections are numbered across the three files and keep their numbers wherever they sit, so a
section number names the same text it did when the guide was one file. A citation says which
file holds the section:

- inside a guide file, a bare "section N" is a section of that file, and a section of another
  guide file is cited with that file's name: "`arming.md`, section 10";
- in any other file, "the authoring guide, section N", "the guide's section N" and "section N
  of the guide" cite ``authoring.md``, and a section of another guide file is cited with that
  file's name, as inside the guide. ``examples/data-root/README.md`` says near its top that
  the sections it cites are the guide's, so its bare "section N" cites ``authoring.md`` too.

A citation followed by a quoted name (section 10, "Treatments") must also name a part of that
section: a ``###`` heading, or a paragraph that opens with the name in bold. The scan covers
the repository's markdown and Python files, except ``CHANGELOG.md``, whose entries describe
the guide as it stood at each release.

Stdlib only; runs without uv (``python tests/test_authoring_guide.py``).
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
REFERENCE = ENGINE / "skills" / "fathom-eval" / "reference"
SKILL = ENGINE / "skills" / "fathom-eval" / "SKILL.md"

ENTRY = "authoring.md"
GUIDE_FILES = ("authoring.md", "arming.md", "bank-design.md")
GUIDE_DIR = "skills/fathom-eval/reference/"

# Outside the guide, files whose bare "section N" cites the guide; each says so near its top.
BARE_CITES_THE_GUIDE = ("examples/data-root/README.md",)
# Files that cite the guide and must keep doing so: a scan that finds nothing in them has
# stopped reading the citations, not found them all correct.
CITING_FILES = (
    "CLAUDE.md",
    "README.md",
    "docs/backlog.md",
    "examples/data-root/README.md",
    "skills/fathom-eval/SKILL.md",
    *(GUIDE_DIR + name for name in GUIDE_FILES),
)
NOT_SCANNED = frozenset({"CHANGELOG.md"})
SKIPPED_DIRS = frozenset(
    {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
)

_BUDGET = re.compile(r"<!--\s*Line budget:\s*(\d+)\s+lines\b", re.IGNORECASE)
_SECTION_HEADING = re.compile(r"^## (\d+)\. ", re.MULTILINE)
_PART = re.compile(r"^(?:### (?P<heading>.+?)\s*$|\*\*(?P<lead>[^*\n]+?)[.:]\*\*)", re.MULTILINE)
_LINK = re.compile(r"\]\(([^)\s]+)\)")

_NUMS = r"(?P<nums>\d+(?:(?:,\s*(?:and\s+)?|\s+(?:and|or|to)\s+)\d+)*)"
_NAME = r'(?:,\s*"(?P<name>[^"\n]+)")?'
_QUALIFIED = re.compile(
    r"(?<![\w.-])`?(?:[\w.-]+/)*(?P<file>authoring|arming|bank-design)\.md`?"
    r"(?:\]\([^)\s]*\))?,?\s+sections?\s+" + _NUMS + _NAME,
    re.IGNORECASE,
)
_BARE = re.compile(r"\bsections?\s+" + _NUMS + _NAME, re.IGNORECASE)
_OF_THE_GUIDE = (
    re.compile(r"\bguide(?:'s)?\)?,?\s*\(?\s*sections?\s+" + _NUMS + _NAME, re.IGNORECASE),
    re.compile(r"\bsections?\s+" + _NUMS + r"\s+of\s+the\s+(?:authoring\s+)?guide\b", re.I),
)


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def guide_text(name: str) -> str:
    return _read(REFERENCE / name)


def sections(name: str) -> dict[int, str]:
    """Section number -> the section's text, heading included, for one guide file."""
    text = guide_text(name)
    found = {}
    for m in _SECTION_HEADING.finditer(text):
        end = text.find("\n## ", m.start() + 1)
        found[int(m.group(1))] = text[m.start() : end if end != -1 else len(text)]
    return found


def parts(section_text: str) -> set[str]:
    """The names a citation may quote for a section: its ### headings and bold leads."""
    names = set()
    for m in _PART.finditer(section_text):
        names.add((m.group("heading") or m.group("lead")).replace("`", "").strip())
    return names


def scanned_files() -> list[str]:
    """The repository's markdown and Python files as POSIX paths relative to it: what git
    tracks or would add, or a walk of the tree without git."""
    try:
        listing = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ENGINE,
            capture_output=True,
            check=True,
            timeout=60,
        ).stdout.decode("utf-8")
        paths = [p for p in listing.split("\0") if p]
    except (OSError, subprocess.SubprocessError):
        paths = []
        for directory, subdirs, names in ENGINE.walk():
            subdirs[:] = [d for d in subdirs if d not in SKIPPED_DIRS]
            paths.extend((directory / n).relative_to(ENGINE).as_posix() for n in names)
    return sorted(
        p
        for p in paths
        if p.endswith((".md", ".py")) and p not in NOT_SCANNED and (ENGINE / p).is_file()
    )


def citations(path: str, text: str) -> list[tuple[str, int, str | None, int]]:
    """(guide file, section number, quoted name or None, line) for each citation in `text`,
    read as `path` (a POSIX path relative to the repository) would be."""
    found: list[tuple[str, int, str | None, int]] = []
    taken: list[tuple[int, int]] = []

    def add(file: str, m: re.Match[str]) -> None:
        numbers = [int(n) for n in re.findall(r"\d+", m.group("nums"))]
        line = text.count("\n", 0, m.start("nums")) + 1
        for index, number in enumerate(numbers):
            name = m.groupdict().get("name") if index == len(numbers) - 1 else None
            found.append((file, number, name, line))

    for m in _QUALIFIED.finditer(text):
        add(m.group("file").lower() + ".md", m)
        taken.append(m.span("nums"))
    if path.startswith(GUIDE_DIR) and path.removeprefix(GUIDE_DIR) in GUIDE_FILES:
        home, patterns = path.removeprefix(GUIDE_DIR), (_BARE,)
    elif path in BARE_CITES_THE_GUIDE:
        home, patterns = ENTRY, (_BARE,)
    else:
        home, patterns = ENTRY, _OF_THE_GUIDE
    for pattern in patterns:
        for m in pattern.finditer(text):
            if not any(start <= m.start("nums") < end for start, end in taken):
                add(home, m)
                taken.append(m.span("nums"))
    return found


class LayoutTests(unittest.TestCase):
    def test_each_file_states_a_line_budget_and_keeps_within_it(self) -> None:
        for name in GUIDE_FILES:
            with self.subTest(file=name):
                text = guide_text(name)
                header = "\n".join(text.split("\n")[:12])
                budget = _BUDGET.search(header)
                self.assertIsNotNone(budget, f"{name} states no line budget in its header")
                assert budget is not None
                lines = len(text.splitlines())
                self.assertLessEqual(
                    lines,
                    int(budget.group(1)),
                    f"{name} has {lines} lines, past its budget of {budget.group(1)}: "
                    "displace something rather than raise the budget",
                )

    def test_the_sections_are_numbered_once_across_the_three_files(self) -> None:
        owner: dict[int, str] = {}
        for name in GUIDE_FILES:
            numbers = [int(n) for n in _SECTION_HEADING.findall(guide_text(name))]
            self.assertTrue(numbers, f"{name} has no numbered section")
            self.assertEqual(numbers, sorted(numbers), f"{name}'s sections are out of order")
            for number in numbers:
                self.assertNotIn(number, owner, f"section {number} is in two files")
                owner[number] = name
        self.assertEqual(sorted(owner), list(range(1, max(owner) + 1)), "a section is missing")

    def test_the_entry_file_and_the_skill_link_every_guide_file(self) -> None:
        entry = guide_text(ENTRY)
        skill = _read(SKILL)
        for name in GUIDE_FILES:
            with self.subTest(file=name):
                self.assertTrue(f"(reference/{name})" in skill, f"SKILL.md does not link {name}")
                if name != ENTRY:
                    self.assertTrue(f"]({name})" in entry, f"{ENTRY} does not link {name}")

    def test_every_relative_link_in_the_guide_and_the_skill_resolves(self) -> None:
        for path in (*(REFERENCE / name for name in GUIDE_FILES), SKILL):
            for target in _LINK.findall(_read(path)):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                with self.subTest(file=path.name, link=target):
                    self.assertTrue((path.parent / target.split("#")[0]).exists())


class CitationTests(unittest.TestCase):
    def test_every_cited_section_is_where_the_citation_says(self) -> None:
        held = {name: sections(name) for name in GUIDE_FILES}
        problems = []
        for path in scanned_files():
            for file, number, name, line in citations(path, _read(ENGINE / path)):
                where = f"{path}:{line}: section {number}"
                if number not in held[file]:
                    elsewhere = [f for f in GUIDE_FILES if number in held[f]]
                    hint = f"; it is in {elsewhere[0]}" if elsewhere else ""
                    problems.append(f"{where} is cited in {file}, which does not hold it{hint}")
                elif name is not None and name not in parts(held[file][number]):
                    problems.append(f'{where} of {file} has no part named "{name}"')
        self.assertEqual(problems, [], "\n".join(problems))

    def test_the_scan_still_finds_the_citations(self) -> None:
        for path in CITING_FILES:
            with self.subTest(file=path):
                self.assertTrue(citations(path, _read(ENGINE / path)), f"no citation in {path}")

    def test_a_citation_reads_as_the_rules_say(self) -> None:
        text = (
            'the authoring guide (`arming.md`, section 10, "Treatments"); the guide\'s\n'
            "section 2; section 7 of the guide; sections 4 and 5 of the authoring guide"
        )
        self.assertEqual(
            sorted(citations("README.md", text), key=lambda c: (c[0], c[1])),
            [
                ("arming.md", 10, "Treatments", 1),
                ("authoring.md", 2, None, 2),
                ("authoring.md", 4, None, 2),
                ("authoring.md", 5, None, 2),
                ("authoring.md", 7, None, 2),
            ],
        )
        bare = "see section 9, and `authoring.md`, sections 2 to 3"
        self.assertEqual(
            sorted(citations(GUIDE_DIR + "bank-design.md", bare)),
            [
                ("authoring.md", 2, None, 1),
                ("authoring.md", 3, None, 1),
                ("bank-design.md", 9, None, 1),
            ],
        )
        self.assertEqual(citations("docs/other.md", "section 9 of the spec"), [])


if __name__ == "__main__":
    unittest.main()
