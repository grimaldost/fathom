"""A study's replication plan: ``[plan] repeats_per_cell`` in a bank's ``bank.toml``.

A bank may declare how many completed trials each arm x task cell needs before a contrast
from it counts as replicated::

    [plan]
    repeats_per_cell = 3

A plan that declares nothing, or declares 1, makes every result from the bank directional;
so does a cell that holds fewer completed trials than the plan declares. The run's plan
printout, the trial rows, the scorecard and ``fathom reconcile`` all read the status from
here, so they state it by one rule.

The plan is not part of any arm's identity: nothing here enters ``config_hash``, its
preimage, ``dataset_version`` or the resume key, and it does not change what a run buys.
It is parsed apart from :func:`fathom.taskbank.load_bank`, so a malformed plan never stops
the report's other readers of ``bank.toml``.

Stdlib only.
"""

from __future__ import annotations

import dataclasses
import tomllib
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from fathom.ledger import apply_voids

PLAN_TABLE = "plan"
REPEATS_KEY = "repeats_per_cell"
DIRECTIONAL = "directional"
REPLICATED = "replicated"

Cell = tuple[str, str]  # (arm name, task id)


class PlanError(ValueError):
    """The ``[plan]`` table of a ``bank.toml`` is present but malformed."""


def parse_plan(manifest: Mapping[str, Any]) -> int | None:
    """The declared ``repeats_per_cell`` of a parsed ``bank.toml``, or ``None`` when undeclared.

    An absent ``[plan]`` table, or a table without the key, is undeclared. ``plan`` that is
    not a table, a value that is not an integer of 1 or more (a TOML boolean is not an
    integer), and any other key in the table raise :class:`PlanError`: a typo must not read
    as "undeclared".
    """
    if PLAN_TABLE not in manifest:
        return None
    table = manifest[PLAN_TABLE]
    if not isinstance(table, dict):
        raise PlanError(
            f"`{PLAN_TABLE}` must be a table, written [{PLAN_TABLE}]; got {type(table).__name__}"
        )
    unknown = sorted(key for key in table if key != REPEATS_KEY)
    if unknown:
        raise PlanError(
            f"[{PLAN_TABLE}] has unknown key(s) {', '.join(unknown)}; the only key is {REPEATS_KEY}"
        )
    if REPEATS_KEY not in table:
        return None
    value = table[REPEATS_KEY]
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PlanError(
            f"[{PLAN_TABLE}] {REPEATS_KEY} must be an integer of 1 or more, got {value!r}"
        )
    return value


@dataclasses.dataclass(frozen=True)
class PlanReading:
    """What one ``bank.toml`` declares, read without raising.

    ``repeats_per_cell`` is ``None`` when the plan is undeclared, the file is missing
    (``missing``), or the file or its plan cannot be read (``problem`` says why).
    """

    repeats_per_cell: int | None
    path: Path
    problem: str | None = None
    missing: bool = False


def read_plan(bank_dir: Path) -> PlanReading:
    """The plan in ``<bank_dir>/bank.toml``. Never raises: a fault is recorded on the reading."""
    path = Path(bank_dir) / "bank.toml"
    if not path.is_file():
        return PlanReading(None, path, missing=True)
    try:
        with path.open("rb") as fh:
            manifest = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return PlanReading(None, path, problem=f"bank.toml cannot be read: {exc}")
    try:
        return PlanReading(parse_plan(manifest), path)
    except PlanError as exc:
        return PlanReading(None, path, problem=str(exc))


def undeclared_reason(reading: PlanReading, bank_dir: str) -> str:
    """Why *reading* declares no ``repeats_per_cell``; *bank_dir* is the bank as displayed."""
    where = f"{bank_dir}/bank.toml"
    if reading.missing:
        return f"no {where} was found, so no [plan] {REPEATS_KEY} is declared"
    if reading.problem is not None:
        return (
            f"{where} has a malformed [plan] ({reading.problem}), read as declaring "
            f"no {REPEATS_KEY}"
        )
    return f"{where} declares no [plan] {REPEATS_KEY}"


def label(repeats_per_cell: int | None) -> str:
    """The plan in force, as a trial row records it: ``directional`` or ``replicated``."""
    return REPLICATED if repeats_per_cell is not None and repeats_per_cell >= 2 else DIRECTIONAL


def underpowered(n: int, min_repeats: int) -> bool:
    """True when *n* trials fall short of the *min_repeats* a plan declared.

    The one rule for "too few repeats": the calibration control's ``min_repeats`` and the
    plan's ``repeats_per_cell`` are both held by it.
    """
    return n < min_repeats


def current_version_rows(rows: Iterable[dict]) -> list[dict]:
    """*rows* as the scorecard reads them by default: voids applied, and only the current
    ``dataset_version`` (the last-appended trial's) kept. Rows without a version are kept."""
    kept = apply_voids(list(rows))
    versions = [
        r.get("dataset_version")
        for r in kept
        if r.get("kind") == "trial" and r.get("dataset_version") is not None
    ]
    if not versions:
        return kept
    current = versions[-1]
    return [r for r in kept if r.get("dataset_version", current) == current]


