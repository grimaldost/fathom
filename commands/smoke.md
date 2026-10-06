---
description: Run fathom's real-spawn isolation smoke gate — the go/no-go before any paid matrix
argument-hint: "[--force-fail] [--no-engine-boundary]"
allowed-tools: Bash
---

Run the fathom smoke gate — the real-spawn go/no-go that must pass before any
paid matrix, and again when resuming one later.

1. Resolve the data root: `$FATHOM_HOME` if set, else the nearest directory at or
   above the current one whose `fathom.toml` has a `[data_root]` table, else ask
   the user. The directory must carry that marker, and it must not be the
   plugin's own tree, a plugin cache directory, or inside either. If
   `$FATHOM_HOME` is set but the current directory sits inside a different data
   root, ask the user which one they mean: `FATHOM_HOME` wins without any error.
2. From the data root directory, run the engine this plugin ships:
   `uv run --no-dev --frozen --project "${CLAUDE_PLUGIN_ROOT}" python -m fathom --home "<data root>" smoke $ARGUMENTS`
   Keep both uv flags: `--no-dev` stops the first call from installing the
   development tools into the plugin's environment, and `--frozen` uses the
   plugin's lock file as shipped instead of rewriting it.
3. A clean run ends with **`SMOKE RESULT: ALL PASS (n/n checks)`** and exits 0. It
   spends a few cents on tiny real spawns. Report the result line and, on any
   failure, the failing or skipped check: a skipped check proved nothing and keeps
   the gate red. Do not proceed to a paid run until it passes.

What smoke checks, on real spawns: the credential has life left (it reads the
credential's expiry, never its token); a spawn whose temporary config holds only
the credential authenticates and completes; a disallowed tool is refused under
default-deny; stream parsing recovers turns and tokens; a mounted plugin reaches
the CLI; the run lock excludes a second holder; and the series-engine boundary.

That last check runs the data root's `scenarios/series.toml` arm against a stub
`claude` that records its arguments and spends no tokens. Without the file it
fails, so pass `--no-engine-boundary` when the data root has no series arm.
`--force-fail` appends a failing check to demonstrate the nonzero exit. Smoke
exits 1 on any failed or skipped check.

Smoke does not prove that the data root's own treatment arms are armed. That is
`fathom verify-arming [--scenarios-dir DIR]`, which makes one cheap real spawn per
arm declaring a treatment and costs a little; `fathom run` makes the same check
before it spends.
