"""Deterministic type-contract probe (harness-side gate augmentation).

Checks ONLY the bool-is-a-subclass-of-int contract class -- the defect class that
dominates weak-tier failures on this task: arithmetic and comparison operators must
REJECT boolean operands with an ExprError subclass (the task statement gives these
type rules explicitly). Deliberately narrow: short-circuiting, precedence, the error
CLASS, and env-borne values stay uncovered, so the blind acceptance oracle keeps a
real escape surface -- this probe strengthens a gate, it must never become the oracle.

Two groups, so the gate can scope each to the phase that introduces the rule it
checks: `arith` (six cases) is meaningful from PR01 onward, `compare` (four cases)
only once PR02 has landed the comparison operators. Running the comparison cases
against a tree that has no comparison operators yet would red on a ParseError, which
is not the contract this probe exists to check.

Every case here is DE-OVERLAPPED from `verify.py`: no probe expression is graded by
the acceptance oracle, as a literal string or after stripping spaces and parentheses
(`tests/test_multiagent_bank.py` enforces it). A probe case that is also a graded
case would make the primary endpoint reachable from inside an arm's gate.

Usage: python type_probe.py <workspace-root> [--group arith|compare|all]
Exit 0 = the contract holds for the selected group.
"""

import sys

_GROUPS = {
    # Boolean operands where a number is required, arithmetic operators only.
    "arith": (
        "true * 3",
        "5 - false",
        "-false",
        "false / 4",
        "true % 5",
        "3 + true",
    ),
    # Boolean operands where a number is required, comparison operators only.
    "compare": (
        "2 == true",
        "false < 1",
        "true >= false",
        "1 > false",
    ),
}

_RULE = (
    "arithmetic and comparison operators must reject boolean operands "
    "(bool is a subclass of int in Python; exclude it explicitly)"
)


def _parse_argv(argv):
    """Return (workspace, group) from *argv* (the script's own argv[1:])."""
    workspace = "."
    group = "all"
    rest = list(argv)
    if "--group" in rest:
        i = rest.index("--group")
        if i + 1 >= len(rest):
            raise SystemExit("type-contract probe: --group needs a value")
        group = rest[i + 1]
        del rest[i : i + 2]
    if rest:
        workspace = rest[0]
    if group not in ("all", *_GROUPS):
        raise SystemExit(f"type-contract probe: unknown group {group!r}")
    return workspace, group


def main(argv):
    workspace, group = _parse_argv(argv)
    cases = _GROUPS["arith"] + _GROUPS["compare"] if group == "all" else _GROUPS[group]

    sys.path.insert(0, workspace)
    try:
        from exprlang import evaluate
        from exprlang.errors import ExprError
    except Exception as exc:  # the package must at least import
        print(f"type-contract probe [{group}]: cannot import exprlang: {exc}")
        return 1

    failures = []
    for src in cases:
        try:
            got = evaluate(src)
        except ExprError:
            continue
        except Exception as exc:
            failures.append(
                f"  {src!r}: raised {type(exc).__name__} (must be an ExprError subclass)"
            )
            continue
        failures.append(
            f"  {src!r}: returned {got!r} (must raise a type error: booleans are not numbers)"
        )

    if failures:
        print(f"type-contract probe [{group}] FAILED -- {_RULE}:")
        print("\n".join(failures))
        return 1

    print(f"type-contract probe [{group}] OK ({len(cases)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
