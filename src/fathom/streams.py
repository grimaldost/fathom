"""Packaged reader for the CLI's ``--output-format stream-json`` event stream.

Every question fathom asks of a spawn *after* the fact — was the plugin actually
registered, did the hook fire, did an ``mcp__*`` call succeed or come back denied,
how many turns did the arm burn — is answered by re-reading these events.  Until
this module existed that parsing lived twice: once inside the adapter (for
tokens/turns) and once as experiment-local script code under ``scripts-rg2x2/``,
which is why the arming defect could not be checked by the harness that
introduced it.

Stdlib only.  Pure functions over already-parsed events: :func:`parse_events`
materialises the stream once (a list, not an iterator, because every caller asks
several questions of the same stream), and the accessors are total — a stream
with no init event yields empty lists rather than raising, so a probe that
observed nothing is reported as "observed nothing" instead of crashing the gate.

Field names come from real persisted streams under ``streams-rg2x2/``:

    {"type":"system","subtype":"init","tools":[...],"skills":[...],
     "plugins":[{"name","path","version"}],"mcp_servers":[{"name","status"}]}
    {"type":"system","subtype":"hook_started","hook_name":"SessionStart:startup",
     "hook_event":"SessionStart"}
    {"type":"assistant","message":{"content":[{"type":"tool_use","id","name","input"}]}}
    {"type":"user","message":{"content":[{"type":"tool_result","tool_use_id",
     "is_error","content"}]}}
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from typing import Any

Event = dict[str, Any]

# Substrings the CLI uses when a tool call is refused by the permission layer.
# A denial is reported as an ordinary tool_result with is_error=true, so the text
# is the only discriminator between "denied" and "the tool ran and errored".
_DENIAL_MARKERS = (
    "requested permissions",
    "permission denied",
    "have not granted it",
    "is not allowed",
    "was blocked",
)

MCP_TOOL_PREFIX = "mcp__"


def parse_events(lines: Iterable[str]) -> list[Event]:
    """Parse NDJSON *lines* into events, silently dropping unparsable ones.

    Tolerant by construction: a truncated final line (a killed spawn) or an
    interleaved non-JSON warning must not lose the events that did arrive.
    """
    out: list[Event] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


# ---------------------------------------------------------------------------
# The init event — everything the spawn reports about its own configuration
# ---------------------------------------------------------------------------


def find_init(events: Sequence[Event]) -> Event | None:
    """The ``system/init`` event, or None.

    Emitted before any model turn, so every fact it carries is model-agnostic
    and costs nothing beyond the spawn that was happening anyway.
    """
    for ev in events:
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            return ev
    return None


def _init_list(events: Sequence[Event], key: str) -> list[Any]:
    init = find_init(events)
    if init is None:
        return []
    value = init.get(key)
    return list(value) if isinstance(value, list) else []


def init_tools(events: Sequence[Event]) -> list[str]:
    """Tool names REGISTERED for the spawn.

    Registration is not permission: the allow-list is applied later, per call, so
    a tool can appear here and still be denied every time it is used.  That gap is
    exactly the serena-nav defect, and telling the two apart is why this accessor
    and :func:`permission_denied_tools` are separate.
    """
    return [str(t) for t in _init_list(events, "tools")]


def init_skills(events: Sequence[Event]) -> list[str]:
    """Skill identifiers (``<plugin>:<skill-dir>``) the spawn reports as available."""
    return [str(s) for s in _init_list(events, "skills") if s]


def init_plugins(events: Sequence[Event]) -> list[Event]:
    """Mounted plugins as ``{"name", "path", "version"}`` dicts."""
    return [p for p in _init_list(events, "plugins") if isinstance(p, dict)]


def init_mcp_servers(events: Sequence[Event]) -> list[Event]:
    """MCP servers as ``{"name", "status"}`` dicts.

    Includes ambient account-level connectors the spawn inherits, which routinely
    sit at ``pending`` / ``needs-auth`` and belong to no arm — callers must
    attribute a server to a declared mount before asserting on its status.
    """
    return [s for s in _init_list(events, "mcp_servers") if isinstance(s, dict)]


def init_model(events: Sequence[Event]) -> str | None:
    init = find_init(events)
    model = init.get("model") if init else None
    return str(model) if model else None


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


def _hook_events(events: Sequence[Event]) -> list[Event]:
    return [
        ev
        for ev in events
        if ev.get("type") == "system"
        and str(ev.get("subtype", "")).startswith("hook_")
        and ev.get("hook_name")
    ]


def hook_names(events: Sequence[Event]) -> list[str]:
    """Distinct ``hook_name`` values observed, in first-seen order.

    A user-scope settings hook that is wired announces itself here; a plugin hook
    in headless ``-p`` does not fire at all, which is the whole reason the
    ``[settings]`` arming axis exists.
    """
    seen: list[str] = []
    for ev in _hook_events(events):
        name = str(ev["hook_name"])
        if name not in seen:
            seen.append(name)
    return seen


def hook_event_kinds(events: Sequence[Event]) -> list[str]:
    """Distinct ``hook_event`` kinds (``SessionStart``, ``PreToolUse``, …)."""
    seen: list[str] = []
    for ev in _hook_events(events):
        kind = str(ev.get("hook_event") or "").strip()
        if kind and kind not in seen:
            seen.append(kind)
    return seen


# ---------------------------------------------------------------------------
# Tool calls and their results
# ---------------------------------------------------------------------------


def _blocks(events: Sequence[Event], event_type: str, block_type: str) -> list[Event]:
    out: list[Event] = []
    for ev in events:
        if ev.get("type") != event_type:
            continue
        content = (ev.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for blk in content:
            if isinstance(blk, dict) and blk.get("type") == block_type:
                out.append(blk)
    return out


def tool_uses(events: Sequence[Event]) -> list[Event]:
    """Assistant ``tool_use`` blocks as ``{"id", "name", "input"}``."""
    return [
        {"id": b.get("id"), "name": str(b.get("name") or ""), "input": b.get("input") or {}}
        for b in _blocks(events, "assistant", "tool_use")
    ]


def tool_results(events: Sequence[Event]) -> list[Event]:
    """User ``tool_result`` blocks as ``{"tool_use_id", "is_error", "text"}``.

    ``is_error`` is normalised to a bool: the CLI omits it on success, and an
    absent flag must not read as an error.
    """
    out: list[Event] = []
    for b in _blocks(events, "user", "tool_result"):
        content = b.get("content")
        text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        out.append(
            {
                "tool_use_id": b.get("tool_use_id"),
                "is_error": bool(b.get("is_error")),
                "text": text,
            }
        )
    return out


def _results_by_id(events: Sequence[Event]) -> dict[Any, Event]:
    return {r["tool_use_id"]: r for r in tool_results(events) if r["tool_use_id"] is not None}


def successful_mcp_calls(events: Sequence[Event]) -> list[str]:
    """Names of ``mcp__*`` calls that returned a non-error result.

    A ``tool_use`` with no matching result is NOT successful — an unanswered call
    is the tell of a spawn that died mid-turn, not evidence the server worked.
    """
    results = _results_by_id(events)
    out: list[str] = []
    for use in tool_uses(events):
        name = use["name"]
        if not name.startswith(MCP_TOOL_PREFIX):
            continue
        result = results.get(use["id"])
        if result is not None and not result["is_error"]:
            out.append(name)
    return out


def permission_denied_tools(events: Sequence[Event]) -> list[str]:
    """Names of tools whose result reads as a permission refusal, first-seen order."""
    results = _results_by_id(events)
    seen: list[str] = []
    for use in tool_uses(events):
        result = results.get(use["id"])
        if result is None or not result["is_error"]:
            continue
        low = result["text"].lower()
        if any(marker in low for marker in _DENIAL_MARKERS) and use["name"] not in seen:
            seen.append(use["name"])
    return seen


def skill_invocations(events: Sequence[Event]) -> list[str]:
    """Skill identifiers passed to the ``Skill`` tool, in call order.

    Lifted from the rg-2x2 activation script, which had to hand-roll it because
    the harness offered no packaged way to ask whether a skill actually fired.
    """
    out: list[str] = []
    for use in tool_uses(events):
        if use["name"] != "Skill":
            continue
        raw = use["input"]
        value = raw.get("skill") if isinstance(raw, dict) else None
        out.append(str(value) if value else json.dumps(raw, ensure_ascii=False))
    return out
