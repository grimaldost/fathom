#!/usr/bin/env python
"""Fresh-agent acceptance test for fathom plugin.

Spawns headless Claude agents with only user prompts and tool permissions,
no fathom-specific instructions. Agents learn to use fathom by exploring
available surfaces. Measures whether the plugin's CLI, MCP, skills and
slash commands work end-to-end.

All pure functions are unit-tested in tests/test_agent_acceptance.py.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

# Optional: import fathom.streams for analysis, but keep it optional
try:
    from fathom import streams as fathom_streams
except ImportError:
    fathom_streams = None


# ============================================================================
# Data structures
# ============================================================================


@dataclass
class ScenarioConfig:
    """A scenario's configuration."""

    name: str
    prompt: str
    workspace_kind: str  # "clone" or "empty"
    allow_spend: bool
    budget_usd: float = 0.0
    tools_allowed: list[str] = field(default_factory=list)
    tools_disallowed: list[str] = field(default_factory=list)
    timeout_s: int = 1800


@dataclass
class ToolUse:
    """A parsed tool_use from the stream."""

    index: int
    id: str | None
    name: str
    surface: str  # "skill", "command", "mcp", "cli", "docs"
    cli_subcommand: str | None = None
    input_summary: str = ""


@dataclass
class ToolResult:
    """A parsed tool_result from the stream."""

    tool_use_id: str | None
    is_error: bool
    text: str


@dataclass
class StreamAnalysis:
    """Analysis of a transcript stream."""

    model: str | None
    init_tools: list[str]
    init_skills: list[str]
    init_mcp_servers: list[dict[str, Any]]
    init_plugins: list[dict[str, Any]]
    fathom_mcp_connected: bool
    fathom_skill_visible: bool
    fathom_commands_visible: bool
    tool_uses: list[ToolUse]
    tool_results: list[ToolResult]
    fathom_surface_errors: list[str]
    fathom_surface_use_count: int
    first_fathom_use_index: int | None
    num_turns: int
    total_cost_usd: float
    duration_ms: int
    is_error: bool
    result_text: str
    malformed_lines: int


@dataclass
class Check:
    """A single check result."""

    name: str
    passed: bool
    evidence: str = ""


@dataclass
class Verdict:
    """Verdict for a single scenario run."""

    scenario_name: str
    checks: list[Check]
    surfaces_used: list[str]
    first_fathom_use_index: int | None
    stream_analysis: StreamAnalysis | None
    workspace_path: pathlib.Path
    cost_usd_est: float
    duration_s: float
    stderr_text: str

    def passed(self) -> bool:
        """All checks passed."""
        return all(c.passed for c in self.checks)


# ============================================================================
# Workspace setup
# ============================================================================


def setup_workspace(
    workspace_base: pathlib.Path,
    scenario: ScenarioConfig,
    data_root: pathlib.Path,
) -> tuple[pathlib.Path, dict[str, str]]:
    """Set up a workspace for the scenario.

    Returns (workspace_path, env_overrides).
    """
    workspace = workspace_base / scenario.name
    workspace.mkdir(parents=True, exist_ok=True)

    env_overrides: dict[str, str] = {}

    if scenario.workspace_kind == "clone":
        # Clone the data root locally
        clone_path = workspace / "data"
        if not clone_path.exists():
            subprocess.run(
                ["git", "clone", "--local", "--no-hardlinks", str(data_root), str(clone_path)],
                check=True,
                capture_output=True,
            )
        # Record initial state
        record_git_state(clone_path, workspace / "git_state_before.json")
        env_overrides["FATHOM_HOME"] = str(clone_path)

    elif scenario.workspace_kind == "empty":
        # Empty workspace, FATHOM_HOME unset
        pass

    return workspace, env_overrides


def record_git_state(repo_path: pathlib.Path, output_file: pathlib.Path) -> None:
    """Record git status and HEAD for the repository."""
    try:
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        head_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        state = {
            "status": status_result.stdout,
            "head": head_result.stdout.strip(),
        }
        output_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Failed to record git state: {exc}") from exc


def check_git_state_unchanged(
    repo_path: pathlib.Path, state_file: pathlib.Path
) -> tuple[bool, str]:
    """Check that git status and HEAD are unchanged."""
    if not state_file.exists():
        return True, "no git state recorded"

    before = json.loads(state_file.read_text(encoding="utf-8"))

    try:
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        head_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        after = {
            "status": status_result.stdout,
            "head": head_result.stdout.strip(),
        }
    except subprocess.CalledProcessError as exc:
        return False, f"git check failed: {exc}"

    if before != after:
        return False, f"git state changed:\nbefore: {before}\nafter: {after}"
    return True, "git state unchanged"


