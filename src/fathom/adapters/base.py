"""Runner protocol and RunRecord — the vendor-abstract model-call boundary.

Every model invocation in fathom (task-attempt runs and judge calls alike) goes
through a Runner (``docs/adr/0001-subscription-cli-behind-vendor-abstract-runner.md``).
``Runner.execute`` returns a ``RunRecord``: the raw economy and outcome of one
spawn.  v1 ships exactly one adapter, ``claude_cli`` (subscription auth); no code
outside ``adapters/`` may invoke a model directly.

Stdlib only.
"""

from __future__ import annotations

import dataclasses
import enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from fathom.scenario import ResolvedScenario


class ExitStatus(enum.StrEnum):
    """Outcome classification for one Runner spawn.

    The split exists so the matrix can stop cleanly on infrastructure trouble
    without scoring it or burning a trial's error-retry budget (spec §5, §10).

    - ``OK`` — the spawn completed and the agent did not report an error.
    - ``ERROR`` — a task-level failure: the agent reported an error, or the CLI
      exited non-zero for a reason that is the run's own fault.  Scored, and
      burns a trial's error-retry budget.
    - ``TIMEOUT`` — the spawn exceeded its wall-clock budget; whatever streamed
      before the kill was parsed (partial-stream tolerance).
    - ``INFRASTRUCTURE`` — auth failure, subscription usage-limit, or a missing
      CLI: never scored, never burns a trial's error-retry budget.
    """

    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    INFRASTRUCTURE = "infrastructure"


@dataclasses.dataclass
class RunRecord:
    """Raw economy and outcome of one Runner spawn.

    ``tokens_*``, ``num_turns``, ``duration_s`` and ``cost_usd_est`` are the
    economy currency the report aggregates; ``cost_usd_est`` is an
    adapter-computed estimate (ADR-0001), tokens/turns/wall-clock are primary.
    ``model_id`` is the exact model id the CLI reported (it may differ from the
    requested slug) and ``cli_version`` pins the transport — both recorded so a
    vendor swap is visible in history rather than silent.  ``usage`` keeps the
    raw CLI-reported usage mapping so a downstream consumer can recover fields
    this dataclass does not name.  ``tokens_cache`` combines the CLI's two cache
    buckets (read + creation).
    """

    status: ExitStatus
    tokens_in: int = 0
    tokens_out: int = 0
    tokens_cache: int = 0
    num_turns: int = 0
    duration_s: float = 0.0
    cost_usd_est: float = 0.0
    model_id: str = ""
    cli_version: str = ""
    result_text: str = ""
    usage: dict[str, Any] = dataclasses.field(default_factory=dict)

    @property
    def is_infrastructure(self) -> bool:
        """True when this run must not be scored and must not burn retry budget."""
        return self.status is ExitStatus.INFRASTRUCTURE

    @property
    def is_error(self) -> bool:
        """True for any non-OK outcome (task error, timeout, or infrastructure)."""
        return self.status is not ExitStatus.OK


@runtime_checkable
class Runner(Protocol):
    """Vendor-abstract model-call boundary (ADR-0001).

    An adapter runs ``prompt`` in ``workspace`` under the resolved ``scenario``
    and returns a ``RunRecord``.  The inputs carry no scenario *identity* beyond
    the resolved transport pins the scenario already holds; grading stays blind.
    """

    def execute(
        self,
        prompt: str,
        workspace: Path,
        scenario: ResolvedScenario,
        max_turns: int | None = None,
    ) -> RunRecord:
        """Run ``prompt`` in ``workspace`` under ``scenario``; return a RunRecord.

        ``max_turns`` is the trial's turn budget (e.g. the task's
        ``task.limits.max_turns``); ``None`` falls back to the adapter default.
        """
        ...
