#!/usr/bin/env bash
# Phase-3: does the discipline-worded SubagentStop gate generalize beyond
# verification, and does the discipline-vs-prescriptive over-trigger gap replicate?
# Pre-registration: craft docs/design/2026-07-25-phase3-gate-generalization-prereg.md
# 168 trials, ~$29. Footprint banks first, then their paired null banks (the
# false-positive measurement is mandatory, not optional -- it vetoed Phase 2's
# primary-metric winner).
set -u
cd /c/Users/grima/Documents/s1
export FATHOM_STREAM_DIR="C:/Users/grima/Documents/s1/streams-phase3"
mkdir -p streams-phase3 ledger-phase3
for b in e1-debug e1-data null-debug null-data; do
  echo "=== RUNNING $b  ($(date '+%H:%M:%S')) ==="
  uv run --no-project -- fathom run "$b" \
    --scenarios-dir "scenarios/phase3-$b" \
    --repeats 3 --max-budget-usd 1.00 \
    --ledger-dir ledger-phase3 2>&1 | tail -4
done
echo "=== PHASE 3 DONE  ($(date '+%H:%M:%S')) ==="