def cell_counts(rows: Iterable[dict]) -> dict[Cell, int]:
    """Completed trials per (arm, task) cell of *rows*, attributed as the scorecard does.

    A trial's arm is the ``scenario`` of the last trial row with its ``config_hash``; a cell
    and repeat recorded twice counts its last row. A cell whose trials all failed counts 0.
    """
    trials = [r for r in rows if r.get("kind") == "trial"]
    arm_of: dict[str, str] = {}
    for row in trials:
        ch = row.get("config_hash", "")
        arm_of[ch] = row.get("scenario") or ch
    last: dict[tuple[str, str, Any], dict] = {}
    for row in trials:
        ch = row.get("config_hash", "")
        last[(arm_of.get(ch, ch), row.get("task_id", ""), row.get("repeat", 0))] = row
    counts: dict[Cell, int] = {}
    for (arm, task, _repeat), row in last.items():
        counts[(arm, task)] = counts.get((arm, task), 0) + (row.get("status") == "completed")
    return counts


@dataclasses.dataclass(frozen=True)
class Assessment:
    """The replication status of a set of cells against a declared plan."""

    repeats_per_cell: int | None
    cells: int
    short: tuple[tuple[Cell, int], ...]

    @property
    def directional(self) -> bool:
        return label(self.repeats_per_cell) == DIRECTIONAL or bool(self.short)


def assess(repeats_per_cell: int | None, counts: Mapping[Cell, int]) -> Assessment:
    """Hold *counts* to the plan. Short cells are listed only for a plan of 2 or more: a plan
    of 1, or none, is directional whatever the cells hold."""
    short: tuple[tuple[Cell, int], ...] = ()
    if repeats_per_cell is not None and label(repeats_per_cell) == REPLICATED:
        short = tuple(
            (cell, n) for cell, n in sorted(counts.items()) if underpowered(n, repeats_per_cell)
        )
    return Assessment(repeats_per_cell, len(counts), short)


def plan_line(repeats_per_cell: int | None, run_repeats: int) -> str:
    """The ``replication:`` line of a run's plan: the declared plan against ``--repeats``."""
    if repeats_per_cell is None:
        return (
            f"replication: no [plan] {REPEATS_KEY} in bank.toml; "
            "any contrast from this run is directional"
        )
    if repeats_per_cell == 1:
        return (
            f"replication: {REPEATS_KEY} = 1 in bank.toml, one repeat per cell; "
            "any contrast from this run is directional"
        )
    if run_repeats < repeats_per_cell:
        return (
            f"replication: {REPEATS_KEY} = {repeats_per_cell} in bank.toml, and this run asks "
            f"for {run_repeats} repeat{'' if run_repeats == 1 else 's'} per cell: a screen; "
            "any contrast from it is directional"
        )
    return (
        f"replication: {REPEATS_KEY} = {repeats_per_cell} in bank.toml; this run asks for "
        f"{run_repeats} repeats per cell"
    )


_CONSEQUENCE = "every verdict and contrast below is directional, not replicated."


def scorecard_line(reading: PlanReading, counts: Mapping[Cell, int], bank_dir: str) -> str:
    """The line under a scorecard's title: ``> **Directional:** ...`` or the plan met.

    *bank_dir* is the bank's directory as the scorecard shows it (``tasks/<bank>``), never
    an absolute path. A missing ``bank.toml`` reads as one that declares no plan, so a
    scorecard rendered without the tasks tree is the same as one rendered with a manifest
    that declares none; a malformed plan says so.
    """
    n = reading.repeats_per_cell
    result = assess(n, counts)
    if n is None:
        reason = (
            undeclared_reason(reading, bank_dir)
            if reading.problem is not None
            else f"{bank_dir}/bank.toml declares no [plan] {REPEATS_KEY}"
        )
        return f"> **Directional:** {reason}; {_CONSEQUENCE}"
    if n == 1:
        return (
            f"> **Directional:** {bank_dir}/bank.toml declares {REPEATS_KEY} = 1, "
            f"1 repeat per cell; {_CONSEQUENCE}"
        )
    if result.short:
        return (
            f"> **Directional:** {len(result.short)} of {result.cells} arm x task cells hold "
            f"fewer than the {n} completed trials {bank_dir}/bank.toml declares "
            f"({REPEATS_KEY} = {n}); {_CONSEQUENCE}"
        )
    if not result.cells:
        return f"Replication plan: {REPEATS_KEY} = {n}; no arm x task cell holds a trial yet."
    return (
        f"Replication plan met: {REPEATS_KEY} = {n}, and every arm x task cell "
        f"({result.cells}) holds at least {n} completed trials."
    )
