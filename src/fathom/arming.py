"""Per-scenario arming VERIFICATION — proof a treatment arm is actually armed.

fathom used to validate *declarations*: the inject file exists, the mount dir is
non-empty.  Nothing checked that the treatment reached the spawn and functioned.
An entirely unarmed arm therefore scored 9/9 (100%) with ``smoke`` 8/8, a clean
plan, 18/18 completed trials and ``Infra Errors: 0`` — about $2.68 of armed-arm
spend that bought no signal, and a null result that four sibling backlogs were
ready to retire shipped surfaces on.

The rule this module enforces: **a declared arming axis must be observed live, or
the run does not start.**  Nothing here infers arming from the absence of
evidence; an axis that cannot be observed reports ``present`` (the treatment
demonstrably reached the spawn boundary) rather than ``verified``, and an axis
that was expected to announce itself and did not is a hard FAIL.

Five axes, each with its own live observation:

===========  ================================================================
``tools``    with ``[tools] registry = "allowed"``, ``--tools`` is in the real
             argv naming the bare allow-list, and the init event registers no
             built-in tool outside it (the iteration-1 multiagent review: 30
             tools registered against a 7-name allow-list, PowerShell calls
             in the streams — pre-approval removes nothing)
``plugins``  every declared mount appears in the init event's ``plugins``
             array; any MCP server the mount serves is healthy AND at least
             one of its registered ``mcp__*`` tools is permitted by the arm's
             own allow-list (the serena-nav defect: 23 tools registered,
             every one denied, because the tools are named
             ``mcp__plugin_<plugin>_<server>__<tool>`` and the allow-list
             said ``mcp__serena``)
``settings`` the arm's ``settings.json`` is present in the live spawn's
             isolated config dir with a matching sha256, and a declared
             ``SessionStart`` / ``UserPromptSubmit`` hook actually fired
``env``      each declared variable is present and non-empty in the real
             spawn environment, with no ``${...}`` template left unsubstituted
``context``  ``--append-system-prompt-file`` is in the real argv and points at
             the declared, non-empty body
===========  ================================================================

Pure functions over an :class:`ArmingObservation`; the probe that produces the
observation lives in :mod:`fathom.armingprobe` so this module stays stdlib-only
and unit-testable without a spawn.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from fathom.scenario import ResolvedScenario, registry_tool_names
from fathom.streams import MCP_TOOL_PREFIX

# Axes whose treatment must be proven live before a paid matrix starts.
ARMING_AXES = ("tools", "plugins", "settings", "env", "context")

# Hook events that fire unprompted in any live spawn.  A settings arm declaring
# one of these has no excuse for silence, so silence is a FAIL.  Everything else
# (PreToolUse, PostToolUse, Stop) needs an action the probe's single no-tool turn
# does not perform, so those arms report `present`, never a green they did not earn.
SELF_FIRING_HOOK_EVENTS = ("SessionStart", "UserPromptSubmit")

# MCP server statuses that mean the server is usable.  Anything else — `failed`,
# `needs-auth`, a `pending` that never resolved — means the arm's tools are not there.
HEALTHY_MCP_STATUSES = ("connected", "ready", "ok")

_TEMPLATE_RE = re.compile(r"\$\{[^}]*\}")


@dataclasses.dataclass(frozen=True)
class ArmingCheck:
    """One assertion about one axis.

    ``level`` is ``verified`` when the treatment was observed doing its job and
    ``present`` when it was observed reaching the spawn but could not be provoked
    into acting.  Both are passes; the distinction is reported so a reader can see
    which half of the gate is load-bearing rather than assuming the strong one.
    """

    axis: str
    name: str
    ok: bool
    detail: str = ""
    level: str = "present"


@dataclasses.dataclass(frozen=True)
class ArmingObservation:
    """What one real probe spawn observed about a scenario's arming.

    Produced by :mod:`fathom.armingprobe` from a single cheap spawn carrying the
    scenario's OWN mount, allow-list, settings and env — a probe with different
    wiring would prove nothing about the arm.
    """

    spawn_ok: bool
    init_present: bool
    plugins: tuple[Mapping[str, Any], ...]
    skills: tuple[str, ...]
    tools: tuple[str, ...]
    mcp_servers: tuple[Mapping[str, Any], ...]
    hooks_fired: tuple[str, ...]
    successful_mcp_calls: tuple[str, ...]
    denied_tools: tuple[str, ...]
    argv: tuple[str, ...]
    spawn_env: Mapping[str, str]
    config_dir_files: tuple[str, ...]
    settings_sha: str | None
    detail: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def file_sha256(path: str | Path) -> str | None:
    """sha256 of *path*'s bytes, or None if it cannot be read."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _norm(path: str) -> str:
    """A comparable spelling of a filesystem path (case- and separator-insensitive).

    The init event echoes the mount path the CLI resolved, which on Windows may
    differ from the scenario's spelling in drive-letter case and separators.
    Comparing raw strings would report a correctly-mounted plugin as missing.
    """
    try:
        resolved = Path(path).resolve()
    except OSError:
        resolved = Path(path)
    return str(resolved).replace("\\", "/").rstrip("/").lower()