# ============================================================================
# Prompt guard
# ============================================================================


def guard_prompt(scenario: ScenarioConfig) -> list[str]:
    """Check that the prompt contains no fathom-specific instructions."""
    errors: list[str] = []
    prompt_lower = scenario.prompt.lower()

    forbidden_terms = [
        "/fathom:",
        "--dry-run",
        "fathom-eval",
        "mcp__",
        "python -m",
        "--home",
        "FATHOM_HOME",
        "fathom init",
        "fathom run",
    ]

    for term in forbidden_terms:
        if term.lower() in prompt_lower:
            errors.append(f"prompt contains '{term}'")

    # S3 must not contain the word "fathom" at all
    if scenario.name == "unnamed-discovery" and "fathom" in prompt_lower:
        errors.append("S3 prompt must not contain the word 'fathom'")

    return errors


# ============================================================================
# Stream parsing
# ============================================================================


def parse_stream_lines(lines: Sequence[str]) -> list[dict[str, Any]]:
    """Parse stream-json lines, tolerating malformed ones."""
    events: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                events.append(obj)
        except (json.JSONDecodeError, ValueError):
            pass
    return events


def classify_tool_use(tool_use: dict[str, Any], input_: dict[str, Any]) -> tuple[str, str | None]:
    """Classify a tool use as a fathom surface.

    Returns (surface_type, cli_subcommand).
    Surface types: "skill", "command", "mcp", "cli", "docs", or "other".
    """
    name = tool_use.get("name", "")

    # MCP tool
    if name.startswith("mcp__plugin_fathom_fathom__"):
        return "mcp", None

    # Skill tool with fathom skill
    if name == "Skill":
        skill = input_.get("skill", "")
        if isinstance(skill, str) and skill.startswith("fathom"):
            return "skill", None
        return "other", None

    # SlashCommand or fathom:* skill in SlashCommand
    if name == "SlashCommand":
        command = input_.get("command", "")
        if isinstance(command, str) and (
            command.startswith("/fathom:") or command.startswith("fathom:")
        ):
            cmd_name = command.split(":", 1)[-1].split()[0]
            return "command", cmd_name
        return "other", None

    # Bash with fathom CLI
    if name == "Bash":
        command = input_.get("command", "")
        if isinstance(command, str) and (
            "python -m fathom" in command or " fathom " in f" {command} "
        ):
            # Extract subcommand
            parts = command.split()
            for i, part in enumerate(parts):
                if "fathom" in part:
                    subcommand = parts[i + 1] if i + 1 < len(parts) else None
                    return "cli", subcommand
        return "other", None

    # Read of fathom docs
    if name == "Read":
        file_path = input_.get("file_path", "")
        if isinstance(file_path, str) and (
            "fathom" in file_path or "skills/fathom-eval" in file_path
        ):
            return "docs", None
        return "other", None

    return "other", None


