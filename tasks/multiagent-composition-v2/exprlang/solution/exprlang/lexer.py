"""Tokenizer for exprlang (arithmetic + comparison + boolean)."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import LexError


@dataclass(frozen=True)
class Token:
    kind: str
    value: object = None


_KEYWORDS = {
    "and": "AND",
    "or": "OR",
    "not": "NOT",
    "true": "TRUE",
    "false": "FALSE",
}

# Two-character operators, matched before single characters (maximal munch).
_MULTI = [("==", "EQ"), ("!=", "NE"), ("<=", "LE"), (">=", "GE")]

_SINGLE = {
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
    "%": "PERCENT",
    "(": "LPAREN",
    ")": "RPAREN",
    "<": "LT",
    ">": "GT",
}


def tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in " \t\n\r":
            i += 1
            continue
        two = src[i : i + 2]
        matched = False
        for text, kind in _MULTI:
            if two == text:
                tokens.append(Token(kind))
                i += 2
                matched = True
                break
        if matched:
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
            word = src[i:j]
            tokens.append(Token(_KEYWORDS.get(word, "NAME"), word))
            i = j
            continue
        raise LexError(f"unexpected character {c!r} at position {i}")
    tokens.append(Token("EOF"))
    return tokens
