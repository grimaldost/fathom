"""exprlang -- a tiny expression evaluator (arithmetic + comparison + boolean)."""

from .errors import EvalError, ExprError, LexError, ParseError, TypeMismatchError
from .evaluator import evaluate

__all__ = [
    "EvalError",
    "ExprError",
    "LexError",
    "ParseError",
    "TypeMismatchError",
    "evaluate",
]
