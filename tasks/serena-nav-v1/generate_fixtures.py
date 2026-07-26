"""Deterministic fixture generator for the serena-nav-v1 bank.

Emits one Python package (`ledgerline`, ~25 files) designed to discriminate
semantic (LSP) navigation from textual grep:

- `settle` is defined in core/compute.py and referenced through five distinct
  import shapes (direct, aliased, module-attr, package re-export, top-level);
  two DECOYS carry the same name and must survive a rename untouched
  (`Money.settle` method, `legacy/oldapi.py`'s public wrapper).
- `legacy/oldapi.py` is imported by exactly five internal modules/tests via
  `legacy_total` (the retire-legacy task's targets).
- `fx.convert` is called through three public paths (the thread-param task).

The word "settle" appears ONLY at genuine rename sites and inside the two decoy
files, so verifiers can use `\\bsettle\\b` as a stale-reference oracle
(docstrings deliberately say "settlement", which the regex does not match).

Run once from the bank dir: `python generate_fixtures.py`. Overwrites the
fixtures/ tree of all three tasks with identical copies. Bump bank
dataset_version after ANY regeneration that changes content.
"""

from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = ["rename-settle", "retire-legacy", "thread-param"]

F: dict[str, str] = {}

F["conftest.py"] = ""

F["ledgerline/__init__.py"] = '''"""ledgerline - tiny settlement toolkit (fixture)."""
from .core.compute import accrue, settle
from .core.fx import convert

__all__ = ["settle", "accrue", "convert"]
'''

F["ledgerline/core/__init__.py"] = """from .compute import accrue, settle
from .fx import convert
"""

F["ledgerline/core/compute.py"] = '''"""Core settlement arithmetic."""


def settle(entries):
    """Sum entry amounts into a settlement total."""
    total = 0.0
    for e in entries:
        total += float(e["amount"])
    return round(total, 2)


def settle_batch(batches):
    """Settlement per batch."""
    return [settle(b) for b in batches]


def accrue(principal, rate, days):
    """Simple accrual on an ACT/360 basis."""
    return round(principal * rate * days / 360.0, 2)
'''

F["ledgerline/core/calendar.py"] = '''"""Business-date helpers."""
from datetime import timedelta


def roll_date(d, days):
    return d + timedelta(days=days)


def is_weekend(d):
    return d.weekday() >= 5
'''

F["ledgerline/core/fx.py"] = '''"""FX conversion."""


def convert(amount, rate):
    """Convert an amount at the given rate."""
    return round(amount * rate, 2)
'''

F["ledgerline/adapters/__init__.py"] = ""

F["ledgerline/adapters/csv_io.py"] = '''"""CSV ingestion (aliased import shape)."""
from ..core.compute import settle as _settle


def load_and_settle(rows):
    return _settle([{"amount": float(r)} for r in rows])
'''

F["ledgerline/adapters/json_io.py"] = '''"""JSON ingestion (module-attr import shape)."""
from ..core import compute


def total_from_json(data):
    return compute.settle(data["entries"])
'''

F["ledgerline/adapters/report.py"] = '''"""Reporting (top-level re-export import shape)."""
from ledgerline import settle

from ..core.fx import convert


def build_report(entries, rate):
    total = settle(entries)
    return {"total": total, "converted": convert(total, rate)}
'''

F["ledgerline/pipelines/__init__.py"] = ""

F["ledgerline/pipelines/daily.py"] = '''"""Daily pipeline (direct import shape)."""
from ledgerline.core.compute import settle
from ledgerline.core.fx import convert


def run_daily(entries, rate):
    return convert(settle(entries), rate)
'''

F["ledgerline/pipelines/monthly.py"] = '''"""Monthly pipeline (module-alias import shape)."""
import ledgerline.core.compute as cc
from ledgerline.core.fx import convert


def run_monthly(batches, rate):
    return convert(sum(cc.settle(b) for b in batches), rate)
'''

F["ledgerline/pipelines/audit.py"] = '''"""Accrual audit pipeline."""
from ledgerline.core.compute import accrue


def audit_accruals(positions):
    return [accrue(p["principal"], p["rate"], p["days"]) for p in positions]
'''

