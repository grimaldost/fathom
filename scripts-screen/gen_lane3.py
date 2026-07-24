"""Generate Lane-3 scenario TOMLs (action-stream hook arms).

Two validated arms -- detector-nudge (5a+5b, PreToolUse) and retrospective-gate
(5e, Stop) -- on the C-present (c-*) and null banks, haiku-first. Each mounts the
craft plugins (constant baseline) PLUS its hook plugin, and passes the bank's
discipline via [env]. trajectory-judge (5d) and runtime-skill-search (5c) are
deferred (nested-model / MCP build cost; revisit if the static arms show signal).
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCEN = BASE / "scenarios"
HOOKS = BASE / "scenarios" / "screen-hooks"

CRAFT = "C:/Users/grima/Documents/craft-collection/plugins"
CRAFT_MOUNT = [
    f"{CRAFT}/humblepowers",
    f"{CRAFT}/engineering-discipline",
    f"{CRAFT}/session-workflow",
]
ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)", "Skill"]

# Lane-3 banks: C-present + null (haiku-first).
BANKS = ["c-debug", "c-data", "c-verif", "null-debug", "null-data", "null-verif"]
DISCIPLINE = {
    "debug": "systematic-debugging",
    "data": "data-engineering-discipline",
    "verif": "verification-before-completion",
}

# arm -> (hook plugin dir name, env var that carries the discipline)
ARMS = {
    "detector-nudge": ("detector-nudge", "DETECTOR_DISCIPLINE"),
    "retrospective-gate": ("retrospective-gate", "GATE_DISCIPLINE"),
}


def toml_for(bank, arm, plugin_dir, env_key, discipline):
    allowed = ", ".join(f'"{t}"' for t in ALLOWED)
    mounts = [*CRAFT_MOUNT, str(HOOKS / plugin_dir).replace("\\", "/")]
    lines = [
        f'name = "screen-{bank}-{arm}-haiku"',
        'adapter = "claude-cli"',
        'model = "claude-haiku-4-5"',
        'strategy = "single-session"',
        'effort = "medium"',
        "",
        "[tools]",
        'source = "none"',
        f"allowed = [{allowed}]",
        "",
        "[plugins]",
        "mount = [",
        *[f'    "{m}",' for m in mounts],
        "]",
        "",
        "[env]",
        'HUMBLEPOWERS_DISPATCH_PROMPT_INJECT = "0"',
        f'{env_key} = "{discipline}"',
        "",
        "[limits]",
        "trial_timeout_s = 600",
    ]
    return "\n".join(lines) + "\n"


def main():
    count = 0
    for bank in BANKS:
        domain = bank.rsplit("-", 1)[1]
        discipline = DISCIPLINE[domain]
        d = SCEN / f"screen-{bank}"
        d.mkdir(exist_ok=True)
        for arm, (plugin_dir, env_key) in ARMS.items():
            path = d / f"{arm}-haiku.toml"
            path.write_text(toml_for(bank, arm, plugin_dir, env_key, discipline), encoding="utf-8")
            count += 1
    print(f"wrote {count} Lane-3 scenario TOMLs across {len(BANKS)} banks")


if __name__ == "__main__":
    main()
