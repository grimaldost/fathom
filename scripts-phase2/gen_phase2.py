"""Generate Phase-2 confirmatory scenario TOMLs (3 tiers incl. opus).

Per the pre-registration (craft docs/design/2026-07-24-dispatch-phase2-preregistration.md):
- Band-B (e1-*): arms bare, oracle, classifier-hint, gate-4a, gate-placebo x 3 tiers.
- null (null-*): same 5 arms x 3 tiers (false-positive / over_scope).
- Band-C (c-*): bare, oracle x 3 tiers (opus capability check).
- Subagent arm (e1-verif only): bare-sub, gated-sub x 3 tiers -- both delegate to a
  general-purpose subagent; gated-sub additionally mounts the SubagentStop
  verification-gate plugin. The only difference between the two is the gate.

Scenario name = phase2-{bank}-{arm}-{tier}; the tier is always the last '-' segment
so multi-word arms (gate-4a, classifier-hint, bare-sub, gated-sub) parse cleanly.
The dispatch hook is forced silent so the arm's injected context (or the gate) is
the only dispatch manipulation.
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCEN = BASE / "scenarios"
ASSETS = "../screen-assets"
P2ASSETS = "../phase2-assets"
GATE_PLUGIN = str((SCEN / "phase2-hooks" / "subagent-verify-gate").as_posix())

CRAFT = "C:/Users/grima/Documents/craft-collection/plugins"
MOUNT = [f"{CRAFT}/humblepowers", f"{CRAFT}/engineering-discipline", f"{CRAFT}/session-workflow"]
ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)", "Skill"]
SUB_ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)", "Task"]
TIERS = {"haiku": "claude-haiku-4-5", "sonnet": "claude-sonnet-5", "opus": "claude-opus-4-8"}

# bank -> asset_key
BANKS = {
    "e1-debug": "debug",
    "e1-data": "data",
    "e1-verif": "verif",
    "null-debug": "null",
    "null-data": "null",
    "null-verif": "null",
    "c-debug": "debug",
    "c-data": "data",
    "c-verif": "verif",
}
BAND_B = {"e1-debug", "e1-data", "e1-verif"}
NULL = {"null-debug", "null-data", "null-verif"}
BAND_C = {"c-debug", "c-data", "c-verif"}

# prompt-time arms: arm -> inject template (asset key filled per bank)
PROMPT_ARMS = {
    "bare": None,
    "oracle": f"{ASSETS}/oracle-{{k}}.md",
    "classifier-hint": f"{ASSETS}/classifier-{{k}}.md",
    "gate-4a": f"{ASSETS}/forced-eval.md",
    "gate-placebo": f"{ASSETS}/gate-placebo.md",
}


def prompt_toml(bank, arm, tier, model, asset_key, inject_tmpl):
    allowed = ", ".join(f'"{t}"' for t in ALLOWED)
    lines = [
        f'name = "phase2-{bank}-{arm}-{tier}"',
        'adapter = "claude-cli"',
        f'model = "{model}"',
        'strategy = "single-session"',
        'effort = "medium"',
        "",
        "[tools]",
        'source = "none"',
        f"allowed = [{allowed}]",
        "",
        "[plugins]",
        "mount = [",
        *[f'    "{m}",' for m in MOUNT],
        "]",
        "",
        "[env]",
        'HUMBLEPOWERS_DISPATCH_PROMPT_INJECT = "0"',
        "",
        "[limits]",
        "trial_timeout_s = 600",
    ]
    if inject_tmpl:
        lines += ["", "[context]", f'inject = "{inject_tmpl.format(k=asset_key)}"']
    return "\n".join(lines) + "\n"


def sub_toml(bank, arm, tier, model):
    """bare-sub / gated-sub: delegate to a subagent; gated-sub mounts the gate."""
    allowed = ", ".join(f'"{t}"' for t in SUB_ALLOWED)
    mount = [GATE_PLUGIN] if arm == "gated-sub" else []
    lines = [
        f'name = "phase2-{bank}-{arm}-{tier}"',
        'adapter = "claude-cli"',
        f'model = "{model}"',
        'strategy = "single-session"',
        'effort = "medium"',
        "",
        "[tools]",
        'source = "none"',
        f"allowed = [{allowed}]",
    ]
    if mount:
        lines += ["", "[plugins]", "mount = [", *[f'    "{m}",' for m in mount], "]"]
    lines += [
        "",
        "[limits]",
        "trial_timeout_s = 600",
        "",
        "[context]",
        f'inject = "{P2ASSETS}/delegate-subagent.md"',
    ]
    return "\n".join(lines) + "\n"


def main():
    count = 0
    for bank, asset_key in BANKS.items():
        d = SCEN / f"phase2-{bank}"
        d.mkdir(exist_ok=True)
        # prompt-time arms
        if bank in BAND_C:
            arms = {"bare": None, "oracle": PROMPT_ARMS["oracle"]}
        else:  # Band-B and null
            arms = PROMPT_ARMS
        for arm, inject_tmpl in arms.items():
            for tier, model in TIERS.items():
                (d / f"{arm}-{tier}.toml").write_text(
                    prompt_toml(bank, arm, tier, model, asset_key, inject_tmpl),
                    encoding="utf-8",
                )
                count += 1
        # subagent arms: e1-verif only
        if bank == "e1-verif":
            for arm in ("bare-sub", "gated-sub"):
                for tier, model in TIERS.items():
                    (d / f"{arm}-{tier}.toml").write_text(
                        sub_toml(bank, arm, tier, model), encoding="utf-8"
                    )
                    count += 1
    print(f"wrote {count} Phase-2 scenario TOMLs")


if __name__ == "__main__":
    main()