F["ledgerline/utils/__init__.py"] = ""

F[
    "ledgerline/utils/money.py"
] = '''"""Money value object. DECOY: the method below shares a name with
the core settlement function and is unrelated to it."""


class Money:
    def __init__(self, amount):
        self.amount = float(amount)

    def settle(self):
        """Round this amount for settlement display (unrelated decoy)."""
        return round(self.amount, 2)

    def as_cents(self):
        return int(round(self.amount * 100))
'''

F["ledgerline/utils/textfmt.py"] = '''"""Text formatting helpers."""


def fmt_amount(x):
    return f"{x:,.2f}"
'''

F["ledgerline/legacy/__init__.py"] = ""

F[
    "ledgerline/legacy/oldapi.py"
] = '''"""Frozen external compatibility surface. DECOY: the public wrapper
keeps its historical name forever; only its internals may change."""
from ..core.compute import settle as _core


def settle(entries):
    """Historical name, kept for external callers."""
    return _core(entries)


def legacy_total(entries):
    """Historical helper used (for now) by internal modules."""
    return _core(entries)
'''

_ANALYTICS = {
    "trend": True,
    "varsum": False,
    "flows": True,
    "ratios": False,
    "windows": False,
}
for name, uses_legacy in _ANALYTICS.items():
    if uses_legacy:
        F[
            f"ledgerline/analytics/{name}.py"
        ] = f'''"""Analytics: {name} (routes through the legacy surface)."""
from ledgerline.legacy import oldapi


def {name}_metric(entries):
    return oldapi.legacy_total(entries) / max(len(entries), 1)
'''
    else:
        F[f"ledgerline/analytics/{name}.py"] = f'''"""Analytics: {name}."""
from ledgerline.utils.textfmt import fmt_amount


def {name}_metric(values):
    return fmt_amount(sum(values))
'''
F["ledgerline/analytics/__init__.py"] = ""

_VALIDATORS = {
    "schema_check": False,
    "rules": True,
    "limits_check": False,
    "nulls": True,
    "ranges": False,
}
for name, uses_legacy in _VALIDATORS.items():
    if uses_legacy:
        F[
            f"ledgerline/validators/{name}.py"
        ] = f'''"""Validator: {name} (routes through the legacy surface)."""
from ledgerline.legacy import oldapi


def check_{name}(entries):
    return oldapi.legacy_total(entries) >= 0
'''
    else:
        F[f"ledgerline/validators/{name}.py"] = f'''"""Validator: {name}."""


def check_{name}(entries):
    return all("amount" in e for e in entries)
'''
F["ledgerline/validators/__init__.py"] = ""

F["tests/test_compute.py"] = """from ledgerline.core.compute import accrue, settle


def test_totals():
    assert settle([{"amount": 1.5}, {"amount": 2.25}]) == 3.75


def test_accrual():
    assert accrue(1000.0, 0.036, 30) == 3.0
"""

F["tests/test_adapters.py"] = """from ledgerline.adapters.csv_io import load_and_settle
from ledgerline.adapters.report import build_report


def test_csv():
    assert load_and_settle(["1.10", "2.20"]) == 3.30


def test_report():
    r = build_report([{"amount": 10.0}], 1.1)
    assert r == {"total": 10.0, "converted": 11.0}
"""

F["tests/test_pipelines.py"] = """from ledgerline.legacy import oldapi
from ledgerline.pipelines.daily import run_daily
from ledgerline.pipelines.monthly import run_monthly


def test_daily():
    assert run_daily([{"amount": 5.0}], 2.0) == 10.0


def test_monthly():
    assert run_monthly([[{"amount": 1.0}], [{"amount": 2.0}]], 1.0) == 3.0


def test_legacy_surface():
    assert oldapi.legacy_total([{"amount": 4.0}]) == 4.0
"""


def main() -> None:
    staging = HERE / "_staging"
    if staging.exists():
        shutil.rmtree(staging)
    for rel, content in F.items():
        p = staging / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    for task in TASKS:
        dest = HERE / task / "fixtures"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(staging, dest)
    shutil.rmtree(staging)
    print(f"wrote {len(F)} files into {len(TASKS)} task fixture trees")


if __name__ == "__main__":
    main()
