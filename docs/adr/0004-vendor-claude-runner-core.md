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

## Amendment (2026-10-24): fathom writes a refreshed credential back to the seat (T53b)

Until this amendment fathom read two timestamps from the seat's credential file
(`expiresAt`, `refreshTokenExpiresAt`) and copied the file, and never wrote it. A spawn
that meets an expired access token refreshes it inside its copy; the server rotates the
refresh token, and the seat's file kept the spent one, so after a run or a smoke that
refreshed, the owner's next `claude` asked for `/login`. The owner chose on 2026-10-24 to
let fathom write the seat's file, under these conditions:

- **When.** Once, when `fathom run`, `fathom smoke` or a subject of the acceptance harness
  ends, from the run's carried copy (`CredentialStore`) or the subject's configuration
  directory (`fathom.credentials.write_back_to_seat`).
- **Guard.** Only when the copy is newer than the seat's file by both expiry timestamps
  (strictly later `expiresAt`, and strictly later `refreshTokenExpiresAt` when the seat's
  file has one), and the seat's file is byte-identical to what was last copied from it
  (compared by SHA-256, once before the merge and once just before the rename). When
  another session changed the seat's file meanwhile, fathom leaves it as it is and says so.
- **What is written.** The seat's `claudeAiOauth` block is replaced by the copy's; every
  other key keeps the seat's value. The new file is written in full to a temporary file in
  the seat's directory and moved over the seat's file with one `os.replace`.
- **What is read.** The merge parses both files, so token values pass through the process
  for the length of that call. None is printed, logged or kept: the result names an
  outcome only.
- **Refusal at start.** `fathom run`, `fathom smoke` and the acceptance harness in isolated
  mode refuse to start while the seat's access token has already expired, and print the
  cure: run any `claude` command once, so the seat refreshes its own file in place.

The guard does not cover a write by another process in the moment between the last
comparison and the rename; on Windows no file system primitive closes that window.
If a real refresh does not move `refreshTokenExpiresAt` forward, the guard finds the copy
not newer and nothing is written; the refusal at start then still keeps the next spend
from starting on a spent seat.
