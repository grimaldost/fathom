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


_KIND_MAP: dict[str, type] = {
    "trial": TrialRecord,
    "run": RunRecord,
    "grading": GradingRecord,
}


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
    with open(path, "a", encoding="utf-8") as f:
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

    Errored trials are excluded — only status=='completed' contributes.
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
    return keys
