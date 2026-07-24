"""Generate screen scenario TOMLs (Lane 2 arms + universal bare/oracle controls).

Lane 3 hook arms (detector-nudge / retrospective-gate / runtime-skill-search /
trajectory-judge) are added by a later pass once their hook plugins are built.

Assignment (pre-registered spec Peca 4.2 / 4.3):
- bare, oracle: ALL banks, BOTH tiers (universal controls).
- static-registry, classifier-hint, framing-4d, gate-4a, gate-placebo: B-present
  (e1-*) + null banks. classifier-hint runs BOTH tiers; the rest haiku-first.
- The dispatch hook is forced silent ([env] HUMBLEPOWERS_DISPATCH_PROMPT_INJECT=0)
  so the only dispatch influence is the arm's injected [context], identical mounts
  otherwise cancelling.
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCEN = BASE / "scenarios"

CRAFT = "C:/Users/grima/Documents/craft-collection/plugins"
MOUNT = [f"{CRAFT}/humblepowers", f"{CRAFT}/engineering-discipline", f"{CRAFT}/session-workflow"]
ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)", "Skill"]
TIERS = {"haiku": "claude-haiku-4-5", "sonnet": "claude-sonnet-5"}

# bank -> (asset_key, lane)
BANKS = {
    "e1-debug": ("debug", "B"),
    "e1-data": ("data", "B"),
    "e1-verif": ("verif", "B"),
    "c-debug": ("debug", "C"),
    "c-data": ("data", "C"),
    "c-verif": ("verif", "C"),
    "null-debug": ("null", "null"),
    "null-data": ("null", "null"),
    "null-verif": ("null", "null"),
}

# arm -> (inject_template or None for bare, lanes it runs on, tiers)
ARMS = {
    "bare": (None, {"B", "C", "null"}, ["haiku", "sonnet"]),
    "oracle": ("oracle-{k}.md", {"B", "C", "null"}, ["haiku", "sonnet"]),
    "static-registry": ("registry.md", {"B", "null"}, ["haiku"]),
    "classifier-hint": ("classifier-{k}.md", {"B", "null"}, ["haiku", "sonnet"]),
    "framing-4d": ("framing.md", {"B", "null"}, ["haiku"]),
    "gate-4a": ("forced-eval.md", {"B", "null"}, ["haiku"]),
    "gate-placebo": ("gate-placebo.md", {"B", "null"}, ["haiku"]),
}


def toml_for(bank, arm, tier, model, asset_key, inject_tmpl):
    allowed = ", ".join(f'"{t}"' for t in ALLOWED)
    lines = [
        f'name = "screen-{bank}-{arm}-{tier}"',
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
        f = inject_tmpl.format(k=asset_key)
        lines += ["", "[context]", f'inject = "../screen-assets/{f}"']
    return "\n".join(lines) + "\n"


def main():
    count = 0
    for bank, (asset_key, lane) in BANKS.items():
        d = SCEN / f"screen-{bank}"
        d.mkdir(exist_ok=True)
        for arm, (inject_tmpl, lanes, tiers) in ARMS.items():
            if lane not in lanes:
                continue
            for tier in tiers:
                path = d / f"{arm}-{tier}.toml"
                path.write_text(
                    toml_for(bank, arm, tier, TIERS[tier], asset_key, inject_tmpl),
                    encoding="utf-8",
                )
                count += 1
    print(f"wrote {count} scenario TOMLs across {len(BANKS)} banks")


if __name__ == "__main__":
    main()
