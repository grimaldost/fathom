"""Append-only JSONL ledger for trial, run, and grading records."""

from __future__ import annotations

import dataclasses
import json
import pathlib
import warnings
from typing import Any, Iterator

LEDGER_DIR = pathlib.Path("ledger")


@dataclasses.dataclass
class TrialRecord:
    bank: str
    task_id: str
    repeat: int
    status: str  # "completed" | "errored"
    dataset_version: str
    config_hash: str
    tool_git_sha: str
    cli_version: str
    pin_level: str  # "strong" | "series"
    verifier_results: dict[str, Any] | None = None
    detail: str = ""  # strategy note (gate first/final, fix count) for defect-escape recovery
    config_preimage: str = ""  # the exact string config_hash digests; additive (ADR-0002).
    # Recomputing a hash from scenarios/ is inference about the past: 45% of committed
    # hashes cannot be reproduced that way, because config_hash embeds a plugin tree_sha
    # globbed from a live filesystem and most mounts point at an external repo under
    # active development. Stored here, the check is exact — sha256(preimage) either equals
    # config_hash or the row is corrupt — and that answer does not change when the tree
    # does. Empty on every line written before 0.4.0, which is reported, never guessed at.
    started_at: str = ""  # ISO-8601 UTC, seconds ("2026-09-03T21:05:07Z"); additive (ADR-0002).
    ended_at: str = ""
    # `started_at` is when the trial's spawn began, `ended_at` when this row was written.
    # A matrix that ran across several days had nothing on a row saying when it happened;
    # the iteration-1 multiagent review had to date trials from stream file names. Empty
    # on every line written before the fields existed — reported, never back-filled.
    kind: str = dataclasses.field(default="trial", init=False)


@dataclasses.dataclass
class RunRecord:
    bank: str
    task_id: str
    repeat: int
    usage: dict[str, Any]
    turns: int
    duration: float
    exit_code: int
    dataset_version: str
    config_hash: str
    tool_git_sha: str
    cli_version: str
    pin_level: str  # "strong" | "series"
    cost_usd_est: float = 0.0  # adapter-computed USD estimate; additive (ADR-0002).
    # Defaults to 0.0 so pre-existing lines without the field still load — no old
    # line is ever rewritten (append-only invariant).
    model_id: str = ""  # exact model id the CLI reported (the strong pin, ADR-0001);
    # additive default "" so legacy lines load unchanged. Was computed by the adapter
    # but dropped at the cli.py ledger boundary — the pin the design advertises but
    # never persisted until this field existed.
    config_preimage: str = ""  # the exact string config_hash digests; additive (ADR-0002).
    # Recomputing a hash from scenarios/ is inference about the past: 45% of committed
    # hashes cannot be reproduced that way, because config_hash embeds a plugin tree_sha
    # globbed from a live filesystem and most mounts point at an external repo under
    # active development. Stored here, the check is exact — sha256(preimage) either equals
    # config_hash or the row is corrupt — and that answer does not change when the tree
    # does. Empty on every line written before 0.4.0, which is reported, never guessed at.
    started_at: str = ""  # ISO-8601 UTC, seconds; additive (ADR-0002). Same meaning as on
    ended_at: str = ""  # TrialRecord: the owning trial's spawn start, and this row's write.
    kind: str = dataclasses.field(default="run", init=False)


@dataclasses.dataclass
class GradingRecord:
    bank: str
    task_id: str
    repeat: int
    verdict: str  # "a" | "b" | "tie"
    dataset_version: str
    config_hash_a: str
    config_hash_b: str
    tool_git_sha: str
    cli_version: str
    judge_config_hash: str
    judge_model: str
    pin_level: str  # "strong" | "series"
    kind: str = dataclasses.field(default="grading", init=False)


