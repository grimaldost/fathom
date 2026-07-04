"""Pratt parser for exprlang (arithmetic + comparison + boolean).

AST shape:
    ("num", value) | ("bool", value) | ("var", name)
    ("unary", op_kind, operand) | ("binary", op_kind, left, right)

Binding powers, low to high:
    or (10) < and (20) < not (30, prefix) < comparisons (40)
      < + - (50) < * / % (60) < unary - + (70, prefix)
"""

from __future__ import annotations

from .errors import ParseError
from .lexer import Token, tokenize

_INFIX_BP = {
    "OR": 10,
    "AND": 20,
    "EQ": 40,
    "NE": 40,
    "LT": 40,
    "LE": 40,
    "GT": 40,
    "GE": 40,
    "PLUS": 50,
    "MINUS": 50,
    "STAR": 60,
    "SLASH": 60,
    "PERCENT": 60,
}

_PREFIX_BP = {
    "NOT": 30,
    "MINUS": 70,
    "PLUS": 70,
}

_LOWEST = 0


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self):
        node = self.parse_expr(_LOWEST)
        if self.peek().kind != "EOF":
            raise ParseError(f"unexpected token {self.peek().kind}")
        return node

    def parse_expr(self, min_bp: int):
        left = self.parse_prefix()
        while True:
            kind = self.peek().kind
            bp = _INFIX_BP.get(kind)
            if bp is None or bp <= min_bp:
                break
            self.advance()
            right = self.parse_expr(bp)  # left-associative
            left = ("binary", kind, left, right)
        return left

    def parse_prefix(self):
        kind = self.peek().kind
        if kind in _PREFIX_BP:
            self.advance()
            operand = self.parse_expr(_PREFIX_BP[kind])
            return ("unary", kind, operand)
        return self.parse_atom()

    def parse_atom(self):
        tok = self.advance()
        if tok.kind == "NUMBER":
            return ("num", tok.value)
        if tok.kind == "TRUE":
            return ("bool", True)
        if tok.kind == "FALSE":
            return ("bool", False)
        if tok.kind == "NAME":
            return ("var", tok.value)
        if tok.kind == "LPAREN":
            node = self.parse_expr(_LOWEST)
            if self.peek().kind != "RPAREN":
                raise ParseError("expected ')'")
            self.advance()
            return node
        raise ParseError(f"unexpected token {tok.kind}")


def parse(src: str):
    return _Parser(tokenize(src)).parse()
