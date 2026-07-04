"""Tokenizer for exprlang.

Turns a source string into a flat list of :class:`Token` ending in an ``EOF``
token. Whitespace is skipped. Numbers are ``int`` unless they contain a ``.``,
in which case they are ``float``. Bare words become ``NAME`` tokens (variables).
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import LexError


@dataclass(frozen=True)
class Token:
    kind: str
    value: object = None


# Single-character operators and punctuation.
_SINGLE = {
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
    "%": "PERCENT",
    "(": "LPAREN",
    ")": "RPAREN",
}


def tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in " \t\n\r":
            i += 1
            continue
        if c in _SINGLE:
            tokens.append(Token(_SINGLE[c]))
            i += 1
            continue
        if c.isdigit() or (c == "." and i + 1 < n and src[i + 1].isdigit()):
            j = i
            seen_dot = False
            while j < n and (src[j].isdigit() or (src[j] == "." and not seen_dot)):
                if src[j] == ".":
                    seen_dot = True
                j += 1
            text = src[i:j]
            tokens.append(Token("NUMBER", float(text) if seen_dot else int(text)))
            i = j
            continue
        if c.isalpha() or c == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            tokens.append(Token("NAME", src[i:j]))
            i = j
            continue
        raise LexError(f"unexpected character {c!r} at position {i}")
    tokens.append(Token("EOF"))
    return tokens
