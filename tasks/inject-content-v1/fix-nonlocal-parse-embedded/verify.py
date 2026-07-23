"""Acceptance verifier for fix-nonlocal-parse (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/parse.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003). Emits a flat
``{criterion: bool}`` JSON object and exits 0 iff every criterion holds.

This is a NON-LOCAL root-cause task. The symptom shows up in the consumers
(``codes`` raises, ``messages`` is garbled), but the real bug is the shared
``parse_line`` (``line.split()`` ignores quoted messages). A symptom-driven band-aid
in a consumer can fix the reported case yet fails the other consumer and the
tagged-line cases; only fixing ``parse_line`` (the root cause) passes both criteria.
The optional trailing TAG is what defeats consumer band-aids like ``fields[-1]`` /
``" ".join(fields[1:-1])``.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bugfix_verify` resolves

import bugfix_verify as bv  # noqa: E402

PACKAGE = "logparse"
MODULE = "parse.py"
BUGGY_ORIGINAL = HERE / "original" / "parse.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _report(view):
    return bv.import_candidate(view, "logparse.report", PACKAGE)


def _messages_quoted(view: Path) -> bool:
    """messages() recovers a quoted message, even with a trailing tag.

    The tagged case defeats a ``" ".join(fields[1:-1])`` band-aid in messages().
    """
    mod = _report(view)
    if mod is None or not hasattr(mod, "messages"):
        return False
    try:
        return mod.messages(['ERROR "disk full" 500']) == ["disk full"] and mod.messages(
            ['WARN "low disk space" 200 urgent']
        ) == ["low disk space"]
    except Exception:
        return False


def _codes_quoted_tagged(view: Path) -> bool:
    """codes() reads the right field for quoted messages, even with a trailing tag.

    The tagged case defeats a ``int(fields[-1])`` band-aid in codes().
    """
    mod = _report(view)
    if mod is None or not hasattr(mod, "codes"):
        return False
    try:
        return mod.codes(['ERROR "disk full" 500']) == [500] and mod.codes(
            ['WARN "low disk space" 200 urgent']
        ) == [200]
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = {
        "messages_quoted": _messages_quoted(view),
        "codes_quoted_tagged": _codes_quoted_tagged(view),
        "no_regression": bv.no_regression(view, SHIPPED_TESTS),
        "regression_test_present": bv.regression_test_present(
            view, PACKAGE, MODULE, BUGGY_ORIGINAL
        ),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