def analyze_stream(transcript_path: pathlib.Path) -> StreamAnalysis:
    """Analyze a stream-json transcript."""
    lines = transcript_path.read_text(encoding="utf-8").splitlines()
    events = parse_stream_lines(lines)

    # Init event
    init_event: dict[str, Any] | None = None
    for event in events:
        if event.get("type") == "system" and event.get("subtype") == "init":
            init_event = event
            break

    model = None
    init_tools = []
    init_skills = []
    init_mcp_servers = []
    init_plugins = []
    fathom_mcp_connected = False
    fathom_skill_visible = False
    fathom_commands_visible = False

    if init_event:
        model = init_event.get("model")
        init_tools = init_event.get("tools", []) or []
        init_skills = init_event.get("skills", []) or []
        init_mcp_servers = init_event.get("mcp_servers", []) or []
        init_plugins = init_event.get("plugins", []) or []

        # Check fathom visibility
        for server in init_mcp_servers:
            if server.get("name") == "fathom" and server.get("status") == "connected":
                fathom_mcp_connected = True

        for skill in init_skills:
            if isinstance(skill, str) and skill.startswith("fathom"):
                fathom_skill_visible = True

        # Slash commands are harder to check from init (they're not listed), so we'll
        # check from tool uses later

    # Tool uses
    tool_uses_list: list[ToolUse] = []
    tool_uses_by_id: dict[str | None, dict[str, Any]] = {}

    assistant_content_index = 0
    for event in events:
        if event.get("type") == "assistant":
            content = event.get("message", {}).get("content", []) or []
            for block in content:
                if block.get("type") == "tool_use":
                    tool_use_id = block.get("id")
                    tool_use_name = block.get("name", "")
                    tool_use_input = block.get("input", {})

                    surface, cli_subcmd = classify_tool_use({"name": tool_use_name}, tool_use_input)

                    if surface == "command" and tool_use_name == "SlashCommand":
                        fathom_commands_visible = True

                    use = ToolUse(
                        index=assistant_content_index,
                        id=tool_use_id,
                        name=tool_use_name,
                        surface=surface,
                        cli_subcommand=cli_subcmd,
                    )
                    tool_uses_list.append(use)
                    tool_uses_by_id[tool_use_id] = {
                        "index": assistant_content_index,
                        "name": tool_use_name,
                        "surface": surface,
                        "cli_subcommand": cli_subcmd,
                    }
                    assistant_content_index += 1

    # Tool results
    tool_results_list: list[ToolResult] = []
    fathom_surface_errors: list[str] = []

    for event in events:
        if event.get("type") == "user":
            content = event.get("message", {}).get("content", []) or []
            for block in content:
                if block.get("type") == "tool_result":
                    tool_use_id = block.get("tool_use_id")
                    is_error = bool(block.get("is_error"))
                    content_text = block.get("content")
                    if isinstance(content_text, str):
                        text = content_text
                    else:
                        text = json.dumps(content_text, ensure_ascii=False)

                    result = ToolResult(
                        tool_use_id=tool_use_id,
                        is_error=is_error,
                        text=text,
                    )
                    tool_results_list.append(result)

                    # Check if this is a fathom surface error
                    if tool_use_id in tool_uses_by_id and is_error:
                        use_info = tool_uses_by_id[tool_use_id]
                        if use_info["surface"] != "other":
                            error_excerpt = text[:300]
                            fathom_surface_errors.append(error_excerpt)

    # Count fathom surface uses
    fathom_surface_use_count = sum(1 for use in tool_uses_list if use.surface != "other")
    first_fathom_use_index = None
    for use in tool_uses_list:
        if use.surface != "other":
            first_fathom_use_index = use.index
            break

    # Result event
    num_turns = 0
    total_cost_usd = 0.0
    duration_ms = 0
    is_error = False
    result_text = ""

    for event in events:
        if event.get("type") == "result":
            num_turns = event.get("num_turns", 0)
            total_cost_usd = event.get("total_cost_usd", 0.0)
            duration_ms = event.get("duration_ms", 0)
            is_error = event.get("is_error", False)
            result_text = event.get("result", "")

    malformed_lines = len(lines) - len(events)

    return StreamAnalysis(
        model=model,
        init_tools=init_tools,
        init_skills=init_skills,
        init_mcp_servers=init_mcp_servers,
        init_plugins=init_plugins,
        fathom_mcp_connected=fathom_mcp_connected,
        fathom_skill_visible=fathom_skill_visible,
        fathom_commands_visible=fathom_commands_visible,
        tool_uses=tool_uses_list,
        tool_results=tool_results_list,
        fathom_surface_errors=fathom_surface_errors,
        fathom_surface_use_count=fathom_surface_use_count,
        first_fathom_use_index=first_fathom_use_index,
        num_turns=num_turns,
        total_cost_usd=total_cost_usd,
        duration_ms=duration_ms,
        is_error=is_error,
        result_text=result_text,
        malformed_lines=malformed_lines,
    )


# ============================================================================
# Ground truth checks
# ============================================================================


def find_ledger_files(workspace: pathlib.Path) -> list[pathlib.Path]:
    """Find ledger files in the workspace."""
    ledger_dir = workspace / "data" / "ledger"
    if not ledger_dir.exists():
        return []
    return sorted(ledger_dir.glob("*.jsonl"))


