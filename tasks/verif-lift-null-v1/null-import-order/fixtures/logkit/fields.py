"""Structured log field helpers."""

import time
import json
import os


def base_fields() -> dict:
    """Fields every log line carries."""
    return {"pid": os.getpid(), "ts": int(time.time())}


def render(fields: dict) -> str:
    """Render *fields* as one JSON line with sorted keys."""
    return json.dumps(fields, sort_keys=True)