@dataclasses.dataclass
class VoidRecord:
    """Append-only exclusion of one recorded trial (and its run rows).

    A void names a (bank, dataset_version, task_id, config_hash, repeat) key and the
    reason its recorded outcome must not be read — an instrument defect discovered after
    the fact (a mutated fixture, an agent that reached the harness), never a result the
    reader dislikes. Order matters: a void applies to the trial and run rows written
    BEFORE it, so the same key can be re-run afterwards and the re-run counts. The
    original rows stay in the file, as the append-only invariant requires; every reader
    goes through :func:`apply_voids` or :func:`completed_keys`, which honour the order.
    """

    bank: str
    task_id: str
    repeat: int
    dataset_version: str
    config_hash: str
    scenario: str
    reason: str
    evidence: str = ""
    voided_at: str = ""
    kind: str = dataclasses.field(default="void", init=False)


_KIND_MAP: dict[str, type] = {
    "trial": TrialRecord,
    "run": RunRecord,
    "grading": GradingRecord,
    "void": VoidRecord,
}


def _row_key(row: dict[str, Any]) -> tuple[str, str, str, str, int]:
    return (
        str(row.get("bank", "")),
        str(row.get("dataset_version", "")),
        str(row.get("task_id", "")),
        str(row.get("config_hash", "")),
        int(row.get("repeat", 0) or 0),
    )


def apply_voids(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The rows a reader may use: trial and run rows voided by a later void row are dropped.

    A void row drops every ``trial`` and ``run`` row with its key that precedes it; rows
    with that key appended after the void (a re-run) survive. Void rows themselves are
    kept, so a report can say what was excluded and why. Pure; order-preserving.
    """
    kept: list[dict[str, Any]] = []
    for row in rows:
        if row.get("kind") == "void":
            key = _row_key(row)
            kept = [r for r in kept if r.get("kind") not in ("trial", "run") or _row_key(r) != key]
        kept.append(row)
    return kept


def _from_dict(data: dict[str, Any]) -> TrialRecord | RunRecord | GradingRecord | dict[str, Any]:
    kind = data.get("kind")
    cls = _KIND_MAP.get(kind)  # type: ignore[arg-type]
    if cls is None:
        return data  # Unknown kind: round-trip untouched
    init_fields = {f.name for f in dataclasses.fields(cls) if f.init}
    kwargs = {k: v for k, v in data.items() if k in init_fields}
    return cls(**kwargs)


def append_record(bank: str, record: Any, *, ledger_dir: pathlib.Path = LEDGER_DIR) -> None:
    """Append one record to the per-bank JSONL file. Only ever opens in append mode."""
    ledger_dir.mkdir(parents=True, exist_ok=True)
    path = ledger_dir / f"{bank}.jsonl"
    if dataclasses.is_dataclass(record) and not isinstance(record, type):
        data = dataclasses.asdict(record)
    else:
        data = dict(record)
    line = json.dumps(data, sort_keys=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def iter_records(bank: str, *, ledger_dir: pathlib.Path = LEDGER_DIR) -> Iterator[Any]:
    """Yield records from the per-bank JSONL file. Skips malformed lines with a warning."""
    path = ledger_dir / f"{bank}.jsonl"
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
                yield _from_dict(data)
            except Exception as exc:
                warnings.warn(
                    f"Skipping malformed record at {path}:{lineno}: {exc}",
                    stacklevel=2,
                )


def completed_keys(
    bank: str, *, ledger_dir: pathlib.Path = LEDGER_DIR
) -> set[tuple[str, str, str, str, int]]:
    """Return completed resume keys: {(bank, dataset_version, task_id, config_hash, repeat)}.

    Errored trials are excluded — only status=='completed' contributes — and a void
    row removes the key it names from the set as of its position, so a voided trial is
    re-run on resume and its re-run, appended later, is done.
    """
    keys: set[tuple[str, str, str, str, int]] = set()
    for record in iter_records(bank, ledger_dir=ledger_dir):
        if isinstance(record, TrialRecord) and record.status == "completed":
            keys.add(
                (
                    record.bank,
                    record.dataset_version,
                    record.task_id,
                    record.config_hash,
                    record.repeat,
                )
            )
        elif isinstance(record, VoidRecord):
            keys.discard(
                (
                    record.bank,
                    record.dataset_version,
                    record.task_id,
                    record.config_hash,
                    record.repeat,
                )
            )
    return keys
