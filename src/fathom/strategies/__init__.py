"""Strategy executors: how a scenario turns one task into model spawns (spec §6).

Every strategy makes its model calls through a Runner (ADR-0001); the strategy that
drove an external engine was retired in 0.13.0.  Each executor satisfies the
:class:`StrategyExecutor` protocol and returns a :class:`TrialResult`.
"""

from fathom.strategies.base import (
    PIN_SERIES,
    PIN_STRONG,
    StrategyExecutor,
    TrialResult,
    TrialStatus,
)
from fathom.strategies.gated_session import GatedSessionExecutor
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
    }
)

__all__ = [
    "KNOWN_STRATEGIES",
    "PIN_SERIES",
    "PIN_STRONG",
    "GatedSessionExecutor",
    "RepromptSessionExecutor",
    "SingleSessionExecutor",
    "StrategyExecutor",
    "TrialResult",
    "TrialStatus",
]
