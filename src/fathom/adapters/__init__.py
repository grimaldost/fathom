"""Model-call adapters.

All model invocations go through a ``Runner`` (ADR-0001).  v1 ships exactly one
adapter, :class:`~fathom.adapters.claude_cli.ClaudeCliRunner`.
"""

from __future__ import annotations

from fathom.adapters.base import ExitStatus, RunRecord, Runner
from fathom.adapters.claude_cli import (
    ClaudeCliRunner,
    build_command,
    cleanup_dir,
    make_isolated_config,
    parse_stream,
)

__all__ = [
    "ExitStatus",
    "RunRecord",
    "Runner",
    "ClaudeCliRunner",
    "build_command",
    "cleanup_dir",
    "make_isolated_config",
    "parse_stream",
]
