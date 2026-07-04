"""AST evaluator for exprlang (arithmetic + comparison + boolean).

Type rules: arithmetic and comparison operators require numeric (int/float, NOT
bool) operands; boolean operators (and/or/not) require bool operands. `and`/`or`
short-circuit. Wrong-typed operands raise :class:`TypeMismatchError`.
"""

from __future__ import annotations

from .errors import EvalError, TypeMismatchError
from .parser import parse


def evaluate(expr: str, env: dict | None = None):
    env = {} if env is None else env
    return _eval(parse(expr), env)


def _is_number(v) -> bool:
    # bool is a subclass of int, so exclude it explicitly.
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _need_number(v, op):
    if not _is_number(v):
        raise TypeMismatchError(f"operator {op!r} requires a number, got {v!r}")
    return v


def _need_bool(v, op):
    if not isinstance(v, bool):
        raise TypeMismatchError(f"operator {op!r} requires a boolean, got {v!r}")
    return v


_COMPARE = {
    "EQ": lambda a, b: a == b,
    "NE": lambda a, b: a != b,
    "LT": lambda a, b: a < b,
    "LE": lambda a, b: a <= b,
    "GT": lambda a, b: a > b,
    "GE": lambda a, b: a >= b,
}


def _eval(node, env):
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "bool":
        return node[1]
    if kind == "var":
        name = node[1]
        if name not in env:
            raise EvalError(f"unknown variable {name!r}")
        return env[name]
    if kind == "unary":
        op = node[1]
        if op == "NOT":
            return not _need_bool(_eval(node[2], env), "not")
        operand = _need_number(_eval(node[2], env), op)
        return -operand if op == "MINUS" else +operand
    if kind == "binary":
        op = node[1]
        # Boolean operators short-circuit: evaluate the right side lazily.
        if op == "AND":
            if not _need_bool(_eval(node[2], env), "and"):
                return False
            return _need_bool(_eval(node[3], env), "and")
        if op == "OR":
            if _need_bool(_eval(node[2], env), "or"):
                return True
            return _need_bool(_eval(node[3], env), "or")
        left = _eval(node[2], env)
        right = _eval(node[3], env)
        if op in _COMPARE:
            _need_number(left, op)
            _need_number(right, op)
            return _COMPARE[op](left, right)
        # arithmetic
        _need_number(left, op)
        _need_number(right, op)
        if op == "PLUS":
            return left + right
        if op == "MINUS":
            return left - right
        if op == "STAR":
            return left * right
        if op == "SLASH":
            if right == 0:
                raise EvalError("division by zero")
            return left / right
        if op == "PERCENT":
            if right == 0:
                raise EvalError("modulo by zero")
            return left % right
    raise EvalError(f"cannot evaluate node {node!r}")
