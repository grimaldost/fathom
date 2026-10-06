"""Unit tests for the agent acceptance harness.

Tests cover: stream parsing, classification, ground-truth checks, and prompt guards.
All tests use synthetic data; no real spawns.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add tools directory to path for imports
tools_dir = Path(__file__).parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

import agent_acceptance as acc  # noqa: E402


class TestPromptGuard(unittest.TestCase):
    """Test prompt validation."""

    def test_prompt_guard_clean(self):
        """Clean prompt passes."""
        scenario = acc.ScenarioConfig(
            name="test",
            prompt="Tell me about AI systems.",
            workspace_kind="empty",
            allow_spend=False,
        )
        errors = acc.guard_prompt(scenario)
        self.assertEqual(errors, [])

    def test_prompt_guard_forbids_fathom_command(self):
        """Prompt containing /fathom: is rejected."""
        scenario = acc.ScenarioConfig(
            name="test",
            prompt="Run /fathom:run to test.",
            workspace_kind="empty",
            allow_spend=False,
        )
        errors = acc.guard_prompt(scenario)
        self.assertTrue(any("fathom:" in e for e in errors))

    def test_prompt_guard_forbids_dry_run(self):
        """Prompt containing --dry-run is rejected."""
        scenario = acc.ScenarioConfig(
            name="test",
            prompt="Use --dry-run to plan.",
            workspace_kind="empty",
            allow_spend=False,
        )
        errors = acc.guard_prompt(scenario)
        self.assertTrue(any("--dry-run" in e for e in errors))

    def test_prompt_guard_forbids_fathom_skill_name(self):
        """Prompt containing fathom-eval is rejected."""
        scenario = acc.ScenarioConfig(
            name="test",
            prompt="Invoke the fathom-eval skill.",
            workspace_kind="empty",
            allow_spend=False,
        )
        errors = acc.guard_prompt(scenario)
        self.assertTrue(any("fathom-eval" in e for e in errors))

    def test_prompt_guard_s3_forbids_fathom_word(self):
        """S3 prompt must not contain the word 'fathom'."""
        scenario = acc.ScenarioConfig(
            name="unnamed-discovery",
            prompt="Is there something that measures whether a tool improves results?",
            workspace_kind="clone",
            allow_spend=False,
        )
        errors = acc.guard_prompt(scenario)
        self.assertEqual(errors, [])

        scenario_bad = acc.ScenarioConfig(
            name="unnamed-discovery",
            prompt="Find fathom to measure tool effectiveness.",
            workspace_kind="clone",
            allow_spend=False,
        )
        errors = acc.guard_prompt(scenario_bad)
        self.assertTrue(any("fathom" in e.lower() for e in errors))


class TestStreamParsing(unittest.TestCase):
    """Test stream-json parsing."""

    def test_parse_valid_events(self):
        """Parse valid stream-json lines."""
        lines = [
            '{"type": "system", "subtype": "init", "model": "claude-opus"}',
            '{"type": "assistant", "message": {"content": []}}',
        ]
        events = acc.parse_stream_lines(lines)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["type"], "system")

    def test_parse_malformed_lines(self):
        """Tolerate malformed lines."""
        lines = [
            '{"type": "system"}',
            "not valid json",
            '{"type": "assistant"}',
            "",
        ]
        events = acc.parse_stream_lines(lines)
        self.assertEqual(len(events), 2)

    def test_parse_empty_input(self):
        """Handle empty input."""
        events = acc.parse_stream_lines([])
        self.assertEqual(events, [])


class TestToolClassification(unittest.TestCase):
    """Test tool use classification."""

    def test_classify_mcp_tool(self):
        """Classify MCP tool."""
        tool_use = {"name": "mcp__plugin_fathom_fathom__plan"}
        surface, subcmd = acc.classify_tool_use(tool_use, {})
        self.assertEqual(surface, "mcp")
        self.assertIsNone(subcmd)

    def test_classify_skill(self):
        """Classify Skill tool with fathom skill."""
        tool_use = {"name": "Skill"}
        input_ = {"skill": "fathom:run"}
        surface, _ = acc.classify_tool_use(tool_use, input_)
        self.assertEqual(surface, "skill")

    def test_classify_slash_command(self):
        """Classify SlashCommand with /fathom:."""
        tool_use = {"name": "SlashCommand"}
        input_ = {"command": "/fathom:smoke"}
        surface, subcmd = acc.classify_tool_use(tool_use, input_)
        self.assertEqual(surface, "command")
        self.assertEqual(subcmd, "smoke")

    def test_classify_cli_fathom(self):
        """Classify Bash with fathom CLI."""
        tool_use = {"name": "Bash"}
        input_ = {"command": "python -m fathom run bank"}
        surface, subcmd = acc.classify_tool_use(tool_use, input_)
        self.assertEqual(surface, "cli")
        self.assertEqual(subcmd, "run")

    def test_classify_docs_read(self):
        """Classify Read of fathom docs."""
        tool_use = {"name": "Read"}
        input_ = {"file_path": "/path/to/fathom/docs/something.md"}
        surface, _ = acc.classify_tool_use(tool_use, input_)
        self.assertEqual(surface, "docs")

    def test_classify_other(self):
        """Classify tool not fathom-related."""
        tool_use = {"name": "Bash"}
        input_ = {"command": "ls -la"}
        surface, _ = acc.classify_tool_use(tool_use, input_)
        self.assertEqual(surface, "other")


class TestStreamAnalysis(unittest.TestCase):
    """Test full stream analysis."""

    def test_analyze_complete_stream(self):
        """Analyze a complete stream."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stream_file = Path(tmpdir) / "stream.jsonl"
            stream_file.write_text(
                '{"type": "system", "subtype": "init", "model": "claude-sonnet", '
                '"tools": ["Read", "Bash"], "skills": ["fathom-eval"], '
                '"mcp_servers": [{"name": "fathom", "status": "connected"}], '
                '"plugins": []}\n'
                '{"type": "assistant", "message": {"content": ['
                '{"type": "tool_use", "id": "u1", "name": "mcp__plugin_fathom_fathom__plan", '
                '"input": {"bank": "test"}}'
                "]}}\n"
                '{"type": "user", "message": {"content": ['
                '{"type": "tool_result", "tool_use_id": "u1", "is_error": false, '
                '"content": "plan output"}'
                "]}}\n"
                '{"type": "result", "num_turns": 1, "total_cost_usd": 0.05, '
                '"duration_ms": 30000, "is_error": false, "result": "done"}\n'
            )

            analysis = acc.analyze_stream(stream_file)
            self.assertEqual(analysis.model, "claude-sonnet")
            self.assertTrue(analysis.fathom_mcp_connected)
            self.assertTrue(analysis.fathom_skill_visible)
            self.assertEqual(len(analysis.tool_uses), 1)
            self.assertEqual(analysis.tool_uses[0].surface, "mcp")
            self.assertEqual(analysis.num_turns, 1)
            self.assertAlmostEqual(analysis.total_cost_usd, 0.05, places=2)

    def test_analyze_stream_with_errors(self):
        """Analyze stream with tool errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stream_file = Path(tmpdir) / "stream.jsonl"
            stream_file.write_text(
                '{"type": "system", "subtype": "init", "model": "claude-sonnet", '
                '"tools": ["Read"], "skills": ["fathom-eval"], '
                '"mcp_servers": [{"name": "fathom", "status": "connected"}], '
                '"plugins": []}\n'
                '{"type": "assistant", "message": {"content": ['
                '{"type": "tool_use", "id": "u1", "name": "mcp__plugin_fathom_fathom__plan", '
                '"input": {}}'
                "]}}\n"
                '{"type": "user", "message": {"content": ['
                '{"type": "tool_result", "tool_use_id": "u1", "is_error": true, '
                '"content": "requested permissions"}'
                "]}}\n"
            )

            analysis = acc.analyze_stream(stream_file)
            self.assertEqual(len(analysis.tool_results), 1)
            self.assertTrue(analysis.tool_results[0].is_error)
            self.assertIn("requested permissions", analysis.fathom_surface_errors)

    def test_analyze_stream_no_init(self):
        """Handle stream without init event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stream_file = Path(tmpdir) / "stream.jsonl"
            stream_file.write_text('{"type": "result", "num_turns": 0}\n')

            analysis = acc.analyze_stream(stream_file)
            self.assertIsNone(analysis.model)
            self.assertEqual(len(analysis.init_tools), 0)
            self.assertFalse(analysis.fathom_mcp_connected)


