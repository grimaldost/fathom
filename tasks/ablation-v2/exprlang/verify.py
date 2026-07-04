"""Acceptance verifier for `exprlang` (harness-side, scenario-blind).

Reads ONLY the result-view path in argv[1], imports the candidate `exprlang`
package, and black-box tests it against an independent, obviously-correct reference
evaluator implemented here over generated ASTs. The candidate is fed
FULLY-PARENTHESIZED source strings (so precedence cannot confound the property
test), while targeted cases check precedence, short-circuiting in both directions,
the bool-is-a-subclass-of-int type rules, and multi-character operator lexing.

This oracle is a STRICT SUPERSET of the visible gate (tests/test_feature.py):
passing the gate does not guarantee passing here. Seeded; deterministic.
"""

import json
import random
import sys

_ALL = (
    "arith_regression",
    "comparisons",
    "bool_ops",
    "not_op",
    "precedence",
    "and_short_circuit",
    "or_short_circuit",
    "short_circuit_propagates",
    "type_bool_in_arith",
    "type_num_in_bool",
    "type_compare_bool",
    "division_semantics",
    "lexing_multichar",
    "bool_result_type",
    "property_random",
)


class _RefError(Exception):
    """The reference evaluator rejects this expression (value error or type error)."""


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _ref(node, env):
    """Independent reference evaluator over the tuple AST (the source of truth)."""
    kind = node[0]
    if kind == "num" or kind == "bool":
        return node[1]
    if kind == "var":
        if node[1] not in env:
            raise _RefError("unknown variable")
        return env[node[1]]
    if kind == "unary":
        op = node[1]
        if op == "NOT":
            v = _ref(node[2], env)
            if not isinstance(v, bool):
                raise _RefError("not requires bool")
            return not v
        v = _ref(node[2], env)
        if not _is_number(v):
            raise _RefError("unary requires number")
        return -v if op == "MINUS" else +v
    if kind == "binary":
        op = node[1]
        if op == "AND":
            left = _ref(node[2], env)
            if not isinstance(left, bool):
                raise _RefError("and requires bool")
            if not left:
                return False
            right = _ref(node[3], env)
            if not isinstance(right, bool):
                raise _RefError("and requires bool")
            return right
        if op == "OR":
            left = _ref(node[2], env)
            if not isinstance(left, bool):
                raise _RefError("or requires bool")
            if left:
                return True
            right = _ref(node[3], env)
            if not isinstance(right, bool):
                raise _RefError("or requires bool")
            return right
        left = _ref(node[2], env)
        right = _ref(node[3], env)
        if op in ("EQ", "NE", "LT", "LE", "GT", "GE"):
            if not _is_number(left) or not _is_number(right):
                raise _RefError("comparison requires numbers")
            return {
                "EQ": left == right,
                "NE": left != right,
                "LT": left < right,
                "LE": left <= right,
                "GT": left > right,
                "GE": left >= right,
            }[op]
        if not _is_number(left) or not _is_number(right):
            raise _RefError("arithmetic requires numbers")
        if op == "PLUS":
            return left + right
        if op == "MINUS":
            return left - right
        if op == "STAR":
            return left * right
        if op == "SLASH":
            if right == 0:
                raise _RefError("division by zero")
            return left / right
        if op == "PERCENT":
            if right == 0:
                raise _RefError("modulo by zero")
            return left % right
    raise _RefError("bad node")


_SYM = {
    "PLUS": "+",
    "MINUS": "-",
    "STAR": "*",
    "SLASH": "/",
    "PERCENT": "%",
    "EQ": "==",
    "NE": "!=",
    "LT": "<",
    "LE": "<=",
    "GT": ">",
    "GE": ">=",
    "AND": "and",
    "OR": "or",
}


def _render(node):
    kind = node[0]
    if kind == "num":
        return repr(node[1])
    if kind == "bool":
        return "true" if node[1] else "false"
    if kind == "var":
        return node[1]
    if kind == "unary":
        if node[1] == "NOT":
            return "(not " + _render(node[2]) + ")"
        return "(" + ("-" if node[1] == "MINUS" else "+") + _render(node[2]) + ")"
    return "(" + _render(node[2]) + " " + _SYM[node[1]] + " " + _render(node[3]) + ")"


def _gen_num(rng, depth):
    if depth <= 0 or rng.random() < 0.35:
        pick = rng.random()
        if pick < 0.55:
            return ("num", rng.randint(0, 5))
        if pick < 0.75:
            return ("num", rng.choice([0.5, 1.5, 2.0, 3.0]))
        return ("var", rng.choice(["x", "y", "z"]))
    if rng.random() < 0.2:
        return ("unary", rng.choice(["MINUS", "PLUS"]), _gen_num(rng, depth - 1))
    op = rng.choice(["PLUS", "MINUS", "STAR", "SLASH", "PERCENT"])
    return ("binary", op, _gen_num(rng, depth - 1), _gen_num(rng, depth - 1))


def _gen_bool(rng, depth):
    if depth <= 0 or rng.random() < 0.35:
        pick = rng.random()
        if pick < 0.5:
            return ("bool", rng.random() < 0.5)
        if pick < 0.75:
            return ("var", rng.choice(["p", "q"]))
        op = rng.choice(["EQ", "NE", "LT", "LE", "GT", "GE"])
        return ("binary", op, _gen_num(rng, depth - 1), _gen_num(rng, depth - 1))
    if rng.random() < 0.3:
        return ("unary", "NOT", _gen_bool(rng, depth - 1))
    op = rng.choice(["AND", "OR"])
    return ("binary", op, _gen_bool(rng, depth - 1), _gen_bool(rng, depth - 1))


