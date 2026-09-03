"""Task bank: load bank manifests, parse task definitions, stage fixture workspaces."""

import os
import shutil
import stat
import subprocess
import tempfile
import tomllib
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class DuplicateTaskIdError(ValueError):
    """Two tasks in the same bank share the same id."""


class MissingFieldError(ValueError):
    """A required field is absent from bank.toml or task.toml."""


class InvalidHoldoutIdError(ValueError):
    """The holdout list references an id not present in the bank."""


@dataclass
class Task:
    id: str
    instruction: str
    limits: dict[str, Any]
    verify: dict[str, Any]
    task_dir: Path
    gate: dict[str, Any] = field(default_factory=dict)


@dataclass
class Bank:
    name: str
    dataset_version: str
    tasks: list[Task]
    holdout: list[str]


def _load_task(task_dir: Path) -> Task:
    with (task_dir / "task.toml").open("rb") as fh:
        data = tomllib.load(fh)

    for required in ("id", "instruction", "limits", "verify"):
        if required not in data:
            raise MissingFieldError(
                f"task.toml in {task_dir} is missing required field '{required}'"
            )

    if not isinstance(data["limits"], dict):
        raise MissingFieldError(
            f"task.toml in {task_dir}: 'limits' must be a TOML table, got scalar"
        )

    verify = data["verify"]
    if not isinstance(verify, dict):
        raise MissingFieldError(
            f"task.toml in {task_dir}: 'verify' must be a TOML table, got scalar"
        )
    if "entry" not in verify:
        raise MissingFieldError(
            f"task.toml in {task_dir} has [verify] but is missing required field 'entry'"
        )

    return Task(
        id=data["id"],
        instruction=data["instruction"],
        limits=dict(data["limits"]),
        verify=dict(verify),
        task_dir=task_dir,
        gate=dict(data.get("gate", {})),
    )


def load_bank(bank_dir: Path) -> Bank:
    """Load a task bank from a directory containing bank.toml and per-task subdirectories."""
    with (bank_dir / "bank.toml").open("rb") as fh:
        data = tomllib.load(fh)

    for required in ("name", "dataset_version", "holdout"):
        if required not in data:
            raise MissingFieldError(
                f"bank.toml in {bank_dir} is missing required field '{required}'"
            )

    if not isinstance(data["holdout"], list):
        raise MissingFieldError(
            f"bank.toml in {bank_dir}: 'holdout' must be a TOML array, got scalar"
        )

    tasks: list[Task] = []
    seen_ids: dict[str, Path] = {}

    for candidate in sorted(bank_dir.iterdir()):
        if candidate.is_dir() and (candidate / "task.toml").exists():
            task = _load_task(candidate)
            if task.id in seen_ids:
                raise DuplicateTaskIdError(
                    f"Duplicate task id '{task.id}' in {seen_ids[task.id]} and {candidate}"
                )
            seen_ids[task.id] = candidate
            tasks.append(task)

    for holdout_id in data["holdout"]:
        if holdout_id not in seen_ids:
            raise InvalidHoldoutIdError(
                f"Holdout id '{holdout_id}' does not reference any task in the bank"
            )

    return Bank(
        name=data["name"],
        dataset_version=data["dataset_version"],
        tasks=tasks,
        holdout=list(data["holdout"]),
    )


def _git(workspace: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(workspace), *args], check=True, capture_output=True)


def _remove_tree(path: str) -> None:
    # Git creates read-only objects on Windows; chmod before retry.
    def _on_error(func: Any, fpath: str, exc: BaseException) -> None:
        try:
            os.chmod(fpath, stat.S_IWRITE)
            func(fpath)
        except Exception:
            pass

    shutil.rmtree(path, onexc=_on_error)


@contextmanager
def stage_task(task: Task, base_branch: str) -> Generator[Path, None, None]:
    """Stage a task's fixtures into a fresh temp workspace as a git repo.

    Copies fixtures/ into a new temp directory, inits a git repo on base_branch
    (never the host default), sets core.autocrlf=false, and commits all fixture
    content as the initial commit. The workspace is removed on context exit.
    """
    tmp_dir = tempfile.mkdtemp(prefix="fathom-stage-")
    try:
        workspace = Path(tmp_dir)

        fixtures_dir = task.task_dir / "fixtures"
        if fixtures_dir.exists():
            shutil.copytree(
                fixtures_dir, workspace, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git")
            )

        # Explicit branch name — never the host default.
        subprocess.run(
            ["git", "init", "-b", base_branch, str(workspace)],
            check=True,
            capture_output=True,
        )

        _git(workspace, "config", "core.autocrlf", "false")
        _git(workspace, "config", "commit.gpgsign", "false")
        _git(workspace, "config", "user.email", "fathom@localhost")
        _git(workspace, "config", "user.name", "fathom")
        _git(workspace, "add", "--all")
        # --allow-empty handles the edge case where fixtures/ is empty.
        _git(workspace, "commit", "--allow-empty", "-m", "Initial fixture commit")

        yield workspace
    finally:
        _remove_tree(tmp_dir)


# ---------------------------------------------------------------------------
# Fixture integrity — the staged baseline must be the committed baseline
# ---------------------------------------------------------------------------

_FINGERPRINT_IGNORED_DIRS = frozenset({"__pycache__", ".git"})
_FINGERPRINT_IGNORED_SUFFIXES = (".pyc", ".pyo")


def _fixture_files(task: Task) -> dict[str, Path]:
    fixtures_dir = task.task_dir / "fixtures"
    files: dict[str, Path] = {}
    if not fixtures_dir.exists():
        return files
    for path in sorted(fixtures_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(fixtures_dir)
        if any(part in _FINGERPRINT_IGNORED_DIRS for part in rel.parts):
            continue
        if path.suffix in _FINGERPRINT_IGNORED_SUFFIXES:
            continue
        files[rel.as_posix()] = path
    return files


def fixture_fingerprint(task: Task) -> str:
    """sha256 over the fixture tree's relative paths and bytes (caches and .git ignored).

    Every trial stages its workspace from ``fixtures/``; an agent that reaches the task
    directory can edit it, and from then on every trial starts from a baseline the bank
    never declared. The fingerprint is recorded on each trial row (``fixture_sha``) and
    compared before and after every trial by ``run_matrix``, which stops the matrix on
    drift instead of buying trials against a corrupted instrument.
    """
    import hashlib

    digest = hashlib.sha256()
    for rel, path in _fixture_files(task).items():
        digest.update(rel.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def fixture_drift(task: Task, expected_files: dict[str, str]) -> list[str]:
    """Paths whose content differs from *expected_files* ({rel path: sha256}), added or removed."""
    import hashlib

    current = {
        rel: hashlib.sha256(path.read_bytes()).hexdigest()
        for rel, path in _fixture_files(task).items()
    }
    changed = [
        rel
        for rel in sorted(set(current) | set(expected_files))
        if current.get(rel) != expected_files.get(rel)
    ]
    return changed


def fixture_manifest(task: Task) -> dict[str, str]:
    """{relative posix path: sha256} for the fixture tree — the basis of :func:`fixture_drift`."""
    import hashlib

    return {
        rel: hashlib.sha256(path.read_bytes()).hexdigest()
        for rel, path in _fixture_files(task).items()
    }
