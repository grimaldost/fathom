#!/usr/bin/env python3
"""Stop hook: ensure opt-in treasuryutils feedback is written (safety net).

OFF BY DEFAULT. Does nothing unless the consumer set ``TREASURYUTILS_FEEDBACK``
to a truthy value. When opted in, at the end of a turn it blocks ONCE to ask the
agent to write the per-session feedback report — but only when ALL of:

- we are not already inside a stop-hook continuation (``stop_hook_active``),
- the per-session report file does not already exist (the ``SessionStart`` prime
  hook usually got the agent to write it), and
- the transcript shows treasuryutils was actually USED this session — a tool call
  touching treasuryutils, not merely the plugin's injected guidance text.

Otherwise it stays silent and allows the stop. Fail-safe: on any uncertainty it
allows the stop, so it can never trap a session.

Exit codes:
  0 — always (a block is signalled via the JSON 'decision' field, not the code).
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path

_TRUTHY = frozenset({'1', 'true', 'yes', 'on'})

# Bound the transcript scan (defensive against a pathologically large file).
_MAX_TRANSCRIPT_BYTES = 4_000_000

# Consumer skills whose invocation counts as treasuryutils usage.
_CONSUMER_SKILLS = (
    'treasuryutils-usage',
    'auth-setup',
    'dataset-creation',
    'setup-source-bindings',
)


def _feedback_enabled() -> bool:
    """True only when the consumer opted in via TREASURYUTILS_FEEDBACK."""
    return os.environ.get('TREASURYUTILS_FEEDBACK', '').strip().lower() in _TRUTHY


def _feedback_file(session_id: str) -> Path:
    """Per-session report path; both feedback hooks derive it identically."""
    override = os.environ.get('TREASURYUTILS_FEEDBACK_DIR', '').strip()
    if override:
        base = Path(override).expanduser()
    else:
        base = Path.home() / 'Downloads' / 'treasuryutils-feedback'
    token = (session_id or 'session').replace('/', '_').replace('\\', '_')[:8] or 'session'
    return base / f'tu-feedback-{token}.md'


def _iter_tool_use_blocks(event: object) -> list[object]:
    """Return the tool_use content blocks of a transcript event (shape-tolerant)."""
    if not isinstance(event, dict):
        return []
    message = event.get('message')
    source = message if isinstance(message, dict) else event
    content = source.get('content')
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict) and b.get('type') == 'tool_use']


def _line_signals_usage(line: str) -> bool:
    """True if a transcript line carries a tool_use that touched treasuryutils."""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return False
    for block in _iter_tool_use_blocks(event):
        payload = json.dumps(block).lower()
        if 'treasuryutils' in payload:
            return True
        if any(skill in payload for skill in _CONSUMER_SKILLS):
            return True
    return False


def _transcript_uses_treasuryutils(transcript_path: str) -> bool:
    """Scan tool_use blocks in the transcript for real treasuryutils usage."""
    if not transcript_path:
        return False
    path = Path(transcript_path)
    if not path.is_file():
        return False
    seen = 0
    with contextlib.suppress(OSError), path.open('r', encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            seen += len(line)
            if seen > _MAX_TRANSCRIPT_BYTES:
                break
            if _line_signals_usage(line):
                return True
    return False


def _reason(file_path: str) -> str:
    """The block reason that asks the agent to write the missing report."""
    return (
        'Before finishing: treasuryutils testing feedback is enabled and this '
        'session used treasuryutils, but no feedback report was written yet. Write '
        f'a short Markdown report now to `{file_path}` (create the folder if '
        'needed). Sections: Context (date, treasuryutils version, OS, the task in '
        'one line); Goal & APIs used; What worked; Friction (unclear / '
        'harder-than-expected / where you guessed, missing or wrong docs — tag '
        'low/med/high); Errors (verbatim + whether the guidance helped); '
        'Suggestions. NEVER include secrets or real data (.env values, tokens, '
        'client/tenant IDs, connection strings, customer/financial data) — refer '
        'to them by name only. Then tell the user the path and stop.'
    )


def main() -> None:
    """Block once for a missing report when opted in and treasuryutils was used."""
    raw = ''
    with contextlib.suppress(OSError, ValueError):
        raw = sys.stdin.read()

    if not _feedback_enabled():
        sys.exit(0)

    data: dict[str, object] = {}
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        loaded = json.loads(raw) if raw else {}
        if isinstance(loaded, dict):
            data = loaded

    # Loop guard: never re-block inside a continuation this hook caused.
    if data.get('stop_hook_active'):
        sys.exit(0)

    target = _feedback_file(str(data.get('session_id', '')))
    if target.exists():
        sys.exit(0)  # the prime hook already got the report written

    if not _transcript_uses_treasuryutils(str(data.get('transcript_path', ''))):
        sys.exit(0)  # treasuryutils was not actually used this session

    print(json.dumps({'decision': 'block', 'reason': _reason(str(target))}))
    sys.exit(0)


if __name__ == '__main__':
    main()
