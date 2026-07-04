## Mode
plan -> implement -> verify

## Mandatory pre-read
- `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` — §8 (and the `--scenarios-dir` footgun in `CLAUDE.md`)
- `scenarios/skill-pyeng/*.toml` — the arm-TOML pattern (flat schema; `[context] inject` is the model for
  `[plugins] mount`)
- `src/fathom/scenario.py` — the `[plugins] mount` field (PR02; depends_on PR02)

## Task
Vendor the pinned plugins and author the 5 arm scenarios.
- **Vendor** (copy plugin content only — `.claude-plugin/`, `skills/`, `hooks/`; NO `.git`) into
  `tasks/humble-vs-super-v1/plugins/`:
  - `humblepowers@0.3.1` from `~/.claude/plugins/cache/craft-collection/humblepowers/0.3.1`
  - `superpowers@6fd4507` (obra/superpowers v5.1.0, pinned commit 6fd4507659784c351abbd2bc264c7162cfd386dc —
    if not already present locally, clone it shallow and check out that commit, then copy minus `.git`)
  - `engineering-discipline` and `session-workflow` from the craft-collection cache (the held-constant stack)
  - Record the source repo + pinned commit/version for each in a short `tasks/humble-vs-super-v1/plugins/VENDORED.md`.
- **Author** `scenarios/humble-vs-super/{bare,humble-only,super-only,stack-humble,stack-super}.toml`, identical
  in `model = "claude-opus-4-8"`, `effort = "high"`, `strategy = "single-session"`, `[tools] source = "none"`,
  `allowed = ["Read","Write","Edit","Glob","Grep","Task","PowerShell","Bash"]`, and `[limits] trial_timeout_s`,
  differing ONLY by `[plugins] mount`:
  - `bare`: no `[plugins]`
  - `humble-only`: mount the vendored humblepowers dir
  - `super-only`: mount the vendored superpowers dir
  - `stack-humble`: mount humblepowers + engineering-discipline + session-workflow
  - `stack-super`: mount superpowers + engineering-discipline + session-workflow
  Mount paths are relative to the scenario file (PR02 absolutizes them).

## Constraints
- The two `stack-*` arms must mount an IDENTICAL held-constant set (engineering-discipline + session-workflow),
  differing only by the humble/super dir (common-mode cancellation, §1).
- Vendored plugin trees are committed (deliberate pin); do not add them to `.gitignore`.

## Starting file list
1. `tasks/humble-vs-super-v1/plugins/{humblepowers@0.3.1,superpowers@6fd4507,engineering-discipline,session-workflow}/`
2. `tasks/humble-vs-super-v1/plugins/VENDORED.md`
3. `scenarios/humble-vs-super/{bare,humble-only,super-only,stack-humble,stack-super}.toml`

## Definition of done
- [ ] `uv run fathom run humble-vs-super-v1 --scenarios-dir scenarios/humble-vs-super --dry-run` resolves all five
      arms and prints the trial count and USD ceiling (spec §8 acceptance).
- [ ] The two `stack-*` arms' resolved configs differ only by the humble/super directory within an identical
      held-constant set.
- [ ] All quality gates pass.
