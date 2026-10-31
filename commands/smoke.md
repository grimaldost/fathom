---
description: Run fathom's real-spawn isolation smoke gate — the go/no-go before any paid matrix
argument-hint: "[--force-fail]"
allowed-tools: Bash
---

Run the fathom smoke gate — the real-spawn go/no-go that must pass before any
paid matrix, and again when resuming one later.

1. Smoke reads no data root, so there is nothing to resolve. From the current
   directory, run the engine this plugin ships:
   `uv run --no-dev --frozen --project "${CLAUDE_PLUGIN_ROOT}" python -m fathom smoke $ARGUMENTS`
   Keep both uv flags: `--no-dev` stops the first call from installing the
   development tools into the plugin's environment, and `--frozen` uses the
   plugin's lock file as shipped instead of rewriting it. Do not pass `--home`.
2. A clean run ends with **`SMOKE RESULT: ALL PASS (n/n checks)`** and exits 0. It
   spends a few cents on tiny real spawns. Report the result line and, on any
   failure, the failing or skipped check: a skipped check proved nothing and keeps
   the gate red. Do not proceed to a paid run until it passes.

What smoke checks, on real spawns: the credential has life left (it reads the
credential's expiry, never its token); a spawn whose temporary config holds only
the credential authenticates and completes; a disallowed tool is refused under
default-deny; stream parsing recovers turns and tokens; a mounted plugin reaches
the CLI; the run lock excludes a second holder; and no instruction file from
above the workspace reaches a spawn.

`--force-fail` appends a failing check to demonstrate the nonzero exit. Smoke
exits 1 on any failed or skipped check. In 0.13.0 the engine-boundary check was retired,
and `--no-engine-boundary` is ignored if given.

Smoke does not prove that the data root's own treatment arms are armed. That is
`fathom verify-arming [--scenarios-dir DIR]`, which makes one cheap real spawn per
arm declaring a treatment and costs a little; `fathom run` makes the same check
before it spends.
