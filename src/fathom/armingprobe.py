"""The live probe behind :mod:`fathom.arming` — one cheap spawn per treatment arm.

Separated from :mod:`fathom.arming` for the same reason ``smoke.py`` splits its
assertions from its probes: the assertions are pure and unit-tested against
recorded observations, while this module performs the real I/O and is exercised
by ``fathom verify-arming`` / ``fathom smoke``.

What one probe spawn costs: the arm's own mount, allow-list, settings and env,
carrying a one-turn "reply ok" prompt on the cheapest model at low effort with a
$0.20 per-spawn cap — a fraction of a cent, against the ~$2.68 of armed-arm spend
a single undetected unarmed arm has already burned for zero signal.

The probe deliberately uses the arm's OWN wiring rather than a representative
copy: the recorded defect was a mismatch between an allow-list and the tool names
a specific mount produces, which a stand-in mount cannot reproduce.  It does NOT
use the arm's model — everything observed here (the init event, the spawn env,
the config dir, the argv) is emitted before any model turn, so paying strong-tier
rates to read it would buy nothing.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Protocol

from fathom import streams
from fathom.adapters.base import ExitStatus
from fathom.arming import ArmingObservation, file_sha256
from fathom.scenario import ResolvedScenario, registry_tool_names

# Cheap defaults — the probe reads pre-turn events, so capability is irrelevant.
PROBE_MODEL = "claude-haiku-4-5"
PROBE_EFFORT = "low"
PROBE_TIMEOUT_S = 180.0
PROBE_MAX_BUDGET_USD = 0.20
PROBE_PROMPT = "Reply with the single word: ok."


class ArmingProbe(Protocol):
    """The seam ``fathom run`` / ``fathom smoke`` call to observe one arm."""

    def observe(self, scenario: ResolvedScenario) -> ArmingObservation:
        """Spawn once with *scenario*'s own arming and report what was observed."""
        ...


def _empty_observation(detail: str) -> ArmingObservation:
    return ArmingObservation(
        spawn_ok=False,
        init_present=False,
        plugins=(),
        skills=(),
        tools=(),
        mcp_servers=(),
        hooks_fired=(),
        successful_mcp_calls=(),
        denied_tools=(),
        argv=(),
        spawn_env={},
        config_dir_files=(),
        settings_sha=None,
        detail=detail,
    )


class RealArmingProbe:
    """Spawns for real.  One spawn per scenario, results memoised per config_hash.

    Memoisation is keyed on ``config_hash``, which is precisely the identity that
    determines arming: two scenarios sharing a hash share a mount, allow-list,
    settings body and env template, so a second spawn would observe the same
    thing at a second cost.
    """

    def __init__(
        self,
        *,
        model: str = PROBE_MODEL,
        effort: str = PROBE_EFFORT,
        real_config_dir: str | None = None,
        timeout_s: float = PROBE_TIMEOUT_S,
        max_budget_usd: float = PROBE_MAX_BUDGET_USD,
    ) -> None:
        self.model = model
        self.effort = effort
        self.real_config_dir = real_config_dir
        self.timeout_s = timeout_s
        self.max_budget_usd = max_budget_usd
        self._cache: dict[str, ArmingObservation] = {}

    def observe(self, scenario: ResolvedScenario) -> ArmingObservation:
        cached = self._cache.get(scenario.config_hash)
        if cached is None:
            cached = self._observe_uncached(scenario)
            self._cache[scenario.config_hash] = cached
        return cached

    def _observe_uncached(self, scenario: ResolvedScenario) -> ArmingObservation:
        from fathom.adapters.claude_cli import ClaudeCliRunner, _subprocess_spawn, cleanup_dir

        captured: dict[str, Any] = {"argv": (), "env": {}, "cfg_files": (), "settings_sha": None}
        stdout_parts: list[str] = []

        def _recording_spawn(argv, *, input, timeout, env, cwd):  # type: ignore[no-untyped-def]
            # Snapshot the spawn boundary BEFORE handing off: the isolated config
            # dir is alive only for the duration of the call, and its contents are
            # the only direct evidence that the arm's settings.json reached the
            # session rather than being silently dropped by a copy failure.
            captured["argv"] = tuple(str(a) for a in argv)
            captured["env"] = dict(env)
            config_dir = env.get("CLAUDE_CONFIG_DIR")
            if config_dir and os.path.isdir(config_dir):
                captured["cfg_files"] = tuple(sorted(os.listdir(config_dir)))
                settings = Path(config_dir) / "settings.json"
                if settings.is_file():
                    captured["settings_sha"] = file_sha256(settings)
            result = _subprocess_spawn(argv, input=input, timeout=timeout, env=env, cwd=cwd)
            stdout_parts.append(result.stdout or "")
            return result

        # Scenario-faithful wiring: the arm's own mount, allow-list, registry
        # restriction, injected context/settings and env template.  Only
        # model/effort/turns/budget differ.
        runner = ClaudeCliRunner(
            allowed_tools=scenario.tools.allowed,
            disallowed_tools=scenario.tools.disallowed,
            registry_tools=registry_tool_names(scenario.tools),
            real_config_dir=self.real_config_dir,
            append_system_prompt_file=scenario.context.inject,
            plugin_dirs=scenario.plugins.mount,
            settings_file=scenario.settings.inject,
            max_attempts=1,
            default_max_turns=1,
            default_max_budget_usd=self.max_budget_usd,
            default_timeout_s=self.timeout_s,
            stream=True,
            spawn=_recording_spawn,
        )
        probe_scenario = _probe_scenario(scenario, self.model, self.effort, self.timeout_s)
        ws = Path(tempfile.mkdtemp(prefix="fathom-arming-"))
        try:
            record = runner.execute(PROBE_PROMPT, ws, probe_scenario)
        except Exception as exc:  # noqa: BLE001 - a probe crash is an arming failure, reported
            return _empty_observation(f"{type(exc).__name__}: {exc}")
        finally:
            cleanup_dir(str(ws))

        events = streams.parse_events("".join(stdout_parts).splitlines())
        init = streams.find_init(events)
        if record.status is ExitStatus.INFRASTRUCTURE:
            return _empty_observation(
                f"probe spawn returned INFRASTRUCTURE: {(record.result_text or '')[:160]}"
            )
        return ArmingObservation(
            spawn_ok=record.status is ExitStatus.OK,
            init_present=init is not None,
            plugins=tuple(streams.init_plugins(events)),
            skills=tuple(streams.init_skills(events)),
            tools=tuple(streams.init_tools(events)),
            mcp_servers=tuple(streams.init_mcp_servers(events)),
            hooks_fired=tuple(streams.hook_names(events)),
            successful_mcp_calls=tuple(streams.successful_mcp_calls(events)),
            denied_tools=tuple(streams.permission_denied_tools(events)),
            argv=captured["argv"],
            spawn_env=captured["env"],
            config_dir_files=captured["cfg_files"],
            settings_sha=captured["settings_sha"],
            detail=f"status={record.status.value} turns={record.num_turns}",
        )


def _probe_scenario(
    scenario: ResolvedScenario, model: str, effort: str, timeout_s: float
) -> ResolvedScenario:
    """A copy of *scenario* at probe model/effort/timeout, arming untouched."""
    import dataclasses

    from fathom.scenario import LimitsOverride

    return dataclasses.replace(
        scenario,
        model=model,
        effort=effort,
        limits=LimitsOverride(trial_timeout_s=int(timeout_s)),
    )