def check_s1_no_spend(workspace: pathlib.Path) -> tuple[bool, str]:
    """S1: No new or modified files in ledgers."""
    clone_path = workspace / "data"
    if not clone_path.exists():
        return False, "clone directory not found"

    # Check git status, ignoring report/ and .fathom/
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=clone_path,
            capture_output=True,
            text=True,
            check=True,
        )
        status = result.stdout

        # Filter out report/ and .fathom/
        relevant_changes = [
            line
            for line in status.splitlines()
            if not line.strip().startswith("??")
            or ("report/" not in line and ".fathom/" not in line)
        ]

        if relevant_changes:
            return False, f"unexpected ledger changes: {relevant_changes}"
        return True, "ledgers unchanged"
    except subprocess.CalledProcessError as exc:
        return False, f"git status failed: {exc}"


def check_s2_bank_structure(workspace: pathlib.Path, budget_usd: float) -> tuple[bool, str]:
    """S2: Bank structure, ledger, and cost constraints."""
    errors: list[str] = []

    # Check fathom.toml with [data_root]
    fathom_toml = workspace / "fathom.toml"
    if not fathom_toml.exists():
        errors.append("fathom.toml not found")
    else:
        content = fathom_toml.read_text()
        if "[data_root]" not in content:
            errors.append("fathom.toml missing [data_root]")

    # Check bank directory structure
    tasks_dir = workspace / "tasks"
    if not tasks_dir.exists():
        errors.append("tasks/ not found")
    else:
        # Find a bank directory (any subdirectory with bank.toml)
        bank_dirs = list(tasks_dir.glob("*/bank.toml"))
        if not bank_dirs:
            errors.append("no bank.toml found in tasks/")
        else:
            bank_path = bank_dirs[0].parent
            # Check for at least one task
            task_tomls = list(bank_path.glob("*/task.toml"))
            if not task_tomls:
                errors.append(f"no tasks in bank {bank_path.name}")
            else:
                # Check for verifier
                for task_toml in task_tomls:
                    verifier = task_toml.parent / "verify.py"
                    if not verifier.exists():
                        errors.append(f"no verify.py for task {task_toml.parent.name}")

    # Check for arm files
    scenarios_dir = workspace / "scenarios"
    if not scenarios_dir.exists():
        errors.append("scenarios/ not found")
    else:
        arm_files = list(scenarios_dir.glob("*.toml"))
        if len(arm_files) < 2:
            errors.append(f"found {len(arm_files)} arm files, need >= 2")

    # Check ledger structure and cost
    ledger_dir = workspace / "ledger"
    if not ledger_dir.exists():
        errors.append("ledger/ not found")
    else:
        ledger_files = list(ledger_dir.glob("*.jsonl"))
        if not ledger_files:
            errors.append("no ledger files found")
        else:
            completed_trials = 0
            distinct_configs = set()
            total_cost = 0.0

            for ledger_file in ledger_files:
                for line in ledger_file.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        if row.get("status") == "completed":
                            completed_trials += 1
                            config_hash = row.get("config_hash")
                            if config_hash:
                                distinct_configs.add(config_hash)
                            cost = row.get("cost_usd_est", 0.0)
                            if isinstance(cost, (int, float)):
                                total_cost += cost
                    except json.JSONDecodeError:
                        pass

            if completed_trials < 2:
                errors.append(f"found {completed_trials} completed trials, need >= 2")
            if len(distinct_configs) < 2:
                errors.append(f"found {len(distinct_configs)} distinct configs, need >= 2")
            if total_cost > budget_usd * 1.5:
                errors.append(f"cost ${total_cost:.2f} exceeds budget ${budget_usd * 1.5:.2f}")

    if errors:
        return False, "; ".join(errors)
    return True, "bank structure and cost valid"


