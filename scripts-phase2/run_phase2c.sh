#!/usr/bin/env bash
# Phase-2c: the two validity tests that defend the 2a subagent win, then the
# 2a missing data (lost to the weekly limit). Serial, value-ordered: the validity
# tests run FIRST so a second limit-hit costs us the re-run, not the tests.
#   1. generic-sub on e1-verif      -> does the gate generalize past criterion-naming?
#   2. subagent arms on null banks  -> does an always-on gate over-trigger? (FP)
#   3. c-*, null-verif, null-data   -> refill 2a's missing cells
set -u
cd /c/Users/grima/Documents/s1
export FATHOM_STREAM_DIR="C:/Users/grima/Documents/s1/streams-phase2c"
mkdir -p streams-phase2c ledger-phase2

echo "########## VALIDITY TESTS ##########"
for b in e1-verif null-verif null-debug; do
  echo "=== 2c $b  ($(date '+%H:%M:%S')) ==="
  uv run --no-project -- fathom run "$b" \
    --scenarios-dir "scenarios/phase2c-$b" \
    --repeats 3 --max-budget-usd 1.00 \
    --ledger-dir ledger-phase2 2>&1 | tail -4
done

echo "########## 2a MISSING DATA ##########"
for b in c-debug c-data c-verif null-verif null-data; do
  echo "=== refill $b  ($(date '+%H:%M:%S')) ==="
  uv run --no-project -- fathom run "$b" \
    --scenarios-dir "scenarios/phase2a-$b" \
    --repeats 3 --max-budget-usd 1.00 \
    --ledger-dir ledger-phase2 2>&1 | tail -4
done
echo "=== PHASE 2c DONE  ($(date '+%H:%M:%S')) ==="
