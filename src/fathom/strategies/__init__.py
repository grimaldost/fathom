"""Strategy executors: how a scenario turns one task into model spawns (spec §6).

``single_session`` makes exactly one Runner call; ``series`` drives the series
engine (the one sanctioned non-adapter model-call path).  Both satisfy the
:class:`StrategyExecutor` protocol and return a :class:`TrialResult`.
"""

from fathom.strategies.base import (
    PIN_SERIES,
    PIN_STRONG,
    StrategyExecutor,
    TrialResult,
    TrialStatus,
)
from fathom.strategies.gated_session import GatedSessionExecutor
from fathom.strategies.series import EngineOutcome, SeriesExecutor
from fathom.strategies.reprompt_session import RepromptSessionExecutor
from fathom.strategies.single_session import SingleSessionExecutor

# The canonical set of strategy names a scenario's ``strategy`` field may carry.
# The executor factory (``fathom.cli._default_executor_factory``) dispatches on
# exactly these; anything else is a typo and must be REJECTED, never silently run
# as the single-session default (which would score the wrong arm under the intended
# arm's name — the "unarmed arm" failure class this harness otherwise guards against).
KNOWN_STRATEGIES: frozenset[str] = frozenset(
    {
        "single-session",
        "gated-session",
        "gated-review",
        "reprompt-session",
        "series",
    }
)

__all__ = [
    "KNOWN_STRATEGIES",
    "PIN_SERIES",
    "PIN_STRONG",
    "EngineOutcome",
    "GatedSessionExecutor",
    "SeriesExecutor",
    "RepromptSessionExecutor",
    "SingleSessionExecutor",
    "StrategyExecutor",
    "TrialResult",
    "TrialStatus",
]
