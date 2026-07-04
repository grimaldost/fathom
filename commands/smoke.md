---
description: Run fathom's real-spawn isolation smoke gate — the go/no-go before any paid matrix
argument-hint: "[--force-fail] [--no-engine-boundary]"
allowed-tools: Bash
---

Run the fathom smoke gate — the real-spawn go/no-go that must pass before any
paid matrix, and again at every resume.

1. Resolve the fathom checkout: use `$FATHOM_HOME` if set, else the current repo
   if it is a fathom checkout (`pyproject.toml` with `name = "fathom"`). If
   neither, ask the user for their fathom checkout path. Never run from a plugin
   cache-clone.
2. From that directory, run: `uv run python -m fathom smoke $ARGUMENTS`
3. A clean run prints **`ALL PASS (8/8 checks)`** and exits 0. It spends a few
   cents on tiny real spawns. Report the pass/fail line and, on any failure, the
   failing check — do not proceed to a paid run until it passes.

`--force-fail` demonstrates the nonzero-exit path; `--no-engine-boundary` skips
the convoy engine-boundary assertion (group 4).
