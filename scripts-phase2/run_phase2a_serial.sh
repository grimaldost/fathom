#!/usr/bin/env bash
# Phase-2a RESUME (serial, value-ordered). Run AFTER a fresh re-auth so the token
# has a full lifetime and the whole remaining run completes before it expires --
# fathom copies creds per-spawn and discards refreshed tokens, so a mid-run expiry
# rotates the single-use refresh token and cascades into "could not be refreshed".
# Idempotent: e1-debug's 90 trials are already banked; fathom skips done trials.
# Banks ordered by value: e1-data + e1-verif complete Band-B + the subagent arm
# first, then null (false-positive), then Band-C.
set -u
cd /c/Users/grima/Documents/s1
export FATHOM_STREAM_DIR="C:/Users/grima/Documents/s1/streams-phase2a"
mkdir -p streams-phase2a ledger-phase2
for b in e1-data e1-verif null-debug null-data null-verif c-debug c-data c-verif; do
  echo "=== RUNNING $b  ($(date '+%H:%M:%S')) ==="
  uv run --no-project -- fathom run "$b" \
    --scenarios-dir "scenarios/phase2a-$b" \
    --repeats 3 --max-budget-usd 1.00 \
    --ledger-dir ledger-phase2 2>&1 | tail -5
done
echo "=== PHASE 2a RESUME DONE  ($(date '+%H:%M:%S')) ==="
