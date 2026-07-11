#!/usr/bin/env python3
"""SessionStart hook: prime opt-in treasuryutils testing feedback.

OFF BY DEFAULT. This hook emits nothing unless the consumer has opted in by
setting ``TREASURYUTILS_FEEDBACK`` to a truthy value (``1`` / ``true`` / ``yes``
/ ``on``). When opted in, it injects one standing instruction: *if* this session
actually uses treasuryutils, write a short, secret-free feedback report to a
dedicated folder before wrapping up. The companion ``Stop`` hook
(``feedback-capture.py``) is the safety net that ensures the report is written.

Nothing is installed, nothing is written, and no context is injected for a
consumer who has not opted in.

Exit codes:
  0 — always (context priming is non-blocking).
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path

# Truthy values that turn the (otherwise off) feedback capture on.
_TRUTHY = frozenset({'1', 'true', 'yes', 'on'})


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


def _instruction(file_path: str) -> str:
    """The standing feedback instruction injected into the session context."""
    return (
        'treasuryutils testing feedback is ENABLED for this session (the consumer '
        'set TREASURYUTILS_FEEDBACK). IF — and only if — this session actually '
        'USES treasuryutils (you run it or its CLI, write or debug code that calls '
        'it, or invoke one of its consumer skills), then before your final summary '
        f'write a short Markdown feedback report to `{file_path}` (create the '
        'folder if needed; use exactly that path so it is not duplicated). '
        'Sections: Context (date, installed treasuryutils version, OS, the task in '
        'one line); Goal & APIs used; What worked; Friction (anything unclear, '
        'harder than expected, where you guessed or hesitated, or docs that were '
        'missing or wrong — tag each low/med/high); Errors (verbatim, and whether '
        'the guidance helped); Suggestions. NEVER write secrets or real data into '
        'the report — no .env values, tokens, client/tenant IDs, connection '
        'strings, or customer/financial data; refer to them by name only. Keep it '
        'honest and specific; short is fine. After writing, tell the user the path '
        'in one line. If this session does NOT use treasuryutils, do nothing.'
    )


def main() -> None:
    """Inject the feedback instruction when opted in; otherwise stay silent."""
    raw = ''
    with contextlib.suppress(OSError, ValueError):
        raw = sys.stdin.read()

    if not _feedback_enabled():
        sys.exit(0)

    session_id = ''
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        payload = json.loads(raw) if raw else {}
        if isinstance(payload, dict):
            session_id = str(payload.get('session_id', ''))

    context = _instruction(str(_feedback_file(session_id)))
    print(json.dumps({'additionalContext': context}))
    sys.exit(0)


if __name__ == '__main__':
    main()
