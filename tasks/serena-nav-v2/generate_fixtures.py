"""Deterministic fixture generator for serena-nav-v2 — the LARGE-SCALE navigation bank.

v1 (34 files) saturated: 11 of 12 criteria scored 100% for both arms, because tasks
that are hard for *grep* are not hard for a competent model *with* grep at small
scale. v2 changes the two variables that actually bind a navigation tool:

  SCALE      ~420 modules across 14 domains, far past a comfortable read-everything
             budget. The token `reconcile` appears in ~150 DECOY files (same-named
             methods, near-miss function names, docstrings, string literals) and in
             only 15 genuine reference sites, so a textual sweep floods while a
             semantic query returns exactly the real set.
  PRECISION  Decoy files are checked by sha256 for byte-identity, so a
             grep-and-replace that catches a decoy fails hard. There is no partial
             credit for "mostly right".

Ground truth (genuine sites, the transitive call closure, decoy hashes) is written
to each task's `truth.json`, which lives NEXT TO verify.py in the task dir and is
therefore NEVER staged into the agent's workspace (fathom stages only `fixtures/`).
The agent cannot read the answer key.

Run once from the bank dir:  uv run python tasks/serena-nav-v2/generate_fixtures.py
Bump bank dataset_version after ANY regeneration that changes content.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = "reconciler"
TASKS = ["rename-reconcile", "impact-report", "disambiguate-fee"]

DOMAINS = [
    "accounts",
    "billing",
    "clearing",
    "custody",
    "fees",
    "fx",
    "ledgers",
    "limits",
    "payments",
    "positions",
    "pricing",
    "reporting",
    "settlements",
    "treasury",
]
MODNAMES = [
    "api",
    "batch",
    "cache",
    "cleanup",
    "client",
    "config",
    "dispatch",
    "export",
    "filters",
    "handlers",
    "hooks",
    "importer",
    "index",
    "jobs",
    "loader",
    "mapper",
    "metrics",
    "models",
    "normalize",
    "parser",
    "policies",
    "queue",
    "reader",
    "registry",
    "rules",
    "schema",
    "service",
    "state",
]

# --- role assignment (deterministic) --------------------------------------------
# 15 direct callers of reconcile, 5 import shapes x 3.
L1 = [(DOMAINS[i % 14], MODNAMES[i]) for i in range(15)]
# 12 second-level callers (each calls exactly one L1 module's run()).
L2 = [(DOMAINS[(i + 3) % 14], MODNAMES[15 + (i % 13)]) for i in range(12)]
# 6 third-level callers (each calls exactly one L2 module's run()).
L3 = [(DOMAINS[(i + 7) % 14], MODNAMES[i + 20]) for i in range(6)]

_participants = set(L1) | set(L2) | set(L3)
_all_slots = [(d, m) for d in DOMAINS for m in MODNAMES]
_free = [s for s in _all_slots if s not in _participants]
DECOYS = _free[:150]
FILLERS = _free[150:]

DECOY_KINDS = ["method", "nearmiss", "docstring", "stringlit", "comment"]


def dotted(domain: str, mod: str) -> str:
    return f"{PKG}.{domain}.{mod}"


def build() -> tuple[dict[str, str], dict]:
    F: dict[str, str] = {}
    F["conftest.py"] = ""

    F[f"{PKG}/__init__.py"] = (
        f'"""{PKG} — settlement reconciliation toolkit (fixture)."""\n'
        "from .core.engine import reconcile\n\n"
        '__all__ = ["reconcile"]\n'
    )
    F[f"{PKG}/core/__init__.py"] = "from .engine import reconcile\n"
    F[f"{PKG}/core/engine.py"] = (
        '"""Core reconciliation engine."""\n\n\n'
        "def reconcile(entries):\n"
        '    """Fold entry amounts into a reconciled total."""\n'
        "    total = 0.0\n"
        "    for e in entries:\n"
        '        total += float(e["amount"])\n'
        "    return round(total, 2)\n"
    )
    F[f"{PKG}/utils/__init__.py"] = ""
    F[f"{PKG}/utils/textfmt.py"] = (
        '"""Formatting leaf helper."""\n\n\ndef fmt(x):\n    return f"{x:,.2f}"\n'
    )

    for d in DOMAINS:
        F[f"{PKG}/{d}/__init__.py"] = ""

    # --- L1: the 15 genuine direct references, five import shapes ---------------
    shapes = [
        ("from {PKG}.core.engine import reconcile", "reconcile(entries)"),
        ("from {PKG}.core.engine import reconcile as _rc", "_rc(entries)"),
        ("from {PKG}.core import engine", "engine.reconcile(entries)"),
        ("from {PKG} import reconcile", "reconcile(entries)"),
        ("import {PKG}.core.engine as eng", "eng.reconcile(entries)"),
    ]
    for i, (d, m) in enumerate(L1):
        imp, call = shapes[i % 5]
        F[f"{PKG}/{d}/{m}.py"] = (
            f'"""{d}.{m} — reconciliation consumer (shape {i % 5})."""\n'
            + imp.format(PKG=PKG)
            + "\n\n\ndef run(entries):\n"
            f"    return {call}\n"
        )

    # --- L2 / L3: the transitive closure ---------------------------------------
    for i, (d, m) in enumerate(L2):
        up_d, up_m = L1[i % len(L1)]
        F[f"{PKG}/{d}/{m}.py"] = (
            f'"""{d}.{m} — second-level consumer."""\n'
            f"from {dotted(up_d, up_m)} import run as _up\n\n\n"
            "def run(entries):\n"
            "    return _up(entries)\n"
        )
    for i, (d, m) in enumerate(L3):
        up_d, up_m = L2[i % len(L2)]
        F[f"{PKG}/{d}/{m}.py"] = (
            f'"""{d}.{m} — third-level consumer."""\n'
            f"from {dotted(up_d, up_m)} import run as _up\n\n\n"
            "def run(entries):\n"
            "    return _up(entries)\n"
        )

    # --- decoys: the token appears, the meaning does not ------------------------
    for i, (d, m) in enumerate(DECOYS):
        kind = DECOY_KINDS[i % len(DECOY_KINDS)]
        if kind == "method":
            body = (
                f'"""{d}.{m} — unrelated component."""\n\n\n'
                f"class {m.capitalize()}Job:\n"
                "    def __init__(self, rows):\n"
                "        self.rows = rows\n\n"
                "    def reconcile(self):\n"
                '        """Unrelated same-named method — must not be renamed."""\n'
                "        return len(self.rows)\n"
            )
        elif kind == "nearmiss":
            body = (
                f'"""{d}.{m} — batch helpers."""\n\n\n'
                "def reconcile_batch(rows):\n"
                "    return sum(rows)\n\n\n"
                "def pre_reconcile(rows):\n"
                "    return list(rows)\n"
            )
        elif kind == "docstring":
            body = (
                f'"""{d}.{m}.\n\n'
                "    Notes: callers must reconcile totals before export; this module\n"
                "    does not reconcile anything itself.\n"
                '    """\n\n\n'
                "def summarize(rows):\n"
                "    return len(rows)\n"
            )
        elif kind == "stringlit":
            body = (
                f'"""{d}.{m} — status labels."""\n\n'
                'STATUS = "reconcile-pending"\n'
                'LABELS = {"reconcile": "Reconcile now", "done": "Reconciled"}\n\n\n'
                "def label(key):\n"
                '    return LABELS.get(key, "")\n'
            )
        else:  # comment
            body = (
                f'"""{d}.{m} — queue plumbing."""\n\n\n'
                "def enqueue(rows):\n"
                "    # TODO: reconcile these against the ledger before enqueueing\n"
                "    reconciled = list(rows)  # reconcile step happens upstream\n"
                "    return reconciled\n"
            )
        F[f"{PKG}/{d}/{m}.py"] = body

    # --- fillers: pure scale ----------------------------------------------------
    for d, m in FILLERS:
        F[f"{PKG}/{d}/{m}.py"] = (
            f'"""{d}.{m}."""\n'
            f"from {PKG}.utils.textfmt import fmt\n\n\n"
            "def render(values):\n"
            "    return [fmt(v) for v in values]\n"
        )

    # --- the four same-named fee implementations (disambiguate-fee) -------------
    # Only fees.standard.apply_fee is reachable from pipelines.daily; it has the
    # 1-decimal bug. The other three are decoys with deliberately different bodies.
    F[f"{PKG}/fees/standard.py"] = (
        '"""Standard fee schedule (the one the daily pipeline uses)."""\n\n\n'
        "def apply_fee(amount, rate):\n"
        '    """Fee on an amount. NOTE: rounds to 1 decimal."""\n'
        "    return round(amount * rate, 1)\n"
    )
    F[f"{PKG}/fees/legacy_a.py"] = (
        '"""Legacy fee schedule A — frozen."""\n\n\n'
        "def apply_fee(amount, rate):\n"
        "    return round(amount * rate * 1.0, 1)\n"
    )
    F[f"{PKG}/fees/legacy_b.py"] = (
        '"""Legacy fee schedule B — frozen."""\n\n\n'
        "def apply_fee(amount, rate):\n"
        "    return round((amount * rate) + 0.0, 1)\n"
    )
    F[f"{PKG}/fees/experimental.py"] = (
        '"""Experimental fee schedule — not wired up."""\n\n\n'
        "def apply_fee(amount, rate):\n"
        "    return round(amount * rate / 1.0, 1)\n"
    )
    F[f"{PKG}/billing/runner.py"] = (
        '"""Billing runner."""\n'
        f"from {PKG}.fees.standard import apply_fee\n\n\n"
        "def charge(amount, rate):\n"
        "    return apply_fee(amount, rate)\n"
    )
    F[f"{PKG}/pipelines/__init__.py"] = ""
    F[f"{PKG}/pipelines/daily.py"] = (
        '"""Daily pipeline — the entry point that reaches the live fee schedule."""\n'
        f"from {PKG}.billing.runner import charge\n"
        f"from {PKG}.core.engine import reconcile\n\n\n"
        "def run_daily(entries, rate):\n"
        "    total = reconcile(entries)\n"
        "    return charge(total, rate)\n"
    )

    F["tests/test_engine.py"] = (
        f"from {PKG}.core.engine import reconcile\n\n\n"
        "def test_reconcile():\n"
        '    assert reconcile([{"amount": 1.5}, {"amount": 2.25}]) == 3.75\n'
    )
    F["tests/test_consumers.py"] = (
        f"from {dotted(*L1[0])} import run as run_l1\n"
        f"from {dotted(*L2[0])} import run as run_l2\n"
        f"from {dotted(*L3[0])} import run as run_l3\n\n\n"
        "def test_chain():\n"
        '    entries = [{"amount": 2.0}]\n'
        "    assert run_l1(entries) == 2.0\n"
        "    assert run_l2(entries) == 2.0\n"
        "    assert run_l3(entries) == 2.0\n"
    )
    F["tests/test_pipeline.py"] = (
        f"from {PKG}.pipelines.daily import run_daily\n\n\n"
        "def test_daily_runs():\n"
        '    assert run_daily([{"amount": 10.0}], 0.1) >= 0\n'
    )

    # --- ground truth -----------------------------------------------------------
    genuine = [f"{PKG}/{d}/{m}.py" for d, m in L1] + [
        f"{PKG}/__init__.py",
        f"{PKG}/core/__init__.py",
        f"{PKG}/pipelines/daily.py",
        # the suite imports the symbol by name, so it is a genuine reference site;
        # omitting it made the reference solution fail pytest (caught by selftest).
        "tests/test_engine.py",
    ]
    closure = sorted(
        [dotted(d, m) for d, m in L1]
        + [dotted(d, m) for d, m in L2]
        + [dotted(d, m) for d, m in L3]
        + [f"{PKG}.pipelines.daily"]
    )
    decoy_files = [f"{PKG}/{d}/{m}.py" for d, m in DECOYS] + [
        f"{PKG}/fees/legacy_a.py",
        f"{PKG}/fees/legacy_b.py",
        f"{PKG}/fees/experimental.py",
    ]
    truth = {
        "genuine_reference_files": sorted(genuine),
        "defining_file": f"{PKG}/core/engine.py",
        "call_closure_modules": closure,
        "decoy_hashes": {
            p: hashlib.sha256(F[p].encode("utf-8")).hexdigest() for p in sorted(decoy_files)
        },
        "fee_target_file": f"{PKG}/fees/standard.py",
        "fee_decoy_files": [
            f"{PKG}/fees/legacy_a.py",
            f"{PKG}/fees/legacy_b.py",
            f"{PKG}/fees/experimental.py",
        ],
        "counts": {
            "total_files": len(F),
            "genuine": len(genuine),
            "decoys": len(decoy_files),
            "closure": len(closure),
        },
    }
    return F, truth


def main() -> None:
    F, truth = build()
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
        (HERE / task / "truth.json").write_text(json.dumps(truth, indent=1), encoding="utf-8")
    shutil.rmtree(staging)
    c = truth["counts"]
    print(
        f"wrote {c['total_files']} files x {len(TASKS)} tasks | "
        f"genuine={c['genuine']} decoys={c['decoys']} closure={c['closure']}"
    )


if __name__ == "__main__":
    main()
