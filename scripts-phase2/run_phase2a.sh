#!/usr/bin/env bash
# Phase-2a: haiku + sonnet, all 9 banks, repeats=3. The powered A3 (gate
# replication) answer on 2 tiers + the subagent arm + null false-positive.
# Opus (Phase-2b) runs separately after a checkpoint. Per-spawn cap $1.00 is a
# runaway guard (screen trials averaged $0.12); total is governed by trial count
# (~558 trials, est ~$75).
set -u
cd /c/Users/grima/Documents/s1
export FATHOM_STREAM_DIR="C:/Users/grima/Documents/s1/streams-phase2a"
mkdir -p streams-phase2a ledger-phase2
for b in e1-debug e1-data e1-verif null-debug null-data null-verif c-debug c-data c-verif; do
  echo "=== RUNNING $b  ($(date '+%H:%M:%S')) ==="
  uv run --no-project -- fathom run "$b" \
    --scenarios-dir "scenarios/phase2a-$b" \
    --repeats 3 --max-budget-usd 1.00 \
    --ledger-dir ledger-phase2 2>&1 | tail -5
done
echo "=== PHASE 2a DONE  ($(date '+%H:%M:%S')) ==="
