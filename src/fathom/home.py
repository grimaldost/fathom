"""Finding the data root: the directory that holds a user's evaluation data.

fathom is the engine. The data it runs against lives in a **data root** of the user's
own, which holds:

- ``tasks/<bank>/`` — the task banks;
- ``scenarios/*.toml`` — the arms;
- ``ledger/<bank>.jsonl`` — the append-only record of every trial;
- ``docs/reports/`` (with the generated ``LEDGER-INDEX.md``) and ``docs/STATUS.md`` — the
  write-ups;
- ``.fathom/`` — runtime state (run locks, kept spawn streams), never committed.

A ``fathom.toml`` at its top level with a ``[data_root]`` table (``schema = 1``) marks
it; ``fathom init`` creates one. The schema is the layout version of the data root. This
fathom reads schema 1 only: a marker that declares another schema, or none, is an error
wherever it is met, never a directory to walk past, because an engine that read a newer
layout with this one's rules would read and write it wrongly.

Every command that reads or writes data resolves exactly one data root, in this order:

1. the global option ``fathom --home DIR <command>``;
2. the ``FATHOM_HOME`` environment variable;
3. the nearest directory at or above the working directory whose ``fathom.toml`` has a
   ``[data_root]`` table;
4. the working directory itself, with a warning, when it already looks like a data root
   but carries no marker (it has ``tasks/`` or ``ledger/``).

Anything else is an error that says how to create a data root or point at one. A root
named by ``--home`` or ``FATHOM_HOME`` must carry the marker: a directory named on
purpose is held to what a data root is, and only the working directory gets the
benefit of the doubt in step 4. A relative ``--home`` or ``FATHOM_HOME`` is taken
relative to the working directory. An empty ``--home`` is an error rather than an
omitted one, since it is what a script's unset variable looks like; an empty
``FATHOM_HOME`` means the variable is not set.

A ``fathom.toml`` that exists but cannot be read (not UTF-8, not TOML) stops the search
with an error rather than being walked past: it may be meant as the marker, and walking
past it would pick a data root further up.

The plugin's MCP server loads this file by its path, without importing the fathom
package, so that the server and the command line resolve a data root with the same
code. It therefore imports the standard library only and nothing from fathom.
"""

from __future__ import annotations

import codecs
import dataclasses
import os
import tomllib
from collections.abc import Mapping
from importlib import metadata
from pathlib import Path

CONFIG_FILE = "fathom.toml"
ENV_VAR = "FATHOM_HOME"
SCHEMA = 1

MARKER_LINES = "the two lines '[data_root]' and 'schema = 1'"

HOW_TO = (
    "Create a data root with `fathom init DIR`, or point at an existing one with "
    "`fathom --home DIR <command>` or the FATHOM_HOME environment variable; a command run "
    "anywhere inside a data root finds it on its own."
)

EMPTY_HOME = (
    "--home was given an empty value. Name the data root with --home DIR, or leave --home "
    "out to use FATHOM_HOME or the data root around the working directory."
)


class ConfigError(ValueError):
    """A ``fathom.toml`` exists but cannot be read as UTF-8 TOML."""


class SchemaError(ConfigError):
    """A ``fathom.toml`` has a ``[data_root]`` table whose schema this fathom does not read."""


class DataRootError(RuntimeError):
    """No data root resolves.

    ``found_nothing`` is true when nothing was named and nothing was found, and false
    when something named or found is unusable (a bad ``--home``, a bad ``FATHOM_HOME``,
    an unreadable ``fathom.toml``). Only the first may fall back to another kind of root,
    such as ``fathom reconcile`` checking an engine checkout.
    """

    def __init__(self, message: str, *, found_nothing: bool = False) -> None:
        super().__init__(message)
        self.found_nothing = found_nothing


