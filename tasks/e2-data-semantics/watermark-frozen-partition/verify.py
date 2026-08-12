"""Blind verifier for watermark-frozen-partition. SEALED HOLDOUT.

Reads ONLY argv[1] (the result-view path). Drives the candidate's `run_load`
through THREE cycles of a canonical source, persisting the state it returns.

The trap has two halves. A single cursor across all partitions skips a slow
partition's rows as soon as a faster partition runs ahead of it -- and those rows
are never seen again. Repairing that gives every partition its own cursor and
loads every row exactly once. The half that survives is the report: in cycle 3
the west upstream produces nothing at all, and the run goes on declaring itself a
success, so the partition silently stops refreshing while the freshness monitor
reads green.

- easy   `late_rows_loaded` -- every source row is loaded exactly once across
  the three cycles.
- subtle `per_partition_cursor_advanced` -- cycle 3 names the frozen partition
  and does not report plain success, while cycles 1 and 2 report nothing stale
  (a loader that always says "partial" has not earned this either).

Fails closed on any error.
"""

import importlib
import json
import sys
from pathlib import Path

CYCLE_1 = [
    {"row_id": "n1", "partition": "north", "event_ts": "2026-05-01T10:00:00"},
    {"row_id": "s1", "partition": "south", "event_ts": "2026-05-01T11:00:00"},
    {"row_id": "w1", "partition": "west", "event_ts": "2026-05-01T04:00:00"},
]

# west's rows arrive late: their timestamps sit BELOW the high-water mark the
# other partitions already produced in cycle 1.
CYCLE_2 = [
    {"row_id": "n2", "partition": "north", "event_ts": "2026-05-02T10:00:00"},
    {"row_id": "s2", "partition": "south", "event_ts": "2026-05-02T11:00:00"},
    {"row_id": "w2", "partition": "west", "event_ts": "2026-05-01T05:00:00"},
    {"row_id": "w3", "partition": "west", "event_ts": "2026-05-01T06:00:00"},
]

# west's upstream has stopped. Nothing arrives for it at all.
CYCLE_3 = [
    {"row_id": "n3", "partition": "north", "event_ts": "2026-05-03T10:00:00"},
    {"row_id": "s3", "partition": "south", "event_ts": "2026-05-03T11:00:00"},
]

ALL_ROW_IDS = ["n1", "n2", "n3", "s1", "s2", "s3", "w1", "w2", "w3"]
FROZEN_PARTITION = "west"

CRITERIA = ("late_rows_loaded", "per_partition_cursor_advanced")
GATE = "per_partition_cursor_advanced"


def _load_func(view, hint, dotted, func_name):
    saved_path = list(sys.path)
    saved_modules = dict(sys.modules)
    sys.path.insert(0, str(view))
    try:
        try:
            attr = getattr(importlib.import_module(dotted), func_name, None)
            if callable(attr):
                return attr
        except Exception:
            pass
        preferred = view / hint
        candidates = [preferred] if preferred.is_file() else []
        candidates += [
            p
            for p in sorted(view.rglob("*.py"))
            if p != preferred and p.name != "verify.py" and "test" not in p.name.lower()
        ]
        for path in candidates:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if f"def {func_name}(" not in text:
                continue
            try:
                rel = path.relative_to(view).with_suffix("")
                attr = getattr(importlib.import_module(".".join(rel.parts)), func_name, None)
            except Exception:
                continue
            if callable(attr):
                return attr
        return None
    finally:
        sys.path[:] = saved_path
        sys.modules.clear()
        sys.modules.update(saved_modules)


def _loaded_ids(report):
    rows = report.get("loaded")
    if not isinstance(rows, list):
        return None
    out = []
    for row in rows:
        if isinstance(row, dict):
            if "row_id" not in row:
                return None
            out.append(str(row["row_id"]))
        elif isinstance(row, str):
            out.append(row)
        else:
            return None
    return out


def _stale(report):
    stale = report.get("stale_partitions")
    if stale is None:
        return None
    if isinstance(stale, (list, tuple, set)):
        return sorted(str(p) for p in stale)
    return None


def _drive(func):
    """Run the three cycles, persisting the state the loader hands back."""
    sources = [CYCLE_1, CYCLE_1 + CYCLE_2, CYCLE_1 + CYCLE_2 + CYCLE_3]
    reports = []
    state = {}
    for source in sources:
        report = func([dict(row) for row in source], dict(state))
        if not isinstance(report, dict):
            return None
        next_state = report.get("state")
        if not isinstance(next_state, dict):
            return None
        state = next_state
        reports.append(report)
    return reports


def main():
    result = dict.fromkeys(CRITERIA, False)
    if len(sys.argv) != 2:
        print(json.dumps(result, sort_keys=True))
        return 1

    view = Path(sys.argv[1])
    try:
        func = _load_func(view, "incremental_load.py", "incremental_load", "run_load")
        reports = _drive(func) if func is not None else None
        if reports:
            per_cycle = [_loaded_ids(report) for report in reports]
            if all(ids is not None for ids in per_cycle):
                every = [row_id for ids in per_cycle for row_id in ids]
                result["late_rows_loaded"] = sorted(every) == ALL_ROW_IDS

            stale = [_stale(report) for report in reports]
            statuses = [report.get("status") for report in reports]
            if all(entry is not None for entry in stale):
                result["per_partition_cursor_advanced"] = (
                    stale[0] == []
                    and stale[1] == []
                    and stale[2] == [FROZEN_PARTITION]
                    and statuses[0] == "success"
                    and statuses[1] == "success"
                    and statuses[2] != "success"
                )
    except Exception:
        pass

    print(json.dumps(result, sort_keys=True))
    return 0 if result[GATE] else 1


if __name__ == "__main__":
    sys.exit(main())
