"""Acceptance verifier for feature-retry-backoff (harness-side, scenario-blind, ADR-0003).

Reads ONLY argv[1] (the result-view path); carries no scenario/arm identity; runs
offline. Imports the candidate ``retrier`` package and grades:

  behavior_correct  - the hidden happy-path suite passes. This is the correctness
                      gate: the process exit code is 0 iff this holds. The edge
                      criteria ride alongside as the discriminating per-criterion
                      signal (a rushed solution clears the gate yet trips an edge).
  zero_retry        - attempts=1 calls fn once and re-raises without sleeping.
  jitter_bounds     - every delay stays within [0, min(max_delay, base*2**k)];
                      the cap is honored and jitter never overshoots it.
  error_propagation - a non-retryable exception raises immediately; after
                      exhaustion the LAST attempt's exception is re-raised.
  tests_present     - the candidate's OWN tests genuinely exercise the edges: they
                      pass against the candidate's code AND fail against a
                      happy-path-correct naive mutant (a mutation kill). A
                      happy-path-only suite does not count.

Every criterion is defensive: any exception yields False, so a missing or broken
feature scores a *fail*, never an *error*. Emits a flat {criterion: bool} JSON
object; exits 0 iff behavior_correct.
"""

import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

PKG = "retrier"
SUBMODULES = ("core", "backoff")

# A happy-path-correct naive mutant: eventual success below the cap works, but it
# sleeps after the final attempt (zero-retry bug), never caps the delay and adds
# jitter on top (overshoot), and catches every exception (ignores retry_on). Used
# only to check whether the candidate's tests actually exercise the edges.
_MUT_CLOCK = """\
import time


def elapsed(start, monotonic=time.monotonic):
    return monotonic() - start
"""

_MUT_BACKOFF = """\
def compute_delay(k, base_delay, max_delay, jitter=False, rand=None):
    delay = base_delay * (2 ** k)
    if jitter:
        if rand is None:
            import random

            rand = random.random
        delay = delay + rand() * delay
    return delay
"""

_MUT_CORE = """\
import random
import time


def retry(fn, *, attempts, base_delay, max_delay, retry_on=(Exception,),
          jitter=False, sleep=time.sleep, rand=random.random):
    last = None
    for k in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
            delay = base_delay * (2 ** k)
            if jitter:
                delay = delay + rand() * delay
            sleep(delay)
    raise last
"""

_MUT_INIT = (
    "from .clock import elapsed\nfrom .core import retry\n\n__all__ = ['elapsed', 'retry']\n"
)

# Stdlib test runner: collects both unittest.TestCase classes and bare test_*
# functions (pytest-style), so the candidate's tests are run whatever style they
# chose. Prints {"collected": n, "failed": m} as JSON.
_RUNNER_SRC = """\
import importlib.util
import json
import sys
import types
import unittest


class _FuncCase(unittest.TestCase):
    def __init__(self, fn):
        super().__init__("runTest")
        self._fn = fn

    def runTest(self):
        self._fn()


def _load(path, idx):
    name = "candmod_%d" % idx
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    test_files = json.loads(sys.argv[1])
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    import_failures = 0
    for idx, path in enumerate(test_files):
        try:
            mod = _load(path, idx)
        except Exception:
            import_failures += 1
            continue
        for attr in dir(mod):
            obj = getattr(mod, attr, None)
            if (
                isinstance(obj, type)
                and issubclass(obj, unittest.TestCase)
                and obj is not unittest.TestCase
            ):
                for case in loader.loadTestsFromTestCase(obj):
                    suite.addTest(case)
        for attr in dir(mod):
            if attr.startswith("test"):
                obj = getattr(mod, attr, None)
                if isinstance(obj, types.FunctionType):
                    suite.addTest(_FuncCase(obj))
    result = unittest.TestResult()
    suite.run(result)
    collected = result.testsRun + import_failures
    failed = len(result.failures) + len(result.errors) + import_failures
    print(json.dumps({"collected": collected, "failed": failed}))


if __name__ == "__main__":
    main()
"""


def _find_pkg_init(view: Path) -> Path | None:
    for cand in (view / PKG / "__init__.py", view / "src" / PKG / "__init__.py"):
        if cand.is_file():
            return cand
    for cand in view.rglob("__init__.py"):
        if "__pycache__" in cand.parts:
            continue
        if cand.parent.name == PKG:
            return cand
    return None


def _pkg_root(view: Path) -> str | None:
    init = _find_pkg_init(view)
    return str(init.parent.parent) if init else None


def _load_pkg(view: Path):
    root = _pkg_root(view)
    if root is None:
        return None
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        return importlib.import_module(PKG)
    except Exception:
        return None


def _get(mod, attr):
    if mod is None:
        return None
    if hasattr(mod, attr):
        return getattr(mod, attr)
    for sub in SUBMODULES:
        try:
            m = importlib.import_module(f"{PKG}.{sub}")
        except Exception:
            continue
        if hasattr(m, attr):
            return getattr(m, attr)
    return None


