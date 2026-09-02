"""exprlang -- a tiny arithmetic expression evaluator.

Public API: :func:`evaluate` plus the error hierarchy in :mod:`exprlang.errors`.
"""

from .errors import EvalError, ExprError, LexError, ParseError
from .evaluator import evaluate

__all__ = ["EvalError", "ExprError", "LexError", "ParseError", "evaluate"]
