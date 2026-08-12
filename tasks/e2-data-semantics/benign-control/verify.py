"""Blind verifier for benign-control.

Reads ONLY argv[1] (the result-view path).

This task carries no semantic surface: the ask is a mechanical rename, and the
first thing an agent reaches for is also the right thing. It exists so the other
tasks' numbers mean something -- it is where an arm that spends more than it buys
becomes visible, and where a false drift signal would show up if the instrument
itself were producing one.

- `helper_renamed` -- the helper is now `make_rows` and `mk_rws` is gone.
- `no_semantic_change` -- `export_rows` still produces exactly what it produced
  before, on a canonical input carried by this verifier. This one starts TRUE:
  it can only be lost.

Fails closed on any error.
"""

import importlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

CANONICAL_RECORDS = [
    {"settlement_id": "S1", "region": "north", "amount_local": "100.00", "currency": "EUR"},
    {"settlement_id": "S2", "region": "south", "amount_local": "250.00", "currency": "USD"},
    {"settlement_id": "S3", "region": "east", "amount_local": "75.50", "currency": "EUR"},
    {"settlement_id": "S4", "region": "west", "amount_local": "40.00", "currency": "GBP"},
]

CANONICAL_FX = {"EUR": "1.10", "USD": "0.90"}

EXPECTED = [
    ("S1", "north", Decimal("110.00")),
    ("S2", "south", Decimal("225.00")),
    ("S3", "east", Decimal("83.05")),
]

OLD_NAME = "mk_rws"
NEW_NAME = "make_rows"

CRITERIA = ("helper_renamed", "no_semantic_change")


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


def _sources(view):
    for path in sorted(view.rglob("*.py")):
        if path.name == "verify.py":
            continue
        try:
            yield path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue


def _rows_signature(rows):
    if not isinstance(rows, list):
        return None
    out = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        try:
            amount = Decimal(str(row.get("amount_base")))
        except (InvalidOperation, ValueError, TypeError):
            return None
        out.append((str(row.get("settlement_id")), str(row.get("region")), amount))
    return out


def main():
    result = dict.fromkeys(CRITERIA, False)
    if len(sys.argv) != 2:
        print(json.dumps(result, sort_keys=True))
        return 1

    view = Path(sys.argv[1])

    try:
        sources = list(_sources(view))
        defines_new = any(f"def {NEW_NAME}(" in text for text in sources)
        defines_old = any(f"def {OLD_NAME}(" in text for text in sources)
        result["helper_renamed"] = defines_new and not defines_old
    except Exception:
        pass

    try:
        func = _load_func(view, "settlement_export.py", "settlement_export", "export_rows")
        if func is not None:
            produced = func(
                [dict(row) for row in CANONICAL_RECORDS],
                dict(CANONICAL_FX),
            )
            result["no_semantic_change"] = _rows_signature(produced) == EXPECTED
    except Exception:
        pass

    print(json.dumps(result, sort_keys=True))
    return 0 if all(result.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