def check_s2_reconcile(workspace: pathlib.Path) -> tuple[bool, str]:
    """S2: fathom reconcile passes."""
    try:
        env = os.environ.copy()
        env["FATHOM_HOME"] = str(workspace)
        result = subprocess.run(
            ["python", "-m", "fathom", "reconcile"],
            cwd=workspace,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        if result.returncode == 0:
            return True, "reconcile passed"
        return False, f"reconcile failed with exit {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "reconcile timed out"
    except Exception as exc:
        return False, f"reconcile error: {exc}"


def check_s2_scorecard(workspace: pathlib.Path) -> tuple[bool, str]:
    """S2: Rendered scorecard exists."""
    scorecards = list(workspace.glob("report/scorecard-*.md"))
    if scorecards:
        return True, f"scorecard found: {scorecards[0].name}"
    return False, "no scorecard found in report/"


# ============================================================================
# Run a scenario
# ============================================================================


def run_scenario(
    scenario: ScenarioConfig,
    workspace: pathlib.Path,
    data_root: pathlib.Path,
    model: str = "sonnet",
    plugin_dir: str | None = None,
    timeout_s: int = 1800,
) -> Verdict:
    """Run a single scenario."""
    start_time = time.time()

    # Setup workspace
    ws_path, env_overrides = setup_workspace(workspace, scenario, data_root)
    cwd = ws_path

    # Guard prompt
    prompt_guard_errors = guard_prompt(scenario)

    # Build allowed/disallowed tool lists
    allowed_tools = ",".join(scenario.tools_allowed)
    disallowed_tools = ",".join(scenario.tools_disallowed)

    # Build claude command
    budget = 0.2 if not scenario.allow_spend else scenario.budget_usd
    cmd = [
        "claude",
        "-p",
        scenario.prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        "--max-budget-usd",
        str(budget),
        "--permission-mode",
        "acceptEdits",
        "--no-session-persistence",
        "--allowedTools",
        allowed_tools,
        "--disallowedTools",
        disallowed_tools,
    ]

    if plugin_dir:
        cmd.extend(["--plugin-dir", plugin_dir])

    # Prepare environment
    spawn_env = os.environ.copy()
    # Remove fathom-related and claudecode variables
    for key in list(spawn_env.keys()):
        if key.startswith("FATHOM_") or key in ["CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"]:
            del spawn_env[key]
    # Set scenario-specific vars
    spawn_env.update(env_overrides)

    # Capture streams
    transcript_path = ws_path / "transcript.jsonl"
    stderr_path = ws_path / "stderr.txt"

    # Run the spawn
    stderr_text = ""
    try:
        with (
            open(transcript_path, "w", encoding="utf-8") as transcript_file,
            open(stderr_path, "w", encoding="utf-8") as stderr_file,
        ):
            subprocess.run(
                cmd,
                cwd=cwd,
                stdout=transcript_file,
                stderr=stderr_file,
                env=spawn_env,
                timeout=timeout_s,
                text=True,
            )
        with open(stderr_path, encoding="utf-8") as f:
            stderr_text = f.read()
    except subprocess.TimeoutExpired:
        stderr_text = f"Process killed after {timeout_s}s timeout"
    except Exception as exc:
        stderr_text = str(exc)

    # Analyze stream
    stream_analysis = None
    if transcript_path.exists():
        stream_analysis = analyze_stream(transcript_path)

    duration_s = time.time() - start_time
    cost_usd = stream_analysis.total_cost_usd if stream_analysis else 0.0

    # Build checks
    checks: list[Check] = []

    if prompt_guard_errors:
        checks.append(
            Check(name="prompt_guard", passed=False, evidence="; ".join(prompt_guard_errors))
        )
    else:
        checks.append(
            Check(name="prompt_guard", passed=True, evidence="no forbidden terms in prompt")
        )

    if stream_analysis:
        checks.append(
            Check(
                name="visibility",
                passed=stream_analysis.fathom_mcp_connected
                and stream_analysis.fathom_skill_visible,
                evidence=(
                    f"mcp_connected={stream_analysis.fathom_mcp_connected}, "
                    f"skill_visible={stream_analysis.fathom_skill_visible}"
                ),
            )
        )
    else:
        checks.append(Check(name="visibility", passed=False, evidence="no stream analysis"))

    # Scenario-specific checks
    if scenario.name == "existing-data":
        check_ok, evidence = check_s1_no_spend(ws_path)
        checks.append(Check(name="no_spend", passed=check_ok, evidence=evidence))

    elif scenario.name == "from-scratch":
        check_ok, evidence = check_s2_bank_structure(ws_path, scenario.budget_usd)
        checks.append(Check(name="bank_structure", passed=check_ok, evidence=evidence))

        check_ok, evidence = check_s2_reconcile(ws_path)
        checks.append(Check(name="reconcile", passed=check_ok, evidence=evidence))

        check_ok, evidence = check_s2_scorecard(ws_path)
        checks.append(Check(name="scorecard", passed=check_ok, evidence=evidence))

    elif scenario.name == "unnamed-discovery":
        check_ok, evidence = check_s1_no_spend(ws_path)
        checks.append(Check(name="no_spend", passed=check_ok, evidence=evidence))

        if stream_analysis:
            checks.append(
                Check(
                    name="fathom_surface_used",
                    passed=stream_analysis.fathom_surface_use_count > 0,
                    evidence=f"{stream_analysis.fathom_surface_use_count} fathom surface uses",
                )
            )

    # Build surfaces used list
    surfaces_used: list[str] = []
    if stream_analysis:
        for use in stream_analysis.tool_uses:
            if use.surface != "other" and use.surface not in surfaces_used:
                surfaces_used.append(use.surface)

    first_fathom_idx = None
    if stream_analysis:
        first_fathom_idx = stream_analysis.first_fathom_use_index

    return Verdict(
        scenario_name=scenario.name,
        checks=checks,
        surfaces_used=surfaces_used,
        first_fathom_use_index=first_fathom_idx,
        stream_analysis=stream_analysis,
        workspace_path=ws_path,
        cost_usd_est=cost_usd,
        duration_s=duration_s,
        stderr_text=stderr_text,
    )


# ============================================================================
# Scenario loading
# ============================================================================


def load_scenarios_toml(toml_path: pathlib.Path) -> dict[str, ScenarioConfig]:
    """Load scenarios from a TOML file."""
    import tomllib

    content = toml_path.read_text(encoding="utf-8")
    data = tomllib.loads(content)

    scenarios: dict[str, ScenarioConfig] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            scenarios[key] = ScenarioConfig(
                name=value.get("name", key),
                prompt=value.get("prompt", ""),
                workspace_kind=value.get("workspace_kind", "empty"),
                allow_spend=value.get("allow_spend", False),
                budget_usd=value.get("budget_usd", 0.0),
                tools_allowed=value.get("tools_allowed", []),
                tools_disallowed=value.get("tools_disallowed", []),
                timeout_s=value.get("timeout_s", 1800),
            )
    return scenarios


# ============================================================================
# Main
# ============================================================================


def main(argv: Sequence[str] | None = None) -> int:
    """Run the acceptance test harness."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--scenarios",
        default="s1_existing_data,s2_from_scratch,s3_unnamed_discovery",
        help="comma-separated scenario keys to run (default: all)",
    )
    parser.add_argument("--model", default="sonnet", help="Claude model (default: sonnet)")
    parser.add_argument(
        "--data-root",
        type=pathlib.Path,
        default=None,
        help="data root for S1/S3 (default: env FATHOM_HOME or error)",
    )
    parser.add_argument("--out", type=pathlib.Path, default=None, help="output directory")
    parser.add_argument(
        "--budget-usd", type=float, default=3.0, help="budget for all spawns (default: $3)"
    )
    parser.add_argument("--timeout-s", type=int, default=1800, help="timeout per spawn")
    parser.add_argument("--plugin-dir", default=None, help="development plugin directory")
    parser.add_argument("--dry-run", action="store_true", help="prepare only, do not spawn")
    parser.add_argument("--preflight-only", action="store_true", help="spawn one trivial session")

    args = parser.parse_args(argv)

    # Resolve data root
    data_root = args.data_root
    if not data_root:
        data_root_env = os.environ.get("FATHOM_HOME")
        if data_root_env:
            data_root = pathlib.Path(data_root_env)

    if not data_root or not (data_root / "fathom.toml").exists():
        print("Error: no data root found; set --data-root or FATHOM_HOME", file=sys.stderr)
        return 3

    # Verify it's not an engine checkout
    if (data_root / ".claude-plugin" / "plugin.json").exists():
        print(
            "Error: data root appears to be an engine checkout; use a separate data root",
            file=sys.stderr,
        )
        return 2

    # Resolve output directory
    out_dir = args.out
    if not out_dir:
        run_id = str(uuid.uuid4())[:8]
        out_dir = pathlib.Path(tempfile.gettempdir()) / "fathom-agent-acceptance" / run_id

    out_dir.mkdir(parents=True, exist_ok=True)

    # Load scenarios
    scenarios_file = pathlib.Path(__file__).parent / "agent_acceptance_scenarios.toml"
    if not scenarios_file.exists():
        print(f"Error: scenarios file not found: {scenarios_file}", file=sys.stderr)
        return 3

    all_scenarios = load_scenarios_toml(scenarios_file)
    scenario_keys = args.scenarios.split(",")
    scenarios_to_run = {k: all_scenarios[k] for k in scenario_keys if k in all_scenarios}

    if not scenarios_to_run:
        print(f"Error: no valid scenarios in {scenario_keys}", file=sys.stderr)
        return 3

    # Dry run
    if args.dry_run:
        for key, scenario in scenarios_to_run.items():
            ws = out_dir / key
            ws_path, env_overrides = setup_workspace(ws, scenario, data_root)
            print(f"\n--- {scenario.name} ---")
            print(f"Workspace: {ws_path}")
            print(f"Env overrides: {env_overrides}")
            # Print the exact command that would run
            allowed = ",".join(scenario.tools_allowed)
            disallowed = ",".join(scenario.tools_disallowed)
            budget = 0.2 if not scenario.allow_spend else scenario.budget_usd
            cmd = [
                "claude",
                "-p",
                scenario.prompt,
                "--output-format",
                "stream-json",
                "--verbose",
                "--model",
                args.model,
                "--max-budget-usd",
                str(budget),
                "--permission-mode",
                "acceptEdits",
                "--no-session-persistence",
                "--allowedTools",
                allowed,
                "--disallowedTools",
                disallowed,
            ]
            print(f"Command: {' '.join(cmd)}")
        return 0

    # Preflight only
    if args.preflight_only:
        # Run a trivial session
        trivial_scenario = ScenarioConfig(
            name="preflight",
            prompt="Reply with the word ready.",
            workspace_kind="empty",
            allow_spend=False,
            budget_usd=0.2,
            tools_allowed=["Bash", "Read", "Write"],
            tools_disallowed=[],
            timeout_s=300,
        )
        ws = out_dir / "preflight"
        verdict = run_scenario(
            trivial_scenario,
            ws,
            data_root,
            model=args.model,
            plugin_dir=args.plugin_dir,
            timeout_s=args.timeout_s,
        )
        mcp_status = (
            verdict.stream_analysis.fathom_mcp_connected if verdict.stream_analysis else "N/A"
        )
        print(f"Preflight visibility: mcp={mcp_status}")
        if verdict.stream_analysis and not verdict.stream_analysis.fathom_mcp_connected:
            print("Environment failure: fathom MCP not connected", file=sys.stderr)
            return 2
        return 0

    # Run all scenarios
    verdicts: list[Verdict] = []
    for key, scenario in scenarios_to_run.items():
        ws = out_dir / key
        verdict = run_scenario(
            scenario,
            ws,
            data_root,
            model=args.model,
            plugin_dir=args.plugin_dir,
            timeout_s=args.timeout_s,
        )
        verdicts.append(verdict)

        # Save verdict
        verdict_file = ws / "verdict.json"
        verdict_data = {
            "scenario_name": verdict.scenario_name,
            "passed": verdict.passed(),
            "checks": [asdict(c) for c in verdict.checks],
            "surfaces_used": verdict.surfaces_used,
            "first_fathom_use_index": verdict.first_fathom_use_index,
            "workspace_path": str(verdict.workspace_path),
            "cost_usd_est": verdict.cost_usd_est,
            "duration_s": verdict.duration_s,
        }
        verdict_file.write_text(json.dumps(verdict_data, indent=2), encoding="utf-8")

    # Generate report
    report_path = out_dir / "report.md"
    report_lines = [
        "# Acceptance Test Report",
        "",
        "| Scenario | Passed | Cost | Duration |",
        "|----------|--------|------|----------|",
    ]

    for verdict in verdicts:
        passed_str = "✓" if verdict.passed() else "✗"
        cost_str = f"${verdict.cost_usd_est:.2f}"
        duration_str = f"{verdict.duration_s:.0f}s"
        report_lines.append(
            f"| {verdict.scenario_name} | {passed_str} | {cost_str} | {duration_str} |"
        )

    report_lines.extend(
        [
            "",
            "## Scenario Details",
            "",
        ]
    )

    for verdict in verdicts:
        report_lines.extend(
            [
                f"### {verdict.scenario_name}",
                "",
                f"Workspace: `{verdict.workspace_path}`",
                "",
                "**Checks:**",
                "",
            ]
        )
        for check in verdict.checks:
            status = "✓" if check.passed else "✗"
            report_lines.append(f"- {status} {check.name}: {check.evidence}")

        report_lines.extend(
            [
                "",
                f"Surfaces used: {', '.join(verdict.surfaces_used) or 'none'}",
                f"Cost: ${verdict.cost_usd_est:.2f}, Duration: {verdict.duration_s:.0f}s",
                "",
            ]
        )

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Report: {report_path}")
    print(f"Workspaces: {out_dir}")

    # Exit code
    all_passed = all(v.passed() for v in verdicts)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