class TestGroundTruthChecks(unittest.TestCase):
    """Test ground-truth validation functions."""

    def test_check_s2_bank_structure_valid(self):
        """Valid S2 structure passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)

            # Create required structure
            (ws / "fathom.toml").write_text("[data_root]\nschema = 1\n")

            tasks = ws / "tasks" / "mybank"
            tasks.mkdir(parents=True)
            (tasks / "bank.toml").write_text("[]\n")

            task_dir = tasks / "task1"
            task_dir.mkdir()
            (task_dir / "task.toml").write_text("[]\n")
            (task_dir / "verify.py").write_text("# verifier\n")

            scenarios = ws / "scenarios"
            scenarios.mkdir()
            (scenarios / "arm1.toml").write_text("[]\n")
            (scenarios / "arm2.toml").write_text("[]\n")

            ledger = ws / "ledger"
            ledger.mkdir()
            (ledger / "mybank.jsonl").write_text(
                '{"status": "completed", "config_hash": "h1", "cost_usd_est": 0.1}\n'
                '{"status": "completed", "config_hash": "h2", "cost_usd_est": 0.1}\n'
            )

            passed, evidence = acc.check_s2_bank_structure(ws, budget_usd=1.0)
            self.assertTrue(passed, evidence)

    def test_check_s2_missing_fathom_toml(self):
        """Missing fathom.toml fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            passed, evidence = acc.check_s2_bank_structure(ws, budget_usd=1.0)
            self.assertFalse(passed)
            self.assertIn("fathom.toml", evidence)

    def test_check_s2_cost_exceeded(self):
        """Cost exceeding budget fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)

            (ws / "fathom.toml").write_text("[data_root]\n")
            (ws / "tasks" / "bank").mkdir(parents=True)
            (ws / "tasks" / "bank" / "bank.toml").write_text("[]\n")
            (ws / "tasks" / "bank" / "task1").mkdir()
            (ws / "tasks" / "bank" / "task1" / "task.toml").write_text("[]\n")
            (ws / "tasks" / "bank" / "task1" / "verify.py").write_text("[]\n")

            (ws / "scenarios").mkdir()
            (ws / "scenarios" / "a1.toml").write_text("[]\n")
            (ws / "scenarios" / "a2.toml").write_text("[]\n")

            (ws / "ledger").mkdir()
            (ws / "ledger" / "bank.jsonl").write_text(
                '{"status": "completed", "config_hash": "h1", "cost_usd_est": 2.0}\n'
                '{"status": "completed", "config_hash": "h2", "cost_usd_est": 2.0}\n'
            )

            passed, evidence = acc.check_s2_bank_structure(ws, budget_usd=1.0)
            self.assertFalse(passed)
            self.assertIn("cost", evidence.lower())


if __name__ == "__main__":
    unittest.main()
