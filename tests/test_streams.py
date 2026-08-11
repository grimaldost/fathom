"""Tests for fathom.streams — the packaged stream-json reader.

Stdlib-only (`python tests/test_streams.py` runs without uv).  The fixtures below
are trimmed from real persisted streams under ``streams-rg2x2/`` so the field
names are the ones the live CLI actually emits, not invented ones.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom import streams  # noqa: E402

INIT = {
    "type": "system",
    "subtype": "init",
    "cwd": "C:\\tmp\\ws",
    "session_id": "s1",
    "tools": ["Read", "Write", "Bash", "mcp__plugin_serena_serena__find_symbol"],
    "mcp_servers": [
        {"name": "plugin:serena:serena", "status": "connected"},
        {"name": "claude.ai Gmail", "status": "needs-auth"},
    ],
    "model": "claude-haiku-4-5",
    "permissionMode": "default",
    "skills": ["humblepowers:brainstorming", "fathom-smoke-canary:probe"],
    "plugins": [
        {"name": "serena", "path": "C:\\plug\\serena", "version": "1.2.0"},
    ],
    "claude_code_version": "2.1.218",
}

HOOK_STARTED = {
    "type": "system",
    "subtype": "hook_started",
    "hook_name": "SessionStart:startup",
    "hook_event": "SessionStart",
}

ASSISTANT_TOOL_USE = {
    "type": "assistant",
    "message": {
        "content": [
            {"type": "text", "text": "Looking it up."},
            {
                "type": "tool_use",
                "id": "tu_1",
                "name": "mcp__plugin_serena_serena__find_symbol",
                "input": {"name_path": "foo"},
            },
        ]
    },
}

USER_TOOL_RESULT_DENIED = {
    "type": "user",
    "message": {
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "tu_1",
                "is_error": True,
                "content": "Claude requested permissions to use "
                "mcp__plugin_serena_serena__find_symbol, but you have not granted it.",
            }
        ]
    },
}

USER_TOOL_RESULT_OK = {
    "type": "user",
    "message": {
        "content": [
            {"type": "tool_result", "tool_use_id": "tu_1", "is_error": False, "content": "ok"}
        ]
    },
}


def _lines(*events: dict) -> list[str]:
    return [json.dumps(e) for e in events]


class ParseEventsTests(unittest.TestCase):
    def test_parses_ndjson_and_skips_garbage(self) -> None:
        lines = ["", "not json", json.dumps(INIT), "  ", "[1,2]"]
        events = streams.parse_events(lines)
        # Only the dict event survives; a bare JSON array is not an event.
        self.assertEqual([e["subtype"] for e in events], ["init"])

    def test_accepts_a_single_blob_of_text(self) -> None:
        blob = "\n".join(_lines(INIT, HOOK_STARTED))
        self.assertEqual(len(streams.parse_events(blob.splitlines())), 2)


class InitEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events = streams.parse_events(_lines(INIT, ASSISTANT_TOOL_USE))

    def test_find_init_returns_the_init_event(self) -> None:
        self.assertEqual(streams.find_init(self.events)["session_id"], "s1")

    def test_find_init_returns_none_when_absent(self) -> None:
        self.assertIsNone(streams.find_init(streams.parse_events(_lines(HOOK_STARTED))))

    def test_init_tools_skills_plugins_mcp_servers(self) -> None:
        self.assertIn("mcp__plugin_serena_serena__find_symbol", streams.init_tools(self.events))
        self.assertIn("fathom-smoke-canary:probe", streams.init_skills(self.events))
        self.assertEqual([p["name"] for p in streams.init_plugins(self.events)], ["serena"])
        names = [s["name"] for s in streams.init_mcp_servers(self.events)]
        self.assertIn("plugin:serena:serena", names)

    def test_init_accessors_are_empty_without_an_init_event(self) -> None:
        empty = streams.parse_events(_lines(HOOK_STARTED))
        self.assertEqual(streams.init_tools(empty), [])
        self.assertEqual(streams.init_skills(empty), [])
        self.assertEqual(streams.init_plugins(empty), [])
        self.assertEqual(streams.init_mcp_servers(empty), [])


class ToolCallTests(unittest.TestCase):
    def test_tool_uses_and_results_pair_by_id(self) -> None:
        events = streams.parse_events(_lines(INIT, ASSISTANT_TOOL_USE, USER_TOOL_RESULT_DENIED))
        uses = streams.tool_uses(events)
        self.assertEqual([u["name"] for u in uses], ["mcp__plugin_serena_serena__find_symbol"])
        results = streams.tool_results(events)
        self.assertEqual(results[0]["tool_use_id"], "tu_1")
        self.assertTrue(results[0]["is_error"])

    def test_successful_mcp_calls_excludes_a_denied_call(self) -> None:
        denied = streams.parse_events(_lines(INIT, ASSISTANT_TOOL_USE, USER_TOOL_RESULT_DENIED))
        self.assertEqual(streams.successful_mcp_calls(denied), [])
        # ...and counts the same call when it is not an error.
        ok = streams.parse_events(_lines(INIT, ASSISTANT_TOOL_USE, USER_TOOL_RESULT_OK))
        self.assertEqual(
            streams.successful_mcp_calls(ok), ["mcp__plugin_serena_serena__find_symbol"]
        )

    def test_a_tool_use_with_no_result_is_not_counted_successful(self) -> None:
        # The "registered but denied" tell: the model tried, nothing came back.
        events = streams.parse_events(_lines(INIT, ASSISTANT_TOOL_USE))
        self.assertEqual(streams.successful_mcp_calls(events), [])

    def test_permission_denied_names_the_denied_tool(self) -> None:
        events = streams.parse_events(_lines(INIT, ASSISTANT_TOOL_USE, USER_TOOL_RESULT_DENIED))
        self.assertEqual(
            streams.permission_denied_tools(events), ["mcp__plugin_serena_serena__find_symbol"]
        )

    def test_skill_invocations(self) -> None:
        ev = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "id": "s1", "name": "Skill", "input": {"skill": "x:y"}}
                ]
            },
        }
        self.assertEqual(streams.skill_invocations(streams.parse_events(_lines(ev))), ["x:y"])


class HookTests(unittest.TestCase):
    def test_hook_names_and_events(self) -> None:
        events = streams.parse_events(_lines(INIT, HOOK_STARTED))
        self.assertEqual(streams.hook_names(events), ["SessionStart:startup"])
        self.assertEqual(streams.hook_event_kinds(events), ["SessionStart"])

    def test_no_hooks_is_an_empty_list_not_an_error(self) -> None:
        self.assertEqual(streams.hook_names(streams.parse_events(_lines(INIT))), [])


if __name__ == "__main__":
    unittest.main()
