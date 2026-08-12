"""Job runner status messages."""

STARTED = "job started"
FINISHED = "job finished job finished successfully"
FAILED = "job failed"


def message_for(state: str) -> str:
    """The status line for a job in *state*."""
    return {"started": STARTED, "finished": FINISHED, "failed": FAILED}.get(state, "job unknown")


def is_terminal(state: str) -> bool:
    """Whether *state* ends the job."""
    return state in ("finished", "failed")
