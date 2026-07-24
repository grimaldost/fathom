#!/usr/bin/env bash
# Full Stage-1 behavioral screen run (haiku-first; sonnet baked in for the
# tier-dependent arms bare/oracle/classifier-hint). 168 trials at repeats=1.
set -u
cd /c/Users/grima/Documents/s1
export FATHOM_STREAM_DIR="C:/Users/grima/Documents/s1/streams-screen"
mkdir -p streams-screen ledger-screen
for b in e1-debug e1-data e1-verif c-debug c-data c-verif null-debug null-data null-verif; do
  echo "=== RUNNING $b  ($(date '+%H:%M:%S')) ==="
  uv run --no-project -- fathom run "$b" \
    --scenarios-dir "scenarios/screen-$b" \
    --repeats 1 --max-budget-usd 0.80 \
    --ledger-dir ledger-screen 2>&1 | tail -4
done
echo "=== ALL 9 BANKS DONE  ($(date '+%H:%M:%S')) ==="