# Longest first: the UTF-32 little-endian mark begins with the UTF-16 one.
_WIDE_BOMS = (
    (codecs.BOM_UTF32_LE, "UTF-32"),
    (codecs.BOM_UTF32_BE, "UTF-32"),
    (codecs.BOM_UTF16_LE, "UTF-16"),
    (codecs.BOM_UTF16_BE, "UTF-16"),
)


def read_config(root: Path) -> dict | None:
    """*root*'s ``fathom.toml``, parsed; ``None`` when the file does not exist.

    TOML is UTF-8. A leading UTF-8 byte-order mark is accepted, since common Windows
    editors and Windows PowerShell 5.1's ``-Encoding UTF8`` write one. A UTF-16 file, which
    is what that shell's ``>`` and ``Out-File`` write by default, is refused by name rather
    than surfacing as a decode traceback.

    Raises :class:`ConfigError` naming the file when it cannot be read, is not UTF-8, or is
    not valid TOML.
    """
    path = Path(root) / CONFIG_FILE
    if not path.is_file():
        return None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigError(f"{path}: cannot be read ({exc})") from exc
    for bom, encoding in _WIDE_BOMS:
        if raw.startswith(bom):
            raise ConfigError(
                f"{path}: is {encoding} text, and fathom.toml must be UTF-8. Windows "
                "PowerShell 5.1 writes UTF-16 with `>` and Out-File by default; save the file "
                "again as UTF-8"
            )
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ConfigError(
            f"{path}: is not UTF-8 text ({exc}), and fathom.toml must be UTF-8"
        ) from exc
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: not valid TOML ({exc})") from exc


def _engine_version() -> str | None:
    """The installed fathom's version, or ``None`` when it is not installed as a package.

    Read from the package metadata rather than imported: this file imports nothing from
    fathom (see the module docstring).
    """
    try:
        return metadata.version("fathom")
    except metadata.PackageNotFoundError:
        return None


