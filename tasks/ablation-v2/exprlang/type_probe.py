"""Deterministic type-contract probe (harness-side gate augmentation, arm E1).

Checks ONLY the bool-is-a-subclass-of-int contract class -- the gate-invisible
defect class that dominates weak-tier failures on this task: arithmetic and
comparison operators must REJECT boolean operands with an ExprError subclass
(the task spec states these type rules explicitly). Deliberately narrow:
or-short-circuit, precedence, and general semantics stay uncovered, so the blind
acceptance oracle's residual escape surface survives -- this probe strengthens
the gate, it must not become the oracle.

Usage: python type_probe.py <workspace-root>    (exit 0 = contract holds)
"""

import sys

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")

try:
    from exprlang import evaluate
    from exprlang.errors import ExprError
except Exception as exc:  # the package must at least import
    print(f"type-contract probe: cannot import exprlang: {exc}")
    sys.exit(1)

# Boolean operands where a number is required. Every case must raise an
# ExprError subclass (per the task's stated type rules).
CASES = [
    "true + 1",
    "1 + true",
    "1 - true",
    "2 * false",
    "true / 2",
    "false % 2",
    "-true",
    "1 < true",
    "true == false",
    "false >= 0",
]

failures = []
for src in CASES:
    try:
        got = evaluate(src)
    except ExprError:
        continue
    except Exception as exc:
        failures.append(f"  {src!r}: raised {type(exc).__name__} (must be an ExprError subclass)")
        continue
    failures.append(
        f"  {src!r}: returned {got!r} (must raise a type error: booleans are not numbers)"
    )

if failures:
    print(
        "type-contract probe FAILED -- arithmetic/comparison operators must reject "
        "boolean operands (bool is a subclass of int in Python; exclude it explicitly):"
    )
    print("\n".join(failures))
    sys.exit(1)

print(f"type-contract probe OK ({len(CASES)} cases)")
