"""Acceptance verifier for control-nonlocal-parse (harness-side, scenario-blind).

PORTED VERBATIM in behaviour from ``tasks/model-tier-v1/fix-nonlocal-parse/verify.py``.
The only differences are mechanical: it imports this bank's ``bankverify`` instead of
v1's ``bugfix_verify`` (the two share the same primitives, carried over unchanged), and
it emits through ``bv.emit`` so a criterion that raises is recorded as ``False`` rather
than crashing the verifier. The four criteria, their exact assertions and the exit-code
rule (0 iff all four hold) are v1's, because this task is the bank's POSITIVE CONTROL
and its v1 reading only transfers if the bar is identical. Do not add criteria here.

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/parse.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003).

This is a NON-LOCAL root-cause task. The symptom shows up in the consumers (``codes``
raises, ``messages`` is garbled), but the real bug is the shared ``parse_line``
(``line.split()`` ignores quoted messages). A symptom-driven band-aid in a consumer can
fix the reported case yet fails the other consumer and the tagged-line cases; only
fixing ``parse_line`` (the root cause) passes both hard criteria. The optional trailing
TAG is what defeats consumer band-aids like ``fields[-1]`` / ``" ".join(fields[1:-1])``.

It carries no oracle slice: ``../oracles.toml`` records thin = standard = strong here,
because inventing levels for the control would change the task it is controlling for.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "logparse"
MODULE = "parse.py"
BUGGY_ORIGINAL = HERE / "original" / "parse.py"
SHIPPED_TESTS = HERE / "original" / "tests"

STANDARD = [
    "messages_quoted",
    "codes_quoted_tagged",
    "no_regression",
    "regression_test_present",
]


def _report(view: Path):  # noqa: ANN202 - a module or None
    return bv.import_candidate(view, "logparse.report", PACKAGE)


def _messages_quoted(view: Path) -> bool:
    """messages() recovers a quoted message, even with a trailing tag.

    The tagged case defeats a ``" ".join(fields[1:-1])`` band-aid in messages().
    """
    mod = _report(view)
    if mod is None or not hasattr(mod, "messages"):
        return False
    return mod.messages(['ERROR "disk full" 500']) == ["disk full"] and mod.messages(
        ['WARN "low disk space" 200 urgent']
    ) == ["low disk space"]


def _codes_quoted_tagged(view: Path) -> bool:
    """codes() reads the right field for quoted messages, even with a trailing tag.

    The tagged case defeats an ``int(fields[-1])`` band-aid in codes().
    """
    mod = _report(view)
    if mod is None or not hasattr(mod, "codes"):
        return False
    return mod.codes(['ERROR "disk full" 500']) == [500] and mod.codes(
        ['WARN "low disk space" 200 urgent']
    ) == [200]


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])

    results = {
        "messages_quoted": bv.check(lambda: _messages_quoted(view)),
        "codes_quoted_tagged": bv.check(lambda: _codes_quoted_tagged(view)),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
