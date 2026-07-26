"""Blind verifier for thread-param. Reads only argv[1] (result-view)."""

import ast
import importlib
import json
import pathlib
import subprocess
import sys

ws = pathlib.Path(sys.argv[1])


def func_has_rounding_default(rel, funcname, default="bankers"):
    try:
        tree = ast.parse((ws / rel).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == funcname:
            args = n.args
            names = [a.arg for a in args.args] + [a.arg for a in args.kwonlyargs]
            if "rounding" not in names:
                return False
            for d in list(args.defaults) + list(args.kw_defaults):
                if isinstance(d, ast.Constant) and d.value == default:
                    return True
            return False
    return False


def passes_through(rel):
    try:
        txt = (ws / rel).read_text(encoding="utf-8")
    except OSError:
        return False
    return "rounding=rounding" in txt.replace(" ", "")


crit = {
    "signature_updated": func_has_rounding_default("ledgerline/core/fx.py", "convert"),
    "threaded_report": func_has_rounding_default("ledgerline/adapters/report.py", "build_report")
    and passes_through("ledgerline/adapters/report.py"),
    "threaded_daily": func_has_rounding_default("ledgerline/pipelines/daily.py", "run_daily")
    and passes_through("ledgerline/pipelines/daily.py"),
    "threaded_monthly": func_has_rounding_default("ledgerline/pipelines/monthly.py", "run_monthly")
    and passes_through("ledgerline/pipelines/monthly.py"),
}

# Behavioral check: 2.675 is a float that reprs cleanly ("2.675") but sits below
# the 2.68 midpoint in binary, so bankers/round() gives 2.67 while a correct
# str()->Decimal ROUND_HALF_UP gives 2.68. Deterministic on any platform.
sys.path.insert(0, str(ws))
try:
    fx = importlib.import_module("ledgerline.core.fx")
    crit["half_up_behavior"] = (
        fx.convert(2.675, 1.0, rounding="half-up") == 2.68 and fx.convert(2.675, 1.0) == 2.67
    )
except Exception:
    crit["half_up_behavior"] = False

try:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=ws, capture_output=True, text=True, timeout=120
    )
    crit["tests_pass"] = r.returncode == 0
except Exception:
    crit["tests_pass"] = False

print(json.dumps(crit))
sys.exit(0 if all(crit.values()) else 1)
