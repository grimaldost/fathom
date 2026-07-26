"""Bank self-test: every verifier must be RED on the pristine fixture and GREEN
on a scripted reference solution. Run after any fixture regeneration:

    uv run python tasks/serena-nav-v1/selftest.py
"""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent


def run_verify(task: str, ws: pathlib.Path) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, str(HERE / task / "verify.py"), str(ws)],
        capture_output=True,
        text=True,
        timeout=200,
    )
    return r.returncode, r.stdout.strip()


def solve_rename(ws: pathlib.Path) -> None:
    decoys = {"ledgerline/utils/money.py", "ledgerline/legacy/oldapi.py"}
    for p in ws.rglob("*.py"):
        rel = p.relative_to(ws).as_posix()
        txt = p.read_text(encoding="utf-8")
        if rel in decoys:
            if rel.endswith("oldapi.py"):
                txt = txt.replace(
                    "from ..core.compute import settle as _core",
                    "from ..core.compute import settle_entries as _core",
                )
                p.write_text(txt, encoding="utf-8")
            continue
        p.write_text(re.sub(r"\bsettle\b", "settle_entries", txt), encoding="utf-8")


def solve_retire(ws: pathlib.Path) -> None:
    targets = (
        list(ws.glob("ledgerline/analytics/*.py"))
        + list(ws.glob("ledgerline/validators/*.py"))
        + list(ws.glob("tests/*.py"))
    )
    for p in targets:
        txt = p.read_text(encoding="utf-8")
        txt = txt.replace(
            "from ledgerline.legacy import oldapi", "from ledgerline.core import compute"
        )
        txt = txt.replace("oldapi.legacy_total(", "compute.settle(")
        p.write_text(txt, encoding="utf-8")


def solve_thread(ws: pathlib.Path) -> None:
    (ws / "ledgerline/core/fx.py").write_text(
        '"""FX conversion."""\n'
        "from decimal import ROUND_HALF_UP, Decimal\n\n\n"
        'def convert(amount, rate, rounding="bankers"):\n'
        '    """Convert an amount at the given rate."""\n'
        "    raw = amount * rate\n"
        '    if rounding == "half-up":\n'
        '        return float(Decimal(str(raw)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))\n'
        "    return round(raw, 2)\n",
        encoding="utf-8",
    )
    edits = {
        "ledgerline/adapters/report.py": [
            (
                "def build_report(entries, rate):",
                'def build_report(entries, rate, rounding="bankers"):',
            ),
            ("convert(total, rate)", "convert(total, rate, rounding=rounding)"),
        ],
        "ledgerline/pipelines/daily.py": [
            ("def run_daily(entries, rate):", 'def run_daily(entries, rate, rounding="bankers"):'),
            ("convert(settle(entries), rate)", "convert(settle(entries), rate, rounding=rounding)"),
        ],
        "ledgerline/pipelines/monthly.py": [
            (
                "def run_monthly(batches, rate):",
                'def run_monthly(batches, rate, rounding="bankers"):',
            ),
            (
                "convert(sum(cc.settle(b) for b in batches), rate)",
                "convert(sum(cc.settle(b) for b in batches), rate, rounding=rounding)",
            ),
        ],
    }
    for rel, pairs in edits.items():
        p = ws / rel
        txt = p.read_text(encoding="utf-8")
        for old, new in pairs:
            assert old in txt, f"selftest solver: {old!r} not found in {rel}"
            txt = txt.replace(old, new)
        p.write_text(txt, encoding="utf-8")


SOLVERS = {
    "rename-settle": solve_rename,
    "retire-legacy": solve_retire,
    "thread-param": solve_thread,
}


def main() -> None:
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        for task, solver in SOLVERS.items():
            rc_red, out_red = run_verify(task, HERE / task / "fixtures")
            red_ok = rc_red != 0
            ws = pathlib.Path(tmp) / task
            shutil.copytree(HERE / task / "fixtures", ws)
            solver(ws)
            rc_green, out_green = run_verify(task, ws)
            green_ok = rc_green == 0
            ok = ok and red_ok and green_ok
            print(f"{task}: RED(pristine)  {'ok' if red_ok else 'FAIL'}  {out_red}")
            print(f"{task}: GREEN(solved)  {'ok' if green_ok else 'FAIL'}  {out_green}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
