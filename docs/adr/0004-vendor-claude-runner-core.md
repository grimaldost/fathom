# ADR-0004 — Vendor the proven claude_runner core; do not depend on or rewrite it

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

craft-collection's `evals/harness/claude_runner.py` embodies hard-won spawn
mechanics: a temp `CLAUDE_CONFIG_DIR` containing only the copied credential,
headless default-deny permissions (never `bypassPermissions`), stream-json parsing
that tolerates partial streams on timeout, retry with cap, and per-spawn budget
flags. Three of its defects (sandbox leak, timeout streaming, isolation) were
found and fixed by live eval rounds in 2026-06. fathom needs exactly this core as
its first Runner adapter, but craft-collection is itself a fathom test subject.

## Decision

Copy (vendor) the runner core into `src/fathom/adapters/claude_cli.py` and refactor
it behind the `Runner` protocol (ADR-0001). fathom takes no import-time dependency
on craft-collection; divergence is expected and managed consciously.

## Alternatives considered

- **Path dependency on craft-collection's evals package** — couples the
  measuring instrument to a repo it measures; concurrent-session worktree state
  in that repo could silently change the instrument mid-run.
- **Greenfield rewrite** — discards debugged isolation behavior; the failure
  modes it guards against (credential leak into real config, bypassed
  allowlists, lost partial streams) are expensive to rediscover.

## Consequences

- One-time duplication is accepted; future fixes to the upstream harness must be
  ported deliberately (a reflection-triage input, not an automatic sync).
- The vendored core's isolation properties are asserted by fathom's own smoke gate
  on real spawns before any paid matrix.
- New invariant: **spawn isolation properties** (credential-only temp config;
  default-deny tool permissions) must hold for every adapter run; the smoke gate
  is their check.
