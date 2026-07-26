"""Generate Phase-4 scenarios: opus tier + the successor hypothesis (H3).

Per docs/design/2026-07-25-phase4-opus-and-successor-prereg.md.
 4a  opus  : bare-sub / disc-sub on e1-verif + null-verif (paired FP, mandatory)
 4b  h+s   : presc-artifact-sub on e1-debug + null-debug -- a prescriptive gate for
             the DEBUGGING discipline whose artifact is always producible
 4c  opus  : bare / classifier-hint on e1-verif (tier-gradient check, prompt arms)
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCEN = BASE / "scenarios"
ASSETS = "../screen-assets"
P2ASSETS = "../phase2-assets"
GATE_MULTI = (SCEN / "phase3-hooks" / "subagent-gate-multi").as_posix()
GATE_VERIFY = (SCEN / "phase2-hooks" / "subagent-generic-gate").as_posix()

CRAFT = "C:/Users/grima/Documents/craft-collection/plugins"
MOUNT = [f"{CRAFT}/humblepowers", f"{CRAFT}/engineering-discipline", f"{CRAFT}/session-workflow"]
SUB_ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)", "Task"]
PROMPT_ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)", "Skill"]
OPUS = "claude-opus-5"
HS = {"haiku": "claude-haiku-4-5", "sonnet": "claude-sonnet-5"}


def sub_toml(bank, arm, tier, model, mount=None, env=None):
    allowed = ", ".join(f'"{t}"' for t in SUB_ALLOWED)
    lines = [
        f'name = "phase4-{bank}-{arm}-{tier}"',
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
        lines += ["", "[plugins]", "mount = [", f'    "{mount}",', "]"]
    if env:
        lines += ["", "[env]"] + [f'{k} = "{v}"' for k, v in env.items()]
    lines += [
        "",
        "[limits]",
        "trial_timeout_s = 900",
        "",
        "[context]",
        f'inject = "{P2ASSETS}/delegate-subagent.md"',
    ]
    return "\n".join(lines) + "\n"


def prompt_toml(bank, arm, tier, model, inject):
    allowed = ", ".join(f'"{t}"' for t in PROMPT_ALLOWED)
    lines = [
        f'name = "phase4-{bank}-{arm}-{tier}"',
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
        "trial_timeout_s = 900",
    ]
    if inject:
        lines += ["", "[context]", f'inject = "{inject}"']
    return "\n".join(lines) + "\n"


def main():
    n = 0
    # --- 4a: opus gate, footprint + paired FP ---
    for bank in ("e1-verif", "null-verif"):
        d = SCEN / f"phase4-{bank}"
        d.mkdir(exist_ok=True)
        (d / "bare-sub-opus.toml").write_text(
            sub_toml(bank, "bare-sub", "opus", OPUS), encoding="utf-8"
        )
        (d / "disc-sub-opus.toml").write_text(
            sub_toml(bank, "disc-sub", "opus", OPUS, mount=GATE_VERIFY), encoding="utf-8"
        )
        n += 2

    # --- 4b: successor hypothesis, always-producible artifact for DEBUGGING ---
    env = {"GATE_DISCIPLINE": "debug", "GATE_REGISTER": "artifact"}
    for bank in ("e1-debug", "null-debug"):
        d = SCEN / f"phase4-{bank}"
        d.mkdir(exist_ok=True)
        for tier, model in HS.items():
            (d / f"presc-artifact-sub-{tier}.toml").write_text(
                sub_toml(bank, "presc-artifact-sub", tier, model, mount=GATE_MULTI, env=env),
                encoding="utf-8",
            )
            n += 1

    # --- 4c: opus tier-gradient check on the prompt arms ---
    d = SCEN / "phase4c-e1-verif"
    d.mkdir(exist_ok=True)
    (d / "bare-opus.toml").write_text(
        prompt_toml("e1-verif", "bare", "opus", OPUS, None), encoding="utf-8"
    )
    (d / "classifier-hint-opus.toml").write_text(
        prompt_toml("e1-verif", "classifier-hint", "opus", OPUS, f"{ASSETS}/classifier-verif.md"),
        encoding="utf-8",
    )
    n += 2
    print(f"wrote {n} Phase-4 scenario TOMLs")


if __name__ == "__main__":
    main()