def _behavior_correct(retry) -> bool:
    calls, sleeps = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("x")
        return "ok"

    if retry(flaky, attempts=5, base_delay=1.0, max_delay=100.0, sleep=sleeps.append) != "ok":
        return False
    if sleeps != [1.0, 2.0]:
        return False

    calls2, sleeps2 = [], []

    def ok():
        calls2.append(1)
        return 42

    out = retry(ok, attempts=3, base_delay=1.0, max_delay=10.0, sleep=sleeps2.append)
    return out == 42 and sleeps2 == [] and calls2 == [1]


def _zero_retry(retry) -> bool:
    calls, sleeps = [], []

    def fn():
        calls.append(1)
        raise ValueError("boom")

    try:
        retry(fn, attempts=1, base_delay=1.0, max_delay=10.0, sleep=sleeps.append)
    except ValueError:
        return calls == [1] and sleeps == []
    except Exception:
        return False
    return False


def _jitter_bounds(retry) -> bool:
    sleeps = []

    def fn():
        raise ValueError("x")

    try:
        retry(
            fn,
            attempts=6,
            base_delay=1.0,
            max_delay=10.0,
            jitter=True,
            sleep=sleeps.append,
            rand=lambda: 1.0,
        )
    except ValueError:
        pass
    except Exception:
        return False
    if not sleeps:
        return False
    caps = [min(10.0, 1.0 * (2**k)) for k in range(len(sleeps))]
    return all(0.0 <= d <= cap for d, cap in zip(sleeps, caps))


def _error_propagation(retry) -> bool:
    # (a) a non-retryable exception propagates immediately — no retry, no sleep.
    calls, sleeps = [], []

    def boom_key():
        calls.append(1)
        raise KeyError("nope")

    try:
        retry(
            boom_key,
            attempts=5,
            base_delay=1.0,
            max_delay=10.0,
            retry_on=(ValueError,),
            sleep=sleeps.append,
        )
        return False
    except KeyError:
        if calls != [1] or sleeps != []:
            return False
    except Exception:
        return False

    # (b) after exhaustion the LAST attempt's exception is the one re-raised.
    seq = []

    def boom_seq():
        seq.append(1)
        raise ValueError(f"e{len(seq)}")

    try:
        retry(
            boom_seq,
            attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            retry_on=(ValueError,),
            sleep=lambda d: None,
        )
        return False
    except ValueError as exc:
        return str(exc) == "e3"
    except Exception:
        return False


def _discover_tests(view: Path) -> list[Path]:
    found: dict[str, Path] = {}
    for pat in ("test_*.py", "*_test.py"):
        for p in view.rglob(pat):
            if "__pycache__" in p.parts:
                continue
            found[str(p)] = p
    return [found[k] for k in sorted(found)]


def _run_suite(view: Path, test_files: list[Path], roots: list[str]) -> dict | None:
    with tempfile.TemporaryDirectory() as rdir:
        runner = Path(rdir) / "runner.py"
        runner.write_text(_RUNNER_SRC, encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(roots)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            proc = subprocess.run(
                [sys.executable, "-B", str(runner), json.dumps([str(p) for p in test_files])],
                cwd=str(view),
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception:
            return None
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except Exception:
                return None
    return None


def _write_mutant(dest: Path) -> None:
    pkg = dest / PKG
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(_MUT_INIT, encoding="utf-8")
    (pkg / "clock.py").write_text(_MUT_CLOCK, encoding="utf-8")
    (pkg / "backoff.py").write_text(_MUT_BACKOFF, encoding="utf-8")
    (pkg / "core.py").write_text(_MUT_CORE, encoding="utf-8")


def _tests_present(view: Path) -> bool:
    test_files = _discover_tests(view)
    if not test_files:
        return False
    root = _pkg_root(view) or str(view)
    cand = _run_suite(view, test_files, [root, str(view)])
    if not cand or cand.get("collected", 0) < 1 or cand.get("failed", 1) != 0:
        return False
    with tempfile.TemporaryDirectory() as mdir:
        _write_mutant(Path(mdir))
        mut = _run_suite(view, test_files, [mdir, str(view)])
    if not mut:
        return False
    return mut.get("failed", 0) >= 1


def _safe(fn, retry) -> bool:
    if retry is None:
        return False
    try:
        return bool(fn(retry))
    except Exception:
        return False


def _safe_call(fn, *args) -> bool:
    try:
        return bool(fn(*args))
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    mod = _load_pkg(view)
    retry = _get(mod, "retry")
    results = {
        "behavior_correct": _safe(_behavior_correct, retry),
        "zero_retry": _safe(_zero_retry, retry),
        "jitter_bounds": _safe(_jitter_bounds, retry),
        "error_propagation": _safe(_error_propagation, retry),
        "tests_present": _safe_call(_tests_present, view),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if results["behavior_correct"] else 1


if __name__ == "__main__":
    sys.exit(main())
