"""Bank self-test for serena-nav-v2: every verifier RED on the pristine fixture and
GREEN on a scripted reference solution. Also asserts the fixture starts green under
pytest and reports the grep-vs-truth ratio that justifies the bank's design.

    uv run python tasks/serena-nav-v2/selftest.py
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
TRUTH = json.loads((HERE / "rename-reconcile" / "truth.json").read_text(encoding="utf-8"))
WORD = re.compile(r"\breconcile\b")


def run_verify(task: str, ws: pathlib.Path) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, str(HERE / task / "verify.py"), str(ws)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    return r.returncode, (r.stdout.strip() or r.stderr.strip()[:200])


def solve_rename(ws: pathlib.Path) -> None:
    eng = ws / TRUTH["defining_file"]
    eng.write_text(WORD.sub("reconcile_entries", eng.read_text(encoding="utf-8")), encoding="utf-8")
    for rel in TRUTH["genuine_reference_files"]:
        p = ws / rel
        p.write_text(WORD.sub("reconcile_entries", p.read_text(encoding="utf-8")), encoding="utf-8")


def solve_impact(ws: pathlib.Path) -> None:
    (ws / "impact.json").write_text(
        json.dumps(sorted(TRUTH["call_closure_modules"]), indent=1), encoding="utf-8"
    )


def solve_fee(ws: pathlib.Path) -> None:
    p = ws / TRUTH["fee_target_file"]
    txt = p.read_text(encoding="utf-8").replace(
        "round(amount * rate, 1)", "round(amount * rate, 2)"
    )
    p.write_text(txt, encoding="utf-8")


SOLVERS = {
    "rename-reconcile": solve_rename,
    "impact-report": solve_impact,
    "disambiguate-fee": solve_fee,
}


def main() -> None:
    fixtures = HERE / "rename-reconcile" / "fixtures"
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=fixtures,
        capture_output=True,
        text=True,
        timeout=300,
    )
    green_start = r.returncode == 0
    print(
        f"fixture starts green: {'ok' if green_start else 'FAIL'}  ({r.stdout.strip().splitlines()[-1:]})"
    )

    hits = [p for p in fixtures.rglob("*.py") if WORD.search(p.read_text(encoding="utf-8"))]
    genuine = len(TRUTH["genuine_reference_files"]) + 1
    print(
        f"discrimination: grep '\\breconcile\\b' hits {len(hits)} files; "
        f"only {genuine} are genuine ({len(hits) - genuine} decoy files to reject)"
    )

    ok = green_start
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
            print(f"{task}: RED(pristine) {'ok' if red_ok else 'FAIL'}  {out_red}")
            print(f"{task}: GREEN(solved) {'ok' if green_ok else 'FAIL'}  {out_green}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
