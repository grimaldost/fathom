"""Acceptance verifier for modernize-timeflow (harness-side, scenario-blind, ADR-0003).

Reads ONLY the result-view path in argv[1]. The five compliance criteria are ported
verbatim from the python-engineering skill's own scripts/doctor.py audit (so the
treatment is graded against the skill's definition of its standard, not ours).
`behavior_preserved` imports the candidate timeflow.parser whether it ended up flat
or under src/ and checks the public functions still behave. Emits {criterion: bool}
JSON; exits 0 iff behavior_preserved (correctness gate). Compliance rides as criteria.
"""

import importlib
import json
import sys
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _compliance(d: Path) -> dict:
    pyproject = _read(d / "pyproject.toml")
    out: dict[str, bool] = {}
    src = d / "src"
    out["src-layout"] = src.is_dir() and any(c.is_dir() for c in src.iterdir())
    out["uv"] = (d / "uv.lock").is_file() or "uv_build" in pyproject or "[tool.uv]" in pyproject
    out["ruff-single-quote"] = (
        'quote-style = "single"' in pyproject or "quote-style = 'single'" in pyproject
    )
    out["dependency-groups"] = "[dependency-groups]" in pyproject
    ci_files = list(d.glob(".github/workflows/*.yml")) + list(d.glob(".github/workflows/*.yaml"))
    ci = " ".join(_read(p) for p in ci_files)
    out["pip-audit"] = "pip-audit" in pyproject or "pip-audit" in ci
    return out


def _find_parser(view: Path) -> Path | None:
    for base in (view / "timeflow", view / "src" / "timeflow"):
        cand = base / "parser.py"
        if cand.is_file():
            return cand
    for cand in view.rglob("timeflow/parser.py"):
        return cand
    return None


def _behavior_preserved(view: Path) -> bool:
    mod_path = _find_parser(view)
    if mod_path is None:
        return False
    # Import `timeflow.parser` as a PACKAGE (root = the dir that contains timeflow/),
    # never a bare file: a correctly modernized solution may use a relative import
    # (`from ._x import ...`), which a file-location load cannot resolve. Grading such
    # a valid refactor as a behavior failure would bias against the very treatment
    # this bank exists to reward. Fail closed on any error; restore import state after.
    root = str(mod_path.parent.parent)
    saved = {k: sys.modules[k] for k in ("timeflow", "timeflow.parser") if k in sys.modules}
    for k in ("timeflow", "timeflow.parser"):
        sys.modules.pop(k, None)
    sys.path.insert(0, root)
    try:
        mod = importlib.import_module("timeflow.parser")
        return (
            mod.normalize("2026-06-13T12:00:00Z") == "2026-06-13T12:00:00Z"
            and mod.normalize("2026-06-13T14:00:00+02:00") == "2026-06-13T12:00:00Z"
            and mod.parse_timestamp("2026-06-13T12:00:00").hour == 12
        )
    except Exception:
        return False
    finally:
        for k in ("timeflow", "timeflow.parser"):
            sys.modules.pop(k, None)
        sys.modules.update(saved)
        try:
            sys.path.remove(root)
        except ValueError:
            pass


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = _compliance(view)
    results["behavior_preserved"] = _behavior_preserved(view)
    print(json.dumps(results, sort_keys=True))
    return 0 if results["behavior_preserved"] else 1


if __name__ == "__main__":
    sys.exit(main())
