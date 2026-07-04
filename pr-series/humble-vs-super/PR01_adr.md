## Mode
plan -> write -> verify (a single ADR document)

## Mandatory pre-read
- `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` — §1 and the Context section
- an existing ADR for house style, e.g. `docs/adr/0004-vendor-claude-runner-core.md` and `docs/adr/0005-sealed-holdout-tasks.md`

## Task
Write `docs/adr/0006-plugin-mount-fidelity.md` recording the plugin-mount fidelity decision for the
humble-vs-super eval. It must state, in prose:
- **Decision:** mount whole plugins via the claude CLI `--plugin-dir` flag (triggering included) rather than
  force-loading individual skill bodies via `--append-system-prompt-file` (as `skill-pyeng-v1` did).
- **Why:** a process-discipline plugin's value is that the right skill auto-fires; force-loading destroys the
  dispatch/triggering signal that is the main differentiator. Validated by the 2026-06-14 spike (both
  humblepowers and superpowers mount and load their skills in headless `-p`).
- **config_hash consequence:** the mounted plugin set enters `config_hash` as `(name, version, tree_sha)` per
  plugin (implemented in §2), hashed only when non-empty so prior ledgers stay stable.
- **Common-mode cancellation:** the `stack-*` arms mount an identical held-constant plugin set, so its exact
  versions cannot bias the humble<->super contrast — only its external validity.
- **Rejected alternative:** force-load the union of skill bodies (weaker; loses triggering; not "the stack").

## Constraints
- Follow the existing ADR format (status, context, decision, consequences, alternatives).
- Status: Accepted. Use ADR number 0006 (confirmed free on this base).
- Docs-only PR: no code changes.

## Starting file list
1. `docs/adr/0006-plugin-mount-fidelity.md` — create

## Definition of done
- [ ] The ADR exists with status Accepted and records the force-load rejected alternative and the
      common-mode-cancellation rationale in prose (spec §1 acceptance criterion).
- [ ] All quality gates pass (ruff format/check, pytest — unaffected by a docs-only change).