def plugin_name_of(mount_dir: str) -> str | None:
    """The plugin's declared name from ``<mount>/.claude-plugin/plugin.json``."""
    try:
        meta = json.loads(
            (Path(mount_dir) / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return None
    name = meta.get("name")
    return str(name) if name else None


def declared_axes(scenario: ResolvedScenario) -> tuple[str, ...]:
    """The arming axes *scenario* declares, in :data:`ARMING_AXES` order."""
    present = {
        "tools": registry_tool_names(scenario.tools) is not None,
        "plugins": bool(scenario.plugins.mount),
        "settings": bool(scenario.settings.inject),
        "env": bool(scenario.env.vars),
        "context": bool(scenario.context.inject),
    }
    return tuple(axis for axis in ARMING_AXES if present[axis])


def needs_verification(scenario: ResolvedScenario) -> bool:
    """True when *scenario* declares any treatment that must be proven live."""
    return bool(declared_axes(scenario))


def allowlist_permits(tool: str, allowed: Sequence[str], disallowed: Sequence[str] = ()) -> bool:
    """Would the headless permission layer let *tool* run under these lists?

    Segment-aware on purpose.  A rule matches a tool when it is the tool's exact
    name, when it is a ``__``-delimited PREFIX of it (``mcp__srv`` permits
    ``mcp__srv__call``), or when it carries a parenthesised specifier for the same
    base name (``Bash(python:*)`` permits ``Bash``).  It must NOT match on a bare
    string prefix: ``mcp__serena`` is a string prefix of nothing useful and is
    emphatically not a segment prefix of ``mcp__plugin_serena_serena__find_symbol``
    — treating it as one would bless the exact run this module exists to refuse.
    Under default-deny an empty allow-list permits nothing.
    """

    def _matches(rule: str, name: str) -> bool:
        base = rule.split("(", 1)[0].strip()
        if not base:
            return False
        return base == name or name.startswith(base + "__")

    if any(_matches(rule, tool) for rule in disallowed):
        return False
    return any(_matches(rule, tool) for rule in allowed)


def mcp_tools_in(tools: Sequence[str]) -> list[str]:
    """The ``mcp__*`` entries of a registered-tool list."""
    return [t for t in tools if t.startswith(MCP_TOOL_PREFIX)]


def server_tool_prefix(server_name: str) -> str:
    """The ``mcp__<slug>`` prefix the tools of *server_name* carry.

    The CLI slugifies a server's display name by collapsing every run of
    non-alphanumerics to a single underscore, so ``plugin:serena:serena`` serves
    ``mcp__plugin_serena_serena__*`` and the account-level ``claude.ai Context7``
    serves ``mcp__claude_ai_Context7__*``.  Attribution matters: the first live
    run of this gate failed three correctly-armed arms because ambient
    account-level connectors leak into the isolated spawn and register tools no
    arm asked for.  Charging those to an arm is a false positive, and a gate that
    cries wolf is how an operator learns to pass the override.
    """
    return MCP_TOOL_PREFIX + re.sub(r"[^A-Za-z0-9]+", "_", server_name).strip("_")


def tools_served_by(servers: Sequence[Mapping[str, Any]], tools: Sequence[str]) -> list[str]:
    """The entries of *tools* attributable to one of *servers*."""
    prefixes = tuple(server_tool_prefix(str(s.get("name", ""))) + "__" for s in servers)
    return [t for t in tools if t.startswith(prefixes)]


def _declared_hook_events(settings_path: str) -> list[str]:
    """Hook event kinds the arm's settings.json declares."""
    try:
        data = json.loads(Path(settings_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    hooks = data.get("hooks") if isinstance(data, dict) else None
    return sorted(str(k) for k in hooks) if isinstance(hooks, dict) else []


def _argv_value(argv: Sequence[str], flag: str) -> str | None:
    for i, tok in enumerate(argv):
        if tok == flag and i + 1 < len(argv):
            return argv[i + 1]
    return None


# ---------------------------------------------------------------------------
# Per-axis assertions
# ---------------------------------------------------------------------------


def registry_violations(observed_tools: Sequence[str], expected: Sequence[str]) -> list[str]:
    """Built-in tools the spawn registered that a restricted registry does not name.

    Pure.  ``mcp__*`` entries are excluded: ``--tools`` governs the built-in set,
    ambient account-level connectors register their own tools in every spawn, and
    the plugins axis already judges the ones an arm actually mounts.  Charging
    them here would fail a correctly restricted arm for a connector it never asked
    for — the false positive that trains an operator to pass the override.
    """
    allowed = set(expected)
    return [t for t in observed_tools if not t.startswith(MCP_TOOL_PREFIX) and t not in allowed]


def _check_tools(sc: ResolvedScenario, obs: ArmingObservation) -> list[ArmingCheck]:
    expected = registry_tool_names(sc.tools) or ()
    in_argv = _argv_value(obs.argv, "--tools")
    reached = in_argv is not None and in_argv == ",".join(expected)
    detail = f"argv_tools={in_argv!r} expected={','.join(expected)!r}"
    if in_argv is None:
        detail += " — --tools absent from the real argv; the registry was never restricted"
    elif not reached:
        detail += " — argv names a DIFFERENT registry than the arm declares"
    checks = [
        ArmingCheck(
            "tools",
            "registry restriction reaches the spawn argv",
            reached,
            detail,
        )
    ]
    if not reached:
        return checks

    extra = registry_violations(obs.tools, expected)
    ok = not extra
    detail = f"registered={len(obs.tools)} expected<={len(expected)}"
    if not ok:
        # Every offender by name: the list is bounded by the CLI's built-in set, and
        # a truncated one would hide exactly the tool the review saw called.
        detail += (
            f"; {len(extra)} registered tool(s) outside the arm's registry: "
            f"{', '.join(extra)} — the spawn still offers the model tools the arm "
            "does not name; pre-approval alone removes nothing"
        )
    checks.append(
        ArmingCheck(
            "tools",
            "init event registers only the arm's own tools",
            ok,
            detail,
            level="verified" if ok else "present",
        )
    )
    return checks


def _check_plugins(sc: ResolvedScenario, obs: ArmingObservation) -> list[ArmingCheck]:
    checks: list[ArmingCheck] = []

    registered_paths = {_norm(str(p.get("path", ""))) for p in obs.plugins if p.get("path")}
    registered_names = {str(p.get("name", "")) for p in obs.plugins if p.get("name")}

    missing: list[str] = []
    matched_names: list[str] = []
    for mount in sc.plugins.mount:
        name = plugin_name_of(mount)
        if _norm(mount) in registered_paths or (name and name in registered_names):
            if name:
                matched_names.append(name)
        else:
            missing.append(name or mount)

    checks.append(
        ArmingCheck(
            "plugins",
            "plugins registered in the spawn",
            not missing,
            (
                f"declared={len(sc.plugins.mount)} registered={sorted(registered_names)}"
                + (f" MISSING={missing}" if missing else "")
            ),
            level="verified" if not missing else "present",
        )
    )
    if missing:
        # Everything below reads the mount's tools; without a mount there are none.
        return checks

    # --- MCP servers the mounted plugins serve -----------------------------
    # Attribute by the `plugin:<plugin>:<server>` spelling the init event uses, so
    # ambient account-level connectors (routinely `pending` / `needs-auth`) are
    # never charged to an arm that did not ask for them.
    owned = [
        s
        for s in obs.mcp_servers
        if any(str(s.get("name", "")).startswith(f"plugin:{n}:") for n in matched_names)
    ]
    if owned:
        unhealthy = [
            f"{s.get('name')}={s.get('status')}"
            for s in owned
            if str(s.get("status", "")).lower() not in HEALTHY_MCP_STATUSES
        ]
        checks.append(
            ArmingCheck(
                "plugins",
                "plugin-served MCP servers are healthy",
                not unhealthy,
                f"servers={[s.get('name') for s in owned]}"
                + (f" UNHEALTHY={unhealthy}" if unhealthy else ""),
                level="verified" if not unhealthy else "present",
            )
        )

    # Only the tools the ARM's own servers serve. Ambient account-level connectors
    # register mcp__* tools in every spawn; default-deny already refuses them, and
    # they are no part of this arm's treatment.
    mcp_tools = tools_served_by(owned, obs.tools)
    if owned and not mcp_tools:
        checks.append(
            ArmingCheck(
                "plugins",
                "plugin-served MCP tools registered",
                False,
                f"servers={[s.get('name') for s in owned]} registered NO mcp__* tools — "
                f"the arm's tools are absent from the spawn "
                f"(ambient tools present: {mcp_tools_in(obs.tools)})",
            )
        )
        return checks

    if mcp_tools:
        permitted = [
            t for t in mcp_tools if allowlist_permits(t, sc.tools.allowed, sc.tools.disallowed)
        ]
        ok = bool(permitted)
        detail = f"registered={len(mcp_tools)} permitted={len(permitted)}"
        if not ok:
            # The serena-nav failure, named precisely enough to fix in one edit.
            detail += (
                f"; the allow-list {list(sc.tools.allowed)} permits NONE of them — e.g. "
                f"{mcp_tools[0]} is registered but every call would be denied. "
                f"Allow the server prefix, e.g. "
                f'"{mcp_tools[0].rsplit("__", 1)[0]}"'
            )
        checks.append(
            ArmingCheck(
                "plugins",
                "registered MCP tools are permitted by the arm's allow-list",
                ok,
                detail,
                level="verified" if ok else "present",
            )
        )

    if obs.denied_tools:
        checks.append(
            ArmingCheck(
                "plugins",
                "no tool call was refused during the probe",
                False,
                f"permission-denied during probe: {list(obs.denied_tools)}",
            )
        )
    return checks


def _check_settings(sc: ResolvedScenario, obs: ArmingObservation) -> list[ArmingCheck]:
    path = sc.settings.inject or ""
    expected = file_sha256(path)
    reached = "settings.json" in obs.config_dir_files and obs.settings_sha is not None
    matches = reached and expected is not None and obs.settings_sha == expected
    checks = [
        ArmingCheck(
            "settings",
            "arm settings.json reached the live spawn config dir",
            bool(matches),
            (
                f"config_dir={list(obs.config_dir_files)} "
                f"observed_sha={(obs.settings_sha or 'none')[:12]} "
                f"expected_sha={(expected or 'unreadable')[:12]}"
            ),
        )
    ]
    if not matches:
        return checks

    declared = _declared_hook_events(path)
    self_firing = [e for e in declared if e in SELF_FIRING_HOOK_EVENTS]
    if self_firing:
        ok = bool(obs.hooks_fired)
        checks.append(
            ArmingCheck(
                "settings",
                "declared session hook fired in the spawn",
                ok,
                f"declares={declared} fired={list(obs.hooks_fired)}"
                + ("" if ok else " — a SessionStart hook that never fires is not wired"),
                level="verified" if ok else "present",
            )
        )
    else:
        checks.append(
            ArmingCheck(
                "settings",
                "settings hooks declared (firing not provokable by the probe)",
                True,
                f"declares={declared or 'no hooks'}; the probe's single no-tool turn "
                "cannot provoke these, so this axis is PRESENT, not VERIFIED",
            )
        )
    return checks


def _check_env(sc: ResolvedScenario, obs: ArmingObservation) -> list[ArmingCheck]:
    missing: list[str] = []
    empty: list[str] = []
    unsubstituted: list[str] = []
    for name, _template in sc.env.vars:
        if name not in obs.spawn_env:
            missing.append(name)
            continue
        value = obs.spawn_env[name]
        if not value.strip():
            empty.append(name)
        elif _TEMPLATE_RE.search(value):
            unsubstituted.append(f"{name}={value}")

    problems = []
    if missing:
        problems.append(f"MISSING={missing}")
    if empty:
        problems.append(f"EMPTY={empty}")
    if unsubstituted:
        problems.append(f"UNSUBSTITUTED={unsubstituted}")
    ok = not problems
    return [
        ArmingCheck(
            "env",
            "declared env vars reach the spawn environment",
            ok,
            f"declared={[n for n, _ in sc.env.vars]}"
            + ("; " + "; ".join(problems) if problems else ""),
            level="verified" if ok else "present",
        )
    ]


def _check_context(sc: ResolvedScenario, obs: ArmingObservation) -> list[ArmingCheck]:
    declared = sc.context.inject or ""
    in_argv = _argv_value(obs.argv, "--append-system-prompt-file")
    same = in_argv is not None and _norm(in_argv) == _norm(declared)
    try:
        size = Path(declared).stat().st_size
    except OSError:
        size = -1
    ok = same and size > 0
    detail = f"argv_file={in_argv!r} declared={declared!r} body_bytes={size}"
    if in_argv is None:
        detail += " — --append-system-prompt-file absent from the real argv"
    elif not same:
        detail += " — argv points at a DIFFERENT file than the arm declares"
    elif size <= 0:
        detail += " — the injected body is empty or unreadable"
    return [
        ArmingCheck(
            "context",
            "injected context body reaches the spawn argv",
            ok,
            detail,
            level="verified" if ok else "present",
        )
    ]


_AXIS_CHECKERS = {
    "tools": _check_tools,
    "plugins": _check_plugins,
    "settings": _check_settings,
    "env": _check_env,
    "context": _check_context,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_arming(scenario: ResolvedScenario, observation: ArmingObservation) -> list[ArmingCheck]:
    """Every arming check *scenario* earns, given what the probe *observation* saw.

    Returns ``[]`` for an arm declaring no treatment axis — there is nothing to
    prove, and inventing a check for it would be the vacuous-gate failure mode
    this module exists to remove.
    """
    axes = declared_axes(scenario)
    if not axes:
        return []

    if not observation.spawn_ok:
        return [
            ArmingCheck(
                "probe",
                "arming probe spawn completed",
                False,
                f"probe spawn failed: {observation.detail or 'unknown error'} — "
                "arming is UNKNOWN, which is not the same as armed",
            )
        ]
    if not observation.init_present:
        return [
            ArmingCheck(
                "probe",
                "arming probe observed an init event",
                False,
                "no init event in the probe stream — nothing about this arm's "
                "configuration could be observed",
            )
        ]

    checks: list[ArmingCheck] = []
    for axis in axes:
        checks.extend(_AXIS_CHECKERS[axis](scenario, observation))
    return checks


def all_ok(checks: Sequence[ArmingCheck]) -> bool:
    """True when every check passed (vacuously true for an unarmed arm)."""
    return all(c.ok for c in checks)


def verify_all(scenarios: Sequence[ResolvedScenario], probe: Any) -> tuple[bool, str]:
    """Verify every arm that declares a treatment; return ``(ok, rendered report)``.

    Probes only the arms that declare an axis, so a matrix of plain arms costs
    nothing to gate.  A probe that raises is a FAILURE, never a skip: "the probe
    broke" and "the arm is armed" must never render the same.
    """
    lines: list[str] = []
    ok = True
    for sc in scenarios:
        if not needs_verification(sc):
            continue
        try:
            observation = probe.observe(sc)
            checks = verify_arming(sc, observation)
        except Exception as exc:  # noqa: BLE001 - a broken probe blocks the run
            checks = [
                ArmingCheck(
                    "probe",
                    "arming probe ran",
                    False,
                    f"{type(exc).__name__}: {exc}",
                )
            ]
        ok = ok and all_ok(checks)
        lines.append(render_checks(sc.name, checks))
    return ok, "\n".join(lines)


def render_checks(scenario_name: str, checks: Sequence[ArmingCheck]) -> str:
    """Human-readable block for one scenario's arming verdict."""
    if not checks:
        return f"  {scenario_name}: no arming axis declared — nothing to verify"
    lines = [f"  {scenario_name}:"]
    for c in checks:
        mark = f"PASS/{c.level}" if c.ok else "FAIL"
        lines.append(f"    [{mark}] ({c.axis}) {c.name}")
        if c.detail:
            lines.append(f"           {c.detail}")
    return "\n".join(lines)