def _val_eq(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b) < 1e-9
    return a == b


def _criteria(view):
    sys.path.insert(0, view)
    try:
        import exprlang as Q
        from exprlang.errors import ExprError
    except Exception:
        return dict.fromkeys(_ALL, False)

    def run(src, env=None):
        """Return ('val', v), ('err',), or ('crash',)."""
        try:
            return ("val", Q.evaluate(src, env or {}))
        except ExprError:
            return ("err",)
        except Exception:
            return ("crash",)

    def val_ok(src, expected, env=None):
        r = run(src, env)
        return r[0] == "val" and _val_eq(r[1], expected)

    def err_ok(src, env=None):
        return run(src, env) == ("err",)

    R = {}

    R["arith_regression"] = all(
        [
            val_ok("1 + 2 * 3", 7),
            val_ok("10 - 2 - 3", 5),
            val_ok("6 / 2", 3.0),
            val_ok("10 % 3", 1),
            val_ok("-2 * 3", -6),
            val_ok("x + 1", 11, {"x": 10}),
        ]
    )

    R["comparisons"] = all(
        [
            val_ok("1 < 2", True),
            val_ok("2 <= 2", True),
            val_ok("3 > 5", False),
            val_ok("5 >= 5", True),
            val_ok("4 == 4", True),
            val_ok("4 != 4", False),
            val_ok("2 > 3", False),
        ]
    )

    R["bool_ops"] = all(
        [
            val_ok("true and true", True),
            val_ok("true and false", False),
            val_ok("false or true", True),
            val_ok("false or false", False),
            val_ok("true or false", True),
        ]
    )

    R["not_op"] = all(
        [
            val_ok("not true", False),
            val_ok("not false", True),
            val_ok("not (1 < 2)", False),
            val_ok("not 1 < 2", False),
        ]
    )

    R["precedence"] = all(
        [
            val_ok("2 + 3 * 4", 14),
            val_ok("2 * 3 == 6", True),
            val_ok("1 < 2 and 2 < 1", False),
            val_ok("not false or false", True),
            val_ok("true or false and false", True),
            val_ok("1 + 1 < 4 - 1", True),
        ]
    )

    R["and_short_circuit"] = all(
        [
            val_ok("false and (1 / 0 > 0)", False),
            val_ok("false and (1 / 0 == 0)", False),
        ]
    )

    R["or_short_circuit"] = all(
        [
            val_ok("true or (1 / 0 > 0)", True),
            val_ok("true or (1 % 0 == 0)", True),
        ]
    )

    R["short_circuit_propagates"] = all(
        [
            err_ok("true and (1 / 0 > 0)"),
            err_ok("false or (1 / 0 > 0)"),
        ]
    )

    R["type_bool_in_arith"] = all(
        [
            err_ok("true + 1"),
            err_ok("1 * false"),
            err_ok("-true"),
            err_ok("1 - true"),
        ]
    )

    # RHS operands are chosen so short-circuit does NOT skip them (left operand
    # forces evaluation of the right): `true and _` and `false or _` both evaluate
    # the right, where the number then fails the bool type check.
    R["type_num_in_bool"] = all(
        [
            err_ok("1 and true"),
            err_ok("true and 2"),
            err_ok("false or 2"),
            err_ok("not 5"),
            err_ok("0 and 1"),
        ]
    )

    R["type_compare_bool"] = all(
        [
            err_ok("true < false"),
            err_ok("true == false"),
            err_ok("1 < true"),
        ]
    )

    R["division_semantics"] = all(
        [
            val_ok("7 / 2", 3.5),
            val_ok("7 % 3", 1),
            err_ok("1 / 0"),
            err_ok("5 % 0"),
        ]
    )

    R["lexing_multichar"] = all(
        [
            val_ok("1 <= 1", True),
            val_ok("2 >= 3", False),
            val_ok("1 == 1", True),
            val_ok("1 != 2", True),
        ]
    )

    r_true = run("1 < 2")
    r_and = run("true and true")
    r_not = run("not false")
    R["bool_result_type"] = (
        r_true[0] == "val"
        and r_true[1] is True
        and r_and[0] == "val"
        and r_and[1] is True
        and r_not[0] == "val"
        and r_not[1] is True
    )

    # ---- property: random ASTs, fully parenthesized, vs the reference ----
    try:
        rng = random.Random(20260701)
        env = {"x": 2, "y": 3, "z": 0, "p": True, "q": False}
        ok = True
        for _ in range(60):
            gen = _gen_num if rng.random() < 0.5 else _gen_bool
            ast = gen(rng, 3)
            src = _render(ast)
            try:
                expected = _ref(ast, env)
                exp_err = False
            except _RefError:
                expected, exp_err = None, True
            got = run(src, env)
            if got[0] == "crash":
                ok = False
                break
            got_err = got == ("err",)
            if got_err != exp_err:
                ok = False
                break
            if not exp_err and not _val_eq(expected, got[1]):
                ok = False
                break
        R["property_random"] = ok
    except Exception:
        R["property_random"] = False

    return R


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    results = _criteria(sys.argv[1])
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
