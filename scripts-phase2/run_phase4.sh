#!/usr/bin/env bash
# Phase-4: opus tier on the promoted gate + the successor hypothesis (H3).
# Pre-registration: craft docs/design/2026-07-25-phase4-opus-and-successor-prereg.md
# 72 trials, ~$51. Opus blocks run FIRST (the expensive, decisive question); the
# cheap haiku/sonnet successor block runs after, so a mid-run halt costs the cheap
# part. Per-spawn cap $2.00 (opus trials run ~$1).
# Paired null banks are NOT optional: every gate arm's false-positive cell runs.
set -u
cd /c/Users/grima/Documents/s1
export FATHOM_STREAM_DIR="C:/Users/grima/Documents/s1/streams-phase4"
mkdir -p streams-phase4 ledger-phase4

echo "########## 4a OPUS GATE (footprint + paired FP) ##########"
for b in e1-verif null-verif; do
  echo "=== $b  ($(date '+%H:%M:%S')) ==="
  uv run --no-project -- fathom run "$b" \
    --scenarios-dir "scenarios/phase4-$b" \
    --repeats 3 --max-budget-usd 2.00 \
    --ledger-dir ledger-phase4 2>&1 | tail -4
done

echo "########## 4c OPUS TIER GRADIENT (prompt arms) ##########"
uv run --no-project -- fathom run e1-verif \
  --scenarios-dir scenarios/phase4c-e1-verif \
  --repeats 2 --max-budget-usd 2.00 \
  --ledger-dir ledger-phase4 2>&1 | tail -4

echo "########## 4b SUCCESSOR HYPOTHESIS (haiku+sonnet) ##########"
for b in e1-debug null-debug; do
  echo "=== $b  ($(date '+%H:%M:%S')) ==="
  uv run --no-project -- fathom run "$b" \
    --scenarios-dir "scenarios/phase4-$b" \
    --repeats 3 --max-budget-usd 1.00 \
    --ledger-dir ledger-phase4 2>&1 | tail -4
done
echo "=== PHASE 4 DONE  ($(date '+%H:%M:%S')) ==="
