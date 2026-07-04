"""Error hierarchy for exprlang."""

from __future__ import annotations


class ExprError(Exception):
    """Base class for every error raised by exprlang."""


class LexError(ExprError):
    """The input string could not be tokenized."""


class ParseError(ExprError):
    """The token stream is not a well-formed expression."""


class EvalError(ExprError):
    """An error raised while evaluating a well-formed expression.

    Covers division/modulo by zero and references to unknown variables.
    """
