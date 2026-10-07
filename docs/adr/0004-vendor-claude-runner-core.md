# ADR-0004 — Vendor the runner core of an earlier eval harness; do not depend on or rewrite it

> **Note (0.8.0):** particulars were removed from this record for the standalone engine.

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

The runner core of an earlier eval harness already implements the spawn mechanics
fathom needs: a temp `CLAUDE_CONFIG_DIR` containing only the copied credential,
headless default-deny permissions (never `bypassPermissions`), stream-json parsing
that tolerates partial streams on timeout, retry with cap, and per-spawn budget
flags. Its handling of three failure modes (a sandbox leak, output lost on timeout,
broken isolation) is already debugged. fathom needs exactly this core as its first
Runner adapter, but that harness lives in a repository whose tools fathom may itself
measure.

## Decision

Copy (vendor) the runner core into `src/fathom/adapters/claude_cli.py` and refactor
it behind the `Runner` protocol (ADR-0001). fathom takes no import-time dependency
on the harness it was copied from; divergence is expected and managed consciously.

## Alternatives considered

- **Path dependency on the earlier harness's package** — couples the measuring
  instrument to a repository it may measure; uncommitted work in that repository
  could silently change the instrument mid-run.
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

## Amendment: instruction files above the workspace (FATH-B83)

A credential-only `CLAUDE_CONFIG_DIR` keeps the user's configuration directory out, but
Claude Code also reads `CLAUDE.md`, `CLAUDE.local.md` and `.claude/CLAUDE.md` in every
directory above its working directory. On Windows the temporary directory, where workspaces
are staged, lies inside the user's profile, so the profile's `.claude/CLAUDE.md` reached every
spawn. Each spawn now also gets a `--settings` layer, written into its own configuration
directory, whose `claudeMdExcludes` lists those files; the arm's `settings.json` is left as
declared. The account's claude.ai connectors are turned off in the spawn environment. The
smoke gate checks the effect on a live spawn, not the configuration directory's contents:
the earlier check passed throughout, because it asserted the cause it had fixed.
