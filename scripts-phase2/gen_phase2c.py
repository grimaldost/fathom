"""Generate Phase-2c scenarios: the two validity tests defending the subagent win.

Test 1 (generalization): `generic-sub` — the SubagentStop gate whose wording never
names the measured criterion — on e1-verif, vs the existing bare-sub / gated-sub.
If footprint still lifts, the mechanism generalizes; if it collapses, the +0.56 was
criterion-naming.

Test 2 (false positive): all three subagent arms on the NULL banks, where the right
behavior is to make the trivial edit and stop. Metric over_scope: does an always-on
verification gate force pointless work on trivial edits? Unmeasured until now.

Both tiers (haiku, sonnet). Scenario name = phase2-{bank}-{arm}-{tier}.
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCEN = BASE / "scenarios"
P2ASSETS = "../phase2-assets"
GATES = {
    "gated-sub": (SCEN / "phase2-hooks" / "subagent-verify-gate").as_posix(),
    "generic-sub": (SCEN / "phase2-hooks" / "subagent-generic-gate").as_posix(),
}

SUB_ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)", "Task"]
TIERS = {"haiku": "claude-haiku-4-5", "sonnet": "claude-sonnet-5"}
ARMS = ["bare-sub", "gated-sub", "generic-sub"]

# Test 1: generic gate on the footprint bank. Test 2: all arms on the null banks.
PLAN = {
    "e1-verif": ["generic-sub"],  # bare-sub / gated-sub already banked in 2a
    "null-verif": ARMS,
    "null-debug": ARMS,
}


def sub_toml(bank, arm, tier, model):
    allowed = ", ".join(f'"{t}"' for t in SUB_ALLOWED)
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
    if arm in GATES:
        lines += ["", "[plugins]", "mount = [", f'    "{GATES[arm]}",', "]"]
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
    for bank, arms in PLAN.items():
        d = SCEN / f"phase2c-{bank}"
        d.mkdir(exist_ok=True)
        for arm in arms:
            for tier, model in TIERS.items():
                (d / f"{arm}-{tier}.toml").write_text(
                    sub_toml(bank, arm, tier, model), encoding="utf-8"
                )
                count += 1
    print(f"wrote {count} Phase-2c scenario TOMLs")


if __name__ == "__main__":
    main()
