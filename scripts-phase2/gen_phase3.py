"""Generate Phase-3 scenarios: does the discipline-worded gate generalize?

Per docs/design/2026-07-25-phase3-gate-generalization-prereg.md. Three arms per
bank -- bare-sub, disc-sub, presc-sub -- all delegating implementation to a
general-purpose subagent with identical [context]; the only difference is which gate
plugin is mounted and how GATE_REGISTER is set. Footprint banks e1-debug / e1-data;
their null banks carry the mandatory paired false-positive measurement.

bare-sub is already banked for null-debug (Phase 2), so it is skipped there.
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCEN = BASE / "scenarios"
P2ASSETS = "../phase2-assets"
GATE = (SCEN / "phase3-hooks" / "subagent-gate-multi").as_posix()

SUB_ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)", "Task"]
TIERS = {"haiku": "claude-haiku-4-5", "sonnet": "claude-sonnet-5"}

# bank -> (discipline, arms)
PLAN = {
    "e1-debug": ("debug", ["bare-sub", "disc-sub", "presc-sub"]),
    "e1-data": ("data", ["bare-sub", "disc-sub", "presc-sub"]),
    "null-debug": ("debug", ["disc-sub", "presc-sub"]),  # bare-sub banked in Phase 2
    "null-data": ("data", ["bare-sub", "disc-sub", "presc-sub"]),
}
REGISTER = {"disc-sub": "discipline", "presc-sub": "prescriptive"}


def toml_for(bank, discipline, arm, tier, model):
    allowed = ", ".join(f'"{t}"' for t in SUB_ALLOWED)
    lines = [
        f'name = "phase3-{bank}-{arm}-{tier}"',
        'adapter = "claude-cli"',
        f'model = "{model}"',
        'strategy = "single-session"',
        'effort = "medium"',
        "",
        "[tools]",
        'source = "none"',
        f"allowed = [{allowed}]",
    ]
    if arm in REGISTER:
        lines += [
            "",
            "[plugins]",
            "mount = [",
            f'    "{GATE}",',
            "]",
            "",
            "[env]",
            f'GATE_DISCIPLINE = "{discipline}"',
            f'GATE_REGISTER = "{REGISTER[arm]}"',
        ]
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
    for bank, (discipline, arms) in PLAN.items():
        d = SCEN / f"phase3-{bank}"
        d.mkdir(exist_ok=True)
        for arm in arms:
            for tier, model in TIERS.items():
                (d / f"{arm}-{tier}.toml").write_text(
                    toml_for(bank, discipline, arm, tier, model), encoding="utf-8"
                )
                count += 1
    print(f"wrote {count} Phase-3 scenario TOMLs")


if __name__ == "__main__":
    main()
