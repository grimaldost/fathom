"""The guardrail-across-tiers recipe runs as written, without spawning.

``skills/fathom-eval/reference/recipe-guardrail-tiers.md`` is a worked recipe built on
``examples/data-root``. A recipe that cannot be run rots as the command line changes, so this
test executes it. It copies the example data root into a temporary directory, writes every
``toml`` and ``markdown`` block that opens with a ``# <relative path>`` line to that path in
the copy (the header line is not part of the file), and runs every ``fathom ...`` line of the
``sh`` blocks as ``python -m fathom --home <copy> ...``, from inside the copy.

A paid ``run`` line gets ``--dry-run`` appended, which plans without spawning and never
resolves a model id. A line that would spend in any other way (``smoke``, ``verify-arming``)
fails the test, as does any subcommand outside ``validate``, ``run``, ``report``,
``reconcile`` and ``index``: those two belong in the recipe's prose, where the reader is told
to run them and nothing here does.

Stdlib only; runs without uv as ``python tests/test_recipe_guardrail_tiers.py``.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
RECIPE = ENGINE / "skills" / "fathom-eval" / "reference" / "recipe-guardrail-tiers.md"
SKILL = ENGINE / "skills" / "fathom-eval" / "SKILL.md"
FIXTURE = ENGINE / "examples" / "data-root"

# A developer's own FATHOM_HOME must not steer these runs (tests/conftest.py does the same
# under pytest; this covers a bare run).
os.environ.pop("FATHOM_HOME", None)

ALLOWED = {"validate", "run", "report", "reconcile", "index"}
ARMS = ("bare-haiku", "bare-sonnet", "guardrail-haiku", "guardrail-sonnet")
FILE_LANGS = {"toml", "markdown"}

_BLOCK = re.compile(r"^```(\w*)[ \t]*\n(.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)
_HEADER = re.compile(r"^# (\S+\.\w+)[ \t]*$")


def _recipe_text() -> str:
    return RECIPE.read_bytes().decode("utf-8").replace("\r\n", "\n")


def blocks(text: str) -> list[tuple[str, str]]:
    """The fenced blocks of a markdown text as (language, body) pairs, in order."""
    return [(m.group(1), m.group(2)) for m in _BLOCK.finditer(text)]


def file_blocks(text: str) -> list[tuple[str, str]]:
    """(relative path, content) for every toml or markdown block, from its header line.

    A block of those languages without a ``# <path>`` header cannot be materialised, so it
    is an error here rather than text the reader would have to guess a place for.
    """
    found = []
    for lang, body in blocks(text):
        if lang not in FILE_LANGS:
            continue
        first, _, rest = body.partition("\n")
        m = _HEADER.match(first)
        if m is None:
            raise AssertionError(f"a {lang} block does not open with '# <path>': {first!r}")
        found.append((m.group(1), rest))
    return found


def fathom_commands(text: str) -> list[list[str]]:
    """The argument list (after ``fathom``) of every ``fathom ...`` line in the sh blocks.

    A trailing backslash continues the command on the next line; comment lines are skipped.
    """
    commands = []
    for lang, body in blocks(text):
        if lang != "sh":
            continue
        pending = ""
        for raw in body.split("\n"):
            line = raw.strip()
            if not pending and (not line or line.startswith("#")):
                continue
            if line.endswith("\\"):
                pending += line[:-1].rstrip() + " "
                continue
            pending += line
            words = shlex.split(pending)
            pending = ""
            if words and words[0] == "fathom":
                commands.append(words[1:])
    return commands


def is_paid_run(args: list[str]) -> bool:
    return args[:1] == ["run"] and "--dry-run" not in args


class ExtractionTests(unittest.TestCase):
    def test_header_line_names_the_file_and_is_not_part_of_it(self):
        text = '```toml\n# a/b.toml\nname = "x"\n```\n'
        self.assertEqual(file_blocks(text), [("a/b.toml", 'name = "x"\n')])

    def test_a_toml_block_without_a_header_is_refused(self):
        with self.assertRaises(AssertionError):
            file_blocks('```toml\nname = "x"\n```\n')

    def test_other_languages_are_not_files(self):
        self.assertEqual(file_blocks("```text\n# not/a/file.txt\nx\n```\n"), [])

    def test_commands_are_joined_across_continuations_and_comments_skipped(self):
        text = "```sh\n# a comment\nfathom run example \\\n    --repeats 3\nls\n```\n"
        self.assertEqual(fathom_commands(text), [["run", "example", "--repeats", "3"]])

    def test_a_paid_run_is_a_run_without_dry_run(self):
        self.assertTrue(is_paid_run(["run", "example"]))
        self.assertFalse(is_paid_run(["run", "example", "--dry-run"]))
        self.assertFalse(is_paid_run(["report", "example"]))


class RecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _recipe_text()
        cls.commands = fathom_commands(cls.text)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / "data-root"
        shutil.copytree(FIXTURE, cls.root)
        for rel, content in file_blocks(cls.text):
            target = cls.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _fathom(self, args: list[str]) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env.pop("FATHOM_HOME", None)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ENGINE / "src"), *filter(None, [env.get("PYTHONPATH")])]
        )
        env["PYTHONUTF8"] = "1"
        return subprocess.run(
            [sys.executable, "-m", "fathom", "--home", str(self.root), *args],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )

    def test_the_recipe_has_commands_and_files_to_run(self):
        self.assertTrue(file_blocks(self.text), "the recipe writes no scenario files")
        self.assertTrue(self.commands, "the recipe has no fathom command in a sh block")
        self.assertTrue(
            any(is_paid_run(c) for c in self.commands), "the recipe has no paid run line"
        )

    def test_every_command_is_one_the_test_may_run(self):
        for args in self.commands:
            self.assertIn(args[0], ALLOWED, f"fathom {' '.join(args)} may spend or is unlisted")

    def test_every_command_exits_zero_and_a_paid_run_is_only_planned(self):
        planned = []
        for args in self.commands:
            run_args = [*args, "--dry-run"] if is_paid_run(args) else args
            with self.subTest(command=" ".join(args)):
                done = self._fathom(run_args)
                self.assertEqual(
                    done.returncode, 0, f"stdout:\n{done.stdout}\nstderr:\n{done.stderr}"
                )
                if args[0] == "run":
                    self.assertIn("[dry-run] no spawns", done.stdout)
                    planned.append(done.stdout)
        self.assertTrue(planned)
        for out in planned:
            for arm in ARMS:
                self.assertIn(f"{arm} [", out, f"the plan does not name the arm {arm}")

    def test_the_example_root_itself_is_untouched(self):
        # The recipe works on a copy; the checked-in root must not hold its files.
        self.assertFalse((FIXTURE / "scenarios" / "tiers").exists())


class SkillLinkTests(unittest.TestCase):
    def test_skill_md_links_the_recipe(self):
        text = SKILL.read_bytes().decode("utf-8")
        self.assertIn("(reference/recipe-guardrail-tiers.md)", text)


if __name__ == "__main__":
    unittest.main()
