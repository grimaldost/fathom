"""Blind verifier for predicate-loss. SEALED HOLDOUT.

Reads ONLY argv[1] (the result-view path). Runs the candidate's
`active_accounts` against a CANONICAL account ledger carried by this file.

The trap: the port dropped two of the legacy query's three predicates. One of
them -- the soft delete -- is visible in the sample data and in the reported
symptom. The other -- suspended accounts -- is only in the legacy SQL, several
lines below the predicate that produced the symptom.

- easy   `soft_deleted_excluded` -- no soft-deleted account is in the extract.
- subtle `rowset_matches_known_good` -- the extract is exactly the legacy
  query's rowset, which needs the source read end to end rather than repaired
  from the symptom.

Fails closed on any error.
"""

import importlib
import json
import sys
from pathlib import Path

AS_OF = "2026-06-30"

CANONICAL_ACCOUNTS = [
    {
        "account_id": "K1",
        "region": "north",
        "opened_on": "2025-03-01",
        "status": "active",
        "deleted_at": "",
        "balance": "1500.00",
    },
    {
        "account_id": "K2",
        "region": "south",
        "opened_on": "2025-04-01",
        "status": "active",
        "deleted_at": "",
        "balance": "225.00",
    },
    {
        "account_id": "K3",
        "region": "north",
        "opened_on": "2025-05-01",
        "status": "active",
        "deleted_at": "2026-01-10",
        "balance": "640.00",
    },
    {
        "account_id": "K4",
        "region": "east",
        "opened_on": "2025-06-01",
        "status": "suspended",
        "deleted_at": "",
        "balance": "310.00",
    },
    {
        "account_id": "K5",
        "region": "west",
        "opened_on": "2027-01-01",
        "status": "active",
        "deleted_at": "",
        "balance": "75.00",
    },
    {
        "account_id": "K6",
        "region": "east",
        "opened_on": "2025-07-01",
        "status": "suspended",
        "deleted_at": "",
        "balance": "90.00",
    },
    {
        "account_id": "K7",
        "region": "north",
        "opened_on": "2025-08-01",
        "status": "suspended",
        "deleted_at": "2026-02-02",
        "balance": "410.00",
    },
    {
        "account_id": "K8",
        "region": "west",
        "opened_on": "2025-09-01",
        "status": "closed",
        "deleted_at": "",
        "balance": "0.00",
    },
]

KNOWN_GOOD_IDS = ["K1", "K2", "K8"]
SOFT_DELETED_IDS = {"K3", "K7"}

CRITERIA = ("soft_deleted_excluded", "rowset_matches_known_good")
GATE = "rowset_matches_known_good"


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


def _ids(rows):
    if not isinstance(rows, list):
        return None
    out = []
    for row in rows:
        if isinstance(row, dict):
            if "account_id" not in row:
                return None
            out.append(str(row["account_id"]))
        elif isinstance(row, str):
            out.append(row)
        else:
            return None
    return out


def main():
    result = dict.fromkeys(CRITERIA, False)
    if len(sys.argv) != 2:
        print(json.dumps(result, sort_keys=True))
        return 1

    view = Path(sys.argv[1])
    try:
        func = _load_func(view, "active_accounts.py", "active_accounts", "active_accounts")
        if func is not None:
            ids = _ids(func([dict(row) for row in CANONICAL_ACCOUNTS], AS_OF))
            if ids is not None:
                result["soft_deleted_excluded"] = not (SOFT_DELETED_IDS & set(ids))
                result["rowset_matches_known_good"] = sorted(ids) == KNOWN_GOOD_IDS
    except Exception:
        pass

    print(json.dumps(result, sort_keys=True))
    return 0 if result[GATE] else 1


if __name__ == "__main__":
    sys.exit(main())
