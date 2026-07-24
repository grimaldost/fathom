"""Scenario configuration parsing and resolution.

A ScenarioConfig is the raw TOML representation.  A ResolvedScenario adds
version pins recorded at resolution time: the exact model id as reported by
the CLI (fillable at run time), the tool repo git SHA (for source="repo"),
and the explicit tool invocation command.  config_hash is SHA-256 over the
canonicalized (sorted-keys JSON) resolved scenario including all pins.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Protocol


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ToolsConfig:
    source: str  # "none" | "repo"
    repo: str | None = None
    # Explicit spawn tool lists (spec §5: "explicit allow/disallow lists from
    # the scenario").  Under headless default-deny an empty allowlist means the
    # agent has NO tools — single-session arms must set `allowed` or they are
    # unarmed, not evaluated (root cause of the invalidated first matrix run).
    allowed: tuple[str, ...] = ()
    disallowed: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class LimitsOverride:
    """Per-scenario trial-limit overrides (strategy-aware timeouts)."""

    trial_timeout_s: int | None = None


@dataclasses.dataclass(frozen=True)
class ContextConfig:
    """Per-scenario injected system-prompt context (a skill body / nudge).

    ``inject`` is an absolute path to a file whose body is appended to the spawn's
    default system prompt via ``--append-system-prompt-file`` (the treatment arm).
    ``None`` means no injection (the control arm). The treatment being measured is
    the file's *content*, so its sha256 — not the path — enters ``config_hash``:
    editing the body forks longitudinal history; relocating the file does not.
    """

    inject: str | None = None


@dataclasses.dataclass(frozen=True)
class SettingsConfig:
    """Per-scenario Claude Code settings.json injected into the spawn's isolated
    config dir (the treatment arm).

    ``inject`` is an absolute path to a JSON file written verbatim as
    ``<CLAUDE_CONFIG_DIR>/settings.json`` at spawn time, so a *user-scope* hook
    (e.g. a PreToolUse command rewrite) is active for the arm — the one thing a
    ``[plugins]`` mount cannot deliver, because plugin hooks do not fire in
    headless ``claude -p`` while user-settings hooks do. ``None`` means no
    settings (the control arm). Like ``[context]``, the file's *content* (sha256)
    — not the path — enters ``config_hash``: editing the body forks longitudinal
    history; relocating the file does not. This is an EXPLICIT per-arm treatment,
    distinct from the user's real settings.json (which stays excluded from the
    isolated config, ADR-0004); the injected file is the arm's own declaration.
    """

    inject: str | None = None


@dataclasses.dataclass(frozen=True)
class PluginsConfig:
    """Per-scenario plugin mounts.

    ``mount`` is a tuple of absolute paths to plugin directories. Absent
    ``[plugins]`` and an empty ``mount`` list are the same effective config —
    neither adds a ``plugins`` key to the hash, so existing ledger resume keys
    are preserved (ADR-0002).
    """

    mount: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class GateConfig:
    """Per-scenario gate augmentation (harness-side oracle strengthening).

    ``extra`` is a tuple of shell commands the gated strategies run AFTER the
    task's own gate command, each from the workspace cwd; any non-zero exit is a
    red gate.  This is the scenario-level knob for "strong deterministic oracle"
    arms: the task, its fixtures, and its visible suite stay untouched -- only the
    HARNESS's gate gets stronger, so bare arms and the blind acceptance oracle are
    unaffected.  Lives on the scenario (not task.toml) so adding it can never
    silently fork the resume keys of existing task-level trials (ADR-0002).
    Commands enter ``config_hash`` verbatim; the content of a script a command
    points at does NOT -- version the scenario name when editing probe scripts.
    """

    extra: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class EnvConfig:
    """Per-scenario environment-variable overrides applied to the spawn.

    ``vars`` is a tuple of (name, value-template) pairs.  Values support
    ``${workspace}`` (the staged workspace path) and ``${VARNAME}`` (the spawn's
    inherited value of VARNAME — e.g. ``${PATH}`` to prepend) — both substituted
    at spawn time, NOT at parse/hash time, so the template (not the per-trial
    workspace path) is what enters ``config_hash``.  Absent ``[env]`` and an empty
    table are the same effective config — neither adds an ``env`` key to the hash,
    preserving existing resume keys (ADR-0002).  NON-SECRET config only (paths,
    modes); never a credential.
    """

    vars: tuple[tuple[str, str], ...] = ()


@dataclasses.dataclass(frozen=True)
class ScenarioConfig:
    """Raw scenario definition as parsed from TOML.  No resolution performed."""

    name: str
    adapter: str
    model: str
    strategy: str
    effort: str
    tools: ToolsConfig
    limits: LimitsOverride
    context: ContextConfig = dataclasses.field(default_factory=ContextConfig)
    settings: SettingsConfig = dataclasses.field(default_factory=SettingsConfig)
    plugins: PluginsConfig = dataclasses.field(default_factory=PluginsConfig)
    env: EnvConfig = dataclasses.field(default_factory=EnvConfig)
    gate: GateConfig = dataclasses.field(default_factory=GateConfig)


@dataclasses.dataclass(frozen=True)
class ResolvedScenario:
    """Scenario with all version pins filled in by a resolver.

    model_id is the exact model id as reported by the CLI; the field is
    present and typed but may be None if resolution is deferred to run time.
    config_hash covers every pin including tool_invocation_cmd.
    """

    name: str
    adapter: str
    model: str
    strategy: str
    effort: str
    tools: ToolsConfig
    limits: LimitsOverride
    model_id: str | None  # exact id as reported by the CLI; fillable at run time
    tool_repo_sha: str | None  # HEAD SHA of the tool repo (source="repo" only)
    tool_invocation_cmd: str | None  # e.g. "uv run --project <repo> convoy"
    config_hash: str  # SHA-256 over canonicalized resolved scenario
    context: ContextConfig = dataclasses.field(default_factory=ContextConfig)
    settings: SettingsConfig = dataclasses.field(default_factory=SettingsConfig)
    plugins: PluginsConfig = dataclasses.field(default_factory=PluginsConfig)
    env: EnvConfig = dataclasses.field(default_factory=EnvConfig)
    gate: GateConfig = dataclasses.field(default_factory=GateConfig)


# ---------------------------------------------------------------------------
# Resolver protocol — injectable; no real git/CLI calls in tests
# ---------------------------------------------------------------------------


class ScenarioResolver(Protocol):
    def resolve_model_id(self, model: str) -> str | None:
        """Return the exact model id that the CLI will report, or None to defer."""
        ...

    def resolve_tool_repo_sha(self, repo: str) -> str:
        """Return the HEAD git SHA of the tool repository."""
        ...

    def build_tool_invocation_cmd(self, repo: str) -> str:
        """Return the explicit invocation command, e.g. 'uv run --project <repo> convoy'."""
        ...

    def resolve_plugin_meta(self, plugin_dir: str) -> tuple[str, str, str]:
        """Return (name, version, tree_sha) for the plugin at plugin_dir.

        name and version come from .claude-plugin/plugin.json inside the dir;
        tree_sha is a sha256 over every file's relative path + contents under the
        dir — the filesystem is globbed, NOT git — minus a small skiplist
        (__pycache__/.venv/.git/…). So a stray untracked or editor-backup file
        inside the dir also forks the hash; keep a mounted plugin dir clean.
        """
        ...


# ---------------------------------------------------------------------------
# Hash computation
# ---------------------------------------------------------------------------


def resolve_repo_invocation_cmd(repo: str) -> str:
    """Freeze a ``source="repo"`` scenario's engine invocation to a cwd-independent command.

    The series engine runs with ``cwd = trial workspace`` (a temp dir), so a
    *relative* ``[tools].repo`` (e.g. ``../convoy``) baked verbatim into
    ``uv run --project <rel> convoy`` cannot resolve from there — the engine never
    starts, spawns no ``claude``, and the arm silently mis-scores (the regression
    the genericize-paths change introduced, caught by the smoke engine boundary).
    Resolve the repo to an absolute path at resolution time (fathom's cwd) and
    normalize to forward slashes so the string — which enters ``config_hash`` — is
    stable across path separators.  Shared by both real resolvers (cli.py,
    smoke.py) so they cannot drift.
    """
    abs_repo = str(Path(repo).resolve()).replace("\\", "/")
    return f"uv run --project {abs_repo} convoy"


def compute_config_hash(d: dict) -> str:
    """SHA-256 of the sorted-keys JSON serialization of *d*.

    Key order is irrelevant (sort_keys=True); every value change shifts the
    hash.  Accepts any JSON-serializable dict, including nested structures.
    """
    canonical = json.dumps(d, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _resolved_to_dict(
    *,
    name: str,
    adapter: str,
    model: str,
    strategy: str,
    effort: str,
    tools: ToolsConfig,
    limits: LimitsOverride,
    model_id: str | None,
    tool_repo_sha: str | None,
    tool_invocation_cmd: str | None,
    inject_set: bool = False,
    inject_sha: str | None = None,
    settings_set: bool = False,
    settings_sha: str | None = None,
    plugins_entries: list | None = None,
    env_vars: list | None = None,
    gate_extra: list | None = None,
) -> dict:
    """Canonical dict representation used for hashing and serialization.

    The ``context`` block is included only when ``inject`` is set (mirrors
    ``_tools_to_dict``'s conditional): an absent ``[context]`` and a present
    ``[context]`` with no ``inject`` are the same effective config, so the
    schema extension must not shift the hash of scenarios that never inject
    (committed ledgers' resume keys depend on it).

    The ``plugins`` block is included only when ``plugins_entries`` is a
    non-empty list, for the same reason: absent ``[plugins]`` and empty
    ``mount`` must not shift existing resume keys (ADR-0002).

    The ``settings`` block mirrors ``context`` exactly (conditional on
    ``settings_set``) and is keyed under its own name, so a body injected as
    settings never collides with the same body injected as context.
    """
    d = {
        "adapter": adapter,
        "effort": effort,
        "limits": {"trial_timeout_s": limits.trial_timeout_s},
        "model": model,
        "model_id": model_id,
        "name": name,
        "strategy": strategy,
        "tool_invocation_cmd": tool_invocation_cmd,
        "tool_repo_sha": tool_repo_sha,
        "tools": _tools_to_dict(tools),
    }
    if inject_set:
        d["context"] = {"inject_sha": inject_sha}
    if settings_set:
        d["settings"] = {"inject_sha": settings_sha}
    if plugins_entries:
        d["plugins"] = plugins_entries
    if env_vars:
        d["env"] = env_vars
    if gate_extra:
        # Absent [gate] and an empty extra list are the same effective config --
        # neither adds a key, so existing resume keys are preserved (ADR-0002).
        d["gate"] = {"extra": gate_extra}
    return d


def _tools_to_dict(tools: ToolsConfig) -> dict:
    """Hashable dict for the tools block.

    `allowed`/`disallowed` are included only when non-empty: an absent list and
    an empty list are the same effective config, so a schema extension must not
    shift the hash of scenarios that never set the field (resume keys of
    completed trials depend on it).
    """
    d: dict = {"repo": tools.repo, "source": tools.source}
    if tools.allowed:
        d["allowed"] = list(tools.allowed)
    if tools.disallowed:
        d["disallowed"] = list(tools.disallowed)
    return d


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_scenario(path: Path) -> ScenarioConfig:
    """Parse a scenario TOML file into a ScenarioConfig.

    No resolution is performed; no git or CLI calls are made.
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)

    tools_raw = data.get("tools", {})
    tools = ToolsConfig(
        source=tools_raw.get("source", "none"),
        repo=tools_raw.get("repo"),
        allowed=tuple(tools_raw.get("allowed", ())),
        disallowed=tuple(tools_raw.get("disallowed", ())),
    )

    limits_raw = data.get("limits", {})
    limits = LimitsOverride(
        trial_timeout_s=limits_raw.get("trial_timeout_s"),
    )

    context_raw = data.get("context", {})
    inject = context_raw.get("inject")
    if inject is not None:
        inject_path = Path(inject)
        if not inject_path.is_absolute():
            inject_path = path.parent / inject_path
        inject = str(inject_path.resolve())
    context = ContextConfig(inject=inject)

    settings_raw = data.get("settings", {})
    settings_inject = settings_raw.get("inject")
    if settings_inject is not None:
        settings_path = Path(settings_inject)
        if not settings_path.is_absolute():
            settings_path = path.parent / settings_path
        settings_inject = str(settings_path.resolve())
    settings = SettingsConfig(inject=settings_inject)

    plugins_raw = data.get("plugins", {})
    raw_mount = plugins_raw.get("mount", [])
    abs_mount = []
    for m in raw_mount:
        p = Path(m)
        if not p.is_absolute():
            p = path.parent / p
        abs_mount.append(str(p.resolve()))
    plugins = PluginsConfig(mount=tuple(abs_mount))

    env_raw = data.get("env", {})
    env = EnvConfig(vars=tuple(sorted((str(k), str(v)) for k, v in env_raw.items())))

    gate_raw = data.get("gate", {})
    gate = GateConfig(extra=tuple(str(c) for c in gate_raw.get("extra", ())))

    return ScenarioConfig(
        name=data["name"],
        adapter=data["adapter"],
        model=data["model"],
        strategy=data["strategy"],
        effort=data["effort"],
        tools=tools,
        limits=limits,
        context=context,
        settings=settings,
        plugins=plugins,
        env=env,
        gate=gate,
    )


def resolve_scenario(config: ScenarioConfig, resolver: ScenarioResolver) -> ResolvedScenario:
    """Resolve version pins for *config* using *resolver*.

    For source="repo" scenarios, calls the resolver to obtain the tool repo
    git SHA and construct the explicit invocation command (never a bare PATH
    lookup).  Computes config_hash over the full resolved representation.
    """
    model_id = resolver.resolve_model_id(config.model)

    tool_repo_sha: str | None = None
    tool_invocation_cmd: str | None = None
    if config.tools.source == "repo" and config.tools.repo:
        tool_repo_sha = resolver.resolve_tool_repo_sha(config.tools.repo)
        tool_invocation_cmd = resolver.build_tool_invocation_cmd(config.tools.repo)

    inject_sha: str | None = None
    if config.context.inject:
        try:
            inject_sha = hashlib.sha256(Path(config.context.inject).read_bytes()).hexdigest()
        except OSError:
            # Missing/unreadable: the CLI factory warns (K7) at run time. Discriminate by
            # path so two distinct-but-missing treatments don't collide into one ledger
            # bucket (fathom never lets longitudinal history silently fork).
            inject_sha = "<unreadable>:" + config.context.inject

    settings_sha: str | None = None
    if config.settings.inject:
        try:
            settings_sha = hashlib.sha256(Path(config.settings.inject).read_bytes()).hexdigest()
        except OSError:
            # Same discipline as context.inject: a missing settings file is discriminated
            # by path so two distinct-but-missing arms never share a ledger bucket.
            settings_sha = "<unreadable>:" + config.settings.inject

    plugins_entries: list | None = None
    if config.plugins.mount:
        plugins_entries = []
        for plugin_dir in config.plugins.mount:
            name, version, tree_sha = resolver.resolve_plugin_meta(plugin_dir)
            plugins_entries.append({"name": name, "tree_sha": tree_sha, "version": version})

    hashable = _resolved_to_dict(
        name=config.name,
        adapter=config.adapter,
        model=config.model,
        strategy=config.strategy,
        effort=config.effort,
        tools=config.tools,
        limits=config.limits,
        model_id=model_id,
        tool_repo_sha=tool_repo_sha,
        tool_invocation_cmd=tool_invocation_cmd,
        inject_set=bool(config.context.inject),
        inject_sha=inject_sha,
        settings_set=bool(config.settings.inject),
        settings_sha=settings_sha,
        plugins_entries=plugins_entries,
        env_vars=[list(p) for p in config.env.vars] or None,
        gate_extra=list(config.gate.extra) or None,
    )
    config_hash = compute_config_hash(hashable)

    return ResolvedScenario(
        name=config.name,
        adapter=config.adapter,
        model=config.model,
        strategy=config.strategy,
        effort=config.effort,
        tools=config.tools,
        limits=config.limits,
        model_id=model_id,
        tool_repo_sha=tool_repo_sha,
        tool_invocation_cmd=tool_invocation_cmd,
        config_hash=config_hash,
        context=config.context,
        settings=config.settings,
        plugins=config.plugins,
        env=config.env,
        gate=config.gate,
    )