def check_schema(path: Path, table: Mapping[str, object]) -> None:
    """Raise :class:`SchemaError` unless the ``[data_root]`` *table* of *path* is schema 1.

    ``schema`` must be present and be the integer 1. A missing schema is refused rather
    than read as 1: the schema is what lets a later fathom refuse a layout it does not
    know, so every marker states it.
    """
    if "schema" not in table:
        raise SchemaError(
            f"{path}: its [data_root] table has no schema. Add the line 'schema = {SCHEMA}' "
            "under [data_root]"
        )
    value = table["schema"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaError(
            f"{path}: [data_root] schema is {value!r}, and it must be the integer {SCHEMA} "
            f"(write 'schema = {SCHEMA}', without quotes)"
        )
    if value == SCHEMA:
        return
    version = _engine_version()
    this = f"this fathom ({version})" if version else "this fathom"
    if value > SCHEMA:
        raise SchemaError(
            f"{path}: declares [data_root] schema = {value}, and {this} reads schema "
            f"{SCHEMA} only. Upgrade fathom to use this data root"
        )
    raise SchemaError(
        f"{path}: declares [data_root] schema = {value}, which no fathom writes; {this} "
        f"reads schema {SCHEMA}. Write 'schema = {SCHEMA}'"
    )


def has_marker(directory: Path) -> bool:
    """Whether *directory*'s ``fathom.toml`` has a ``[data_root]`` table.

    Raises :class:`ConfigError` when the file exists but cannot be read, and its subclass
    :class:`SchemaError` when the table declares a schema other than 1, or none.
    """
    config = read_config(directory)
    if config is None:
        return False
    table = config.get("data_root")
    if not isinstance(table, dict):
        return False
    check_schema(Path(directory) / CONFIG_FILE, table)
    return True


def looks_like_data_root(directory: Path) -> bool:
    """Whether *directory* holds ``tasks/`` or ``ledger/`` — data, marked or not."""
    return (Path(directory) / "tasks").is_dir() or (Path(directory) / "ledger").is_dir()


def looks_like_engine_checkout(directory: Path) -> bool:
    """Whether *directory* is a fathom engine source tree (``src/fathom/`` beside a
    ``pyproject.toml`` that names the ``fathom`` project)."""
    directory = Path(directory)
    if not (directory / "src" / "fathom").is_dir():
        return False
    try:
        data = tomllib.loads((directory / "pyproject.toml").read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False
    project = data.get("project")
    return isinstance(project, dict) and project.get("name") == "fathom"


def unmarked_reason(directory: Path) -> str:
    """Why a directory whose ``fathom.toml`` is readable is not marked, as one sentence."""
    if not (Path(directory) / CONFIG_FILE).is_file():
        return f"It has no {CONFIG_FILE}."
    return f"Its {CONFIG_FILE} has no [data_root] table."


def how_to_mark(directory: Path) -> str:
    """How to mark *directory* as a data root, as one sentence."""
    if (Path(directory) / CONFIG_FILE).is_file():
        return (
            f"To mark it, add {MARKER_LINES} to its {CONFIG_FILE}; `fathom init {directory}` "
            "then creates whatever else a data root holds."
        )
    return (
        f"To mark it, run `fathom init {directory}` (it creates what is missing and never "
        f"overwrites a file), or create {CONFIG_FILE} at its top level containing {MARKER_LINES}."
    )


@dataclasses.dataclass(frozen=True)
class DataRoot:
    """A resolved data root.

    ``origin`` says how it was found: ``"--home"``, ``"FATHOM_HOME"``, ``"found above"``
    (step 3, the working directory or a directory above it) or ``"working directory"``
    (step 4, unmarked). ``marked`` is false only for step 4.
    """

    path: Path
    origin: str
    marked: bool = True

    def warning(self, *, appends_to: Path | None = None) -> str | None:
        """The stderr warning for an unmarked root, or ``None`` for a marked one."""
        if self.marked:
            return None
        appends = f" This command appends to {appends_to}." if appends_to is not None else ""
        return (
            f"WARNING: {self.path} is not a fathom data root. {unmarked_reason(self.path)} "
            "fathom is using it because it is the working directory and holds tasks/ or "
            f"ledger/.{appends} {how_to_mark(self.path)}"
        )


# What `fathom init` writes. Directories are created empty; files are written only where
# none exists.
LAYOUT_DIRS = ("tasks", "scenarios", "ledger", "docs/reports")

_CONFIG_TEXT = """\
# Marks this directory as a fathom data root. fathom finds it from any directory inside
# it (unless FATHOM_HOME names another), and from anywhere with `fathom --home DIR` or
# FATHOM_HOME set to it.
[data_root]
schema = 1

# `fathom reconcile` fails on any discrepancy not declared here. Declare one only for a
# permanent fact about the recorded history, with its reason:
#
# [[reconcile.known]]
# check = "scenario-known"
# subject = "<bank>"
# key = "<arm>"
# reason = "why this discrepancy is accepted"
#
# An entry whose discrepancy no longer occurs fails the reconcile, so none outlives its cause.
"""

_GITIGNORE_TEXT = """\
# Runtime state fathom writes here: run locks, stop requests, kept spawn streams.
.fathom/
# Scorecards `fathom report` renders. They regenerate from the ledger at any time.
report/
"""

_GITATTRIBUTES_TEXT = """\
# LF line endings on every platform, for every text file. An arm's injected files
# ([context], [settings]) and every file of a mounted plugin are hashed by their bytes into
# the arm's config_hash, whatever their extension, so a checkout that rewrote line endings
# would change the hash, and with it every resume key of that arm. The first rule covers
# every file git sees as text; the rules after it name the common ones explicitly.
* text=auto eol=lf
*.md text eol=lf
*.toml text eol=lf
*.py text eol=lf
*.json text eol=lf
*.jsonl text eol=lf
"""

LAYOUT_FILES = (
    (CONFIG_FILE, _CONFIG_TEXT),
    (".gitignore", _GITIGNORE_TEXT),
    (".gitattributes", _GITATTRIBUTES_TEXT),
)

# Lines a data root's .gitignore needs; `fathom init` names any an existing file lacks.
IGNORED = (".fathom/", "report/")

# The .gitattributes rule that pins LF for every text file; `fathom init` notes an existing
# file without one.
LF_RULE = "* text=auto eol=lf"


def _declares_data_root(directory: Path) -> bool:
    """Whether *directory*'s ``fathom.toml`` has a ``[data_root]`` table, whatever its
    schema; an unreadable file counts as none."""
    try:
        config = read_config(directory)
    except ConfigError:
        return False
    return config is not None and isinstance(config.get("data_root"), dict)


def init_problem(directory: Path) -> str | None:
    """Why ``fathom init`` must not touch *directory*, or ``None`` when it may.

    Checked before anything is written, so a refusal leaves the directory as it was.
    A directory inside an engine checkout is refused as well as the checkout itself: a
    data root holds private banks and ledgers, and inside the engine's working tree,
    which does not ignore them, one commit to the engine would publish them.
    """
    directory = Path(os.path.abspath(directory))
    if directory.exists() and not directory.is_dir():
        return f"{directory} exists and is not a directory."
    if looks_like_engine_checkout(directory):
        return (
            f"{directory} is a fathom engine checkout. A data root is a directory of its "
            "own, outside the engine: for example `fathom init ../my-evals`."
        )
    for parent in directory.parents:
        if looks_like_engine_checkout(parent):
            return (
                f"{directory} is inside the fathom engine checkout at {parent}. A data root "
                "holds your own banks and ledgers, and inside the engine's working tree a "
                "commit to the engine could pick them up. Choose a directory outside it: for "
                f"example `fathom init {parent.parent / 'my-evals'}`."
            )
    try:
        config = read_config(directory)
    except ConfigError as exc:
        return f"{exc}. Fix or remove it, then run `fathom init` again."
    if config is None:
        return None
    table = config.get("data_root")
    if not isinstance(table, dict):
        return (
            f"{directory / CONFIG_FILE} exists and has no [data_root] table, and `fathom "
            f"init` never overwrites a file. Add {MARKER_LINES} to it, then run `fathom init` "
            "again to create whatever else is missing."
        )
    try:
        check_schema(directory / CONFIG_FILE, table)
    except SchemaError as exc:
        return f"{exc}. `fathom init` never overwrites a file."
    return None


def init_notes(directory: Path) -> list[str]:
    """What ``fathom init`` should point out about *directory* without refusing it."""
    directory = Path(os.path.abspath(directory))
    notes = []
    for parent in directory.parents:
        if _declares_data_root(parent):
            notes.append(
                f"{directory} is inside another data root, {parent}. The two keep separate "
                "banks and ledgers, and a command uses the nearest one at or above the "
                "directory it runs in."
            )
            break
    if lacks_lf_rule(directory):
        notes.append(
            f"the existing .gitattributes does not pin LF line endings for every text file. "
            f"Add the line '{LF_RULE}' at its top, unless a .gitattributes higher in the "
            "repository already has it: injected files are hashed by their bytes into each "
            "arm's config_hash, and a checkout that rewrites line endings changes it."
        )
    return notes


def init(directory: Path) -> list[tuple[str, bool]]:
    """Create a data root at *directory*; ``[(relative path, created?), ...]``.

    Never overwrites a file: anything already there is kept and reported as kept. The
    caller checks :func:`init_problem` first.
    """
    directory = Path(directory)
    done: list[tuple[str, bool]] = []
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in LAYOUT_FILES:
        path = directory / name
        if path.exists():
            done.append((name, False))
            continue
        with open(path, "x", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        done.append((name, True))
    for name in LAYOUT_DIRS:
        path = directory / name
        existed = path.is_dir()
        path.mkdir(parents=True, exist_ok=True)
        done.append((f"{name}/", not existed))
    return done


def missing_ignores(directory: Path) -> list[str]:
    """The :data:`IGNORED` entries *directory*'s ``.gitignore`` does not list."""
    try:
        lines = (Path(directory) / ".gitignore").read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError):
        return list(IGNORED)
    listed = {line.strip().lstrip("/") for line in lines}
    return [entry for entry in IGNORED if entry not in listed and entry.rstrip("/") not in listed]


def lacks_lf_rule(directory: Path) -> bool:
    """Whether *directory* has a ``.gitattributes`` with no rule pinning LF for every file.

    A rule for every file is one whose pattern is ``*`` and whose attributes include
    ``eol=lf``. A missing file is not reported: ``fathom init`` writes one.
    """
    path = Path(directory) / ".gitattributes"
    if not path.exists():
        return False
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError):
        return True
    for line in lines:
        fields = line.split()
        if fields and fields[0] == "*" and "eol=lf" in fields[1:]:
            return False
    return True


def _absolute(value: str | os.PathLike[str], cwd: Path) -> Path:
    """*value* made absolute against *cwd*, with ``~`` expanded and ``..`` folded.

    ``os.path.abspath`` rather than ``Path.resolve``: resolving would also expand a
    Windows short (8.3) name, and the same directory would then print differently
    depending on how it was reached.
    """
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = cwd / path
    return Path(os.path.abspath(path))


def _named(raw: str | os.PathLike[str], label: str, cwd: Path) -> DataRoot:
    """The data root named by ``--home`` or ``FATHOM_HOME``; it must carry the marker."""
    path = _absolute(raw, cwd)
    if not path.is_dir():
        raise DataRootError(f"{label} names {path}, which is not a directory. {HOW_TO}")
    try:
        marked = has_marker(path)
    except ConfigError as exc:
        raise DataRootError(f"{label} names {path}, but {exc}.") from exc
    if marked:
        return DataRoot(path, label)
    if looks_like_engine_checkout(path):
        raise DataRootError(
            f"{label} names {path}, which is a fathom engine checkout, not a data root: "
            f"--home and FATHOM_HOME name the directory that holds the data. {HOW_TO}"
        )
    raise DataRootError(
        f"{label} names {path}, which is not a fathom data root. {unmarked_reason(path)} "
        f"{how_to_mark(path)}"
    )


def resolve(
    home: str | os.PathLike[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
) -> DataRoot:
    """The data root a command runs against, found in the order the module docstring gives.

    *home* is the value of ``--home`` (``None`` when it was not given), *env* the process
    environment (default :data:`os.environ`), *cwd* the working directory (default the
    current one). Raises :class:`DataRootError` with a message that says what to do.
    """
    environ = os.environ if env is None else env
    here = Path(os.path.abspath(Path.cwd() if cwd is None else cwd))

    if home is not None:
        named = str(home).strip()
        if not named:
            raise DataRootError(EMPTY_HOME)
        return _named(named, "--home", here)
    raw = environ.get(ENV_VAR, "").strip()
    if raw:
        return _named(raw, ENV_VAR, here)

    for directory in (here, *here.parents):
        try:
            if has_marker(directory):
                return DataRoot(directory, "found above")
        except SchemaError as exc:
            # A data root of a schema this fathom does not read is still a data root: the
            # search stops at it rather than finding an older one further up.
            raise DataRootError(f"{exc}.") from exc
        except ConfigError as exc:
            raise DataRootError(
                f"{exc}. The search for a data root stops there, because that file may be "
                "meant as the marker: fix it, or remove it if it is not one."
            ) from exc

    if looks_like_data_root(here):
        return DataRoot(here, "working directory", marked=False)

    hint = ""
    if looks_like_engine_checkout(here):
        hint = f" {here} is a fathom engine checkout, which holds no data."
    raise DataRootError(
        f"no fathom data root found: --home was not given, FATHOM_HOME is not set, and "
        f"neither {here} nor any directory above it has a {CONFIG_FILE} with a [data_root] "
        f"table.{hint} {HOW_TO}",
        found_nothing=True,
    )
