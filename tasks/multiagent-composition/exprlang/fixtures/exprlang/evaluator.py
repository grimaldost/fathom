"""AST evaluator for exprlang.

Walks the tuple AST produced by :mod:`exprlang.parser`. Variables are looked up in
the ``env`` mapping. Division and modulo by zero raise :class:`EvalError`.
"""

from __future__ import annotations

from .errors import EvalError
from .parser import parse


def evaluate(expr: str, env: dict | None = None):
    env = {} if env is None else env
    return _eval(parse(expr), env)


def _eval(node, env):
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "var":
        name = node[1]
        if name not in env:
            raise EvalError(f"unknown variable {name!r}")
        return env[name]
    if kind == "unary":
        op = node[1]
        operand = _eval(node[2], env)
        return -operand if op == "MINUS" else +operand
    if kind == "binary":
        op = node[1]
        left = _eval(node[2], env)
        right = _eval(node[3], env)
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
