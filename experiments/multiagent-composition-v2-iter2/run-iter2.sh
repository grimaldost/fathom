#!/usr/bin/env bash
# Iteration 2 of the multiagent-composition program on bank multiagent-composition-v2 —
# the eight contemporaneous cells {control2, placebo2, perpr2, hook2} x {haiku, sonnet} from
# scenarios/multiagent-composition-v2-iter2, same ledger, a fresh stream dir.
#   usage: run-iter2.sh <n_per_cell> <max_run_usd> <stream_dir> [START] [ITER_SPEND_CAP]
# Modelled on run-main2.sh / run-hook2.sh, with the lessons of iteration 1:
#   * HARNESS DIR staged outside the repository (prompts/, run_convoy_gate.py, type_probe.py,
#     placebo_gate.py, series.toml from the task dir; placebo_gate2.py, hook-gate.toml from the
#     iter2 assets); FATHOM_TASK_DIR / FATHOM_PROMPTS_DIR point at it, FATHOM_STREAM_DIR is
#     absolute (the hook arms' Stop hook resolves it from the workspace). Its contents are
#     hashed into a manifest on pass 1 and compared on every later invocation (including a
#     resume) — a mid-run edit to the driver/probe/prompts/series.toml forks the arm silently
#     otherwise, and config_hash does not cover referenced files.
#   * SPEND is the iteration's own: cost_usd_est of run rows whose config_hash belongs to a
#     trial row of one of the eight iter2 scenarios (voided trials were paid, so no void filter).
#   * FORECAST CAP, checked BEFORE a pass starts: spent + forecast > ITER_SPEND_CAP -> exit 6
#     without starting the pass. The forecast is the mean cost of the completed passes on the
#     iter2 cells (a pass is complete when all eight cells carry a COMPLETED trial row for its
#     repeat — an errored re-buy does not count as a pass, or the forecast is pulled low by rows
#     that bought nothing), or $19.5 when none has completed. The cap check fails CLOSED: a
#     non-numeric spend/forecast (a failed ledger read, a missing interpreter) stops the runner
#     rather than silently skipping the cap. ITER_SPEND_CAP is required and is refused above the
#     pre-registered $385. Iteration 1 checked its cap only after a pass.
#   * after EVERY pass: the exposure scan (exit 7 on any exposed counted trial), passing BOTH
#     --task-dir-name <bank> (the repo's tasks/<bank> tree) and --task-dir <harness dir> (the
#     staged copy outside the repo, which the name-only match cannot see); after pass 1: the
#     per-arm arming check over the pass-1 trials (exit 8 on any FAIL). The arming check is
#     gated on its own artefact (iter2-arming.txt), not on the pass counter, so a resume that
#     starts at START>1 because pass 1 never produced trials still runs it once.
#   * seat death (exit 3) and fixture drift (exit 4) as run-main2.sh; a post-pass hard cap (5).
#   * the runner reads fathom's own exit code after every pass and stops the matrix on ANY
#     non-zero code, naming it: 10 infrastructure/seat (resume with START=$k after re-login,
#     retried once automatically first), 11 unarmed (retried once after a 60s sleep, since the
#     arming probe is a single-attempt spawn and a transient blip should not end the run), 12
#     bank invalid, 14 run-budget rail, anything else reported and stopped. seat_dead() is kept
#     only to put a human-readable message on an infrastructure exit, never as the gate itself.
#   * pass logs at <stream_dir>/iter2-pass-<k>.log; the cumulative iter2 spend after each pass.
set -uo pipefail
N="$1"; CAP="$2"; STREAMS="$3"; START="${4:-1}"; SPEND_CAP="${5:-385}"
BANK="multiagent-composition-v2"
SDIR="scenarios/multiagent-composition-v2-iter2"
LEDGER="ledger/$BANK.jsonl"
ITER2_CELLS="control2-haiku control2-sonnet placebo2-haiku placebo2-sonnet perpr2-haiku perpr2-sonnet hook2-haiku hook2-sonnet"
FIRST_PASS_FORECAST="19.5"

# The pre-registered cap is $385: an override may lower it, never raise it.
if ! uv run python -c "import sys; sys.exit(0 if float('$SPEND_CAP') <= 385 else 1)"; then
  echo "SPEND_CAP \$$SPEND_CAP exceeds the pre-registered \$385 — refusing to start" >&2
  exit 9
fi

cd /c/Users/grima/Documents/fathom
REAL_TASK_DIR="/c/Users/grima/Documents/fathom/tasks/$BANK/exprlang"
HARNESS_DIR="$(cygpath -u "$LOCALAPPDATA")/Temp/fathom-harness-$BANK-iter2"
for f in "$SDIR/assets/placebo_gate2.py" "$SDIR/assets/hook-gate.toml"; do
  [ -f "$f" ] || { echo "missing $f — the iter2 scenarios dir is not staged"; exit 2; }
done
rm -rf "$HARNESS_DIR"; mkdir -p "$HARNESS_DIR"
cp -r "$REAL_TASK_DIR/prompts" "$HARNESS_DIR/prompts"
for f in run_convoy_gate.py type_probe.py placebo_gate.py series.toml; do cp "$REAL_TASK_DIR/$f" "$HARNESS_DIR/$f"; done
cp "$SDIR/assets/placebo_gate2.py" "$HARNESS_DIR/placebo_gate2.py"
cp "$SDIR/assets/hook-gate.toml" "$HARNESS_DIR/hook-gate.toml"
mkdir -p "$STREAMS"
STREAMS_ABS="$(cygpath -m "$(cd "$STREAMS" && pwd)")"
export FATHOM_TASK_DIR="$(cygpath -m "$HARNESS_DIR")"
export FATHOM_PROMPTS_DIR="$FATHOM_TASK_DIR/prompts"
export FATHOM_STREAM_DIR="$STREAMS_ABS"
unset FATHOM_CONVOY_GATE_LOCAL
echo "harness dir: $FATHOM_TASK_DIR (contains: $(ls "$HARNESS_DIR" | tr '\n' ' '))"
echo "stream dir:  $FATHOM_STREAM_DIR"
echo "spend cap:   \$$SPEND_CAP (pre-registered ceiling: \$385)"

# Harness content attestation: hash every staged file. Pass 1 writes the manifest; every
# later invocation (a fresh re-copy from the live repo, since the top of this script is
# unconditional) compares against it and refuses to proceed on drift, so an edit to the
# driver/probe/prompts/series.toml between resumes cannot silently fork the arm's material.
MANIFEST="$STREAMS/harness-manifest.txt"
NEW_MANIFEST="$(uv run python -c "
import hashlib, sys
from pathlib import Path
root = Path(sys.argv[1])
for p in sorted(root.rglob('*')):
    if p.is_file():
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        print(f'{digest} {p.relative_to(root).as_posix()}')
" "$HARNESS_DIR")"
if [ -f "$MANIFEST" ]; then
  if ! diff <(echo "$NEW_MANIFEST") "$MANIFEST" > "$STREAMS/harness-manifest.diff" 2>&1; then
    echo "HARNESS MATERIAL DRIFTED since the manifest was written — see $STREAMS/harness-manifest.diff" >&2
    cat "$STREAMS/harness-manifest.diff" >&2
    echo "If this drift is intended (a deliberate arm-versioning edit), delete $MANIFEST and re-run." >&2
    exit 9
  fi
else
  echo "$NEW_MANIFEST" > "$MANIFEST"
fi
echo "harness manifest: $MANIFEST ($(wc -l < "$MANIFEST") files attested)"

seat_dead() {
  # Message only, never the gate: the real gate is fathom's own exit code (see the loop).
  local log="$1"
  grep -qi 'Failed to authenticate\|OAuth session expired\|authentication.\{0,20\}fail\|oauth.\{0,20\}\(expired\|invalid\)\|infrastructure error' "$log" && return 0
  tail -n 6 "$LEDGER" 2>/dev/null | grep -q '"status": "infrastructure"'
}

# Prints three fields: <iter2 spend> <forecast for the next pass> <completed iter2 passes>.
# "Completed" here means every one of the eight cells carries a COMPLETED trial row for that
# repeat (not merely any row — an errored re-buy must not count as bought a pass, or the
# forecast for the next pass is pulled below what it will actually cost). Spend itself stays
# unfiltered: an errored or infrastructure-killed attempt was still paid for.
iter2_stats() {
  uv run python - "$LEDGER" "$ITER2_CELLS" "$FIRST_PASS_FORECAST" <<'PY'
import json, sys
ledger, cells, first = sys.argv[1], set(sys.argv[2].split()), float(sys.argv[3])
try:
    rows = [json.loads(l) for l in open(ledger, encoding="utf-8") if l.strip()]
except Exception as exc:
    print(f"ERROR reading ledger: {exc}", file=sys.stderr)
    sys.exit(2)
trials = [r for r in rows if r.get("kind") == "trial" and r.get("scenario") in cells]
hashes = {r["config_hash"] for r in trials}
runs = [r for r in rows if r.get("kind") == "run" and r.get("config_hash") in hashes]
spent = sum(float(r.get("cost_usd_est") or 0) for r in runs)
seen = {}
for r in trials:
    if r.get("status") != "completed":
        continue
    seen.setdefault(int(r.get("repeat", -1)), set()).add(r["scenario"])
complete = sorted(k for k, s in seen.items() if s >= cells)
complete_hashes = {
    r["config_hash"]
    for r in trials
    if r.get("status") == "completed" and int(r.get("repeat", -1)) in complete
}
per_pass = {k: 0.0 for k in complete}
for r in runs:
    if r.get("config_hash") not in complete_hashes:
        continue
    k = int(next(t["repeat"] for t in trials if t["config_hash"] == r["config_hash"]))
    if k in per_pass:
        per_pass[k] += float(r.get("cost_usd_est") or 0)
forecast = sum(per_pass.values()) / len(per_pass) if per_pass else first
print(f"{spent:.2f} {forecast:.2f} {len(complete)}")
PY
}

# Fail CLOSED: a non-numeric field (empty string from a failed iter2_stats, or garbage)
# must stop the runner, never be read as "cap not reached".
_require_numeric() {
  case "$1" in
    ''|*[!0-9.]*) echo "$2: '$1' is not numeric — iter2_stats failed; stopping" >&2; exit 9 ;;
  esac
}

retried_unarmed=0
for k in $(seq "$START" "$N"); do
  read -r spent forecast done_passes <<< "$(iter2_stats)"
  _require_numeric "$spent" "spend"
  _require_numeric "$forecast" "forecast"
  if uv run python -c "import sys; sys.exit(0 if float('$spent') + float('$forecast') > float('$SPEND_CAP') else 1)"; then
    echo "FORECAST CAP: spent \$$spent + forecast \$$forecast (mean of $done_passes completed iter2 pass(es)) > cap \$$SPEND_CAP — not starting pass $k"
    exit 6
  fi
  echo "== ITER2 PASS $k / $N  ($(date -u +%H:%M:%SZ))  spent so far \$$spent, forecast \$$forecast =="
  PASSLOG="$STREAMS/iter2-pass-$k.log"

  RUN_ARGS=(run "$BANK" --scenarios-dir "$SDIR" --repeats "$k" --max-spawn-usd 20 --max-run-usd "$CAP")
  ARMED_ARGS=()
  if [ -f "$STREAMS/iter2-arming.txt" ]; then
    ARMED_ARGS=(--skip-arming-check)
  fi
  uv run fathom "${RUN_ARGS[@]}" "${ARMED_ARGS[@]}" > "$PASSLOG" 2>&1
  rc=$?
  grep -E "planned:|completed|errored|infrastructure|ceiling|max-run|Traceback|Error|drift|arming" "$PASSLOG" | tail -12

  case "$rc" in
    0) : ;;
    10)
      seat_dead "$PASSLOG" && echo "SEAT/INFRASTRUCTURE (exit 10) during pass $k — stopping (resume with START=$k after re-login)"
      exit 10
      ;;
    11)
      if [ "$retried_unarmed" -eq 0 ]; then
        echo "UNARMED (exit 11) during pass $k — possible transient probe failure; retrying once after 60s"
        retried_unarmed=1
        sleep 60
        uv run fathom "${RUN_ARGS[@]}" "${ARMED_ARGS[@]}" > "$PASSLOG" 2>&1
        rc=$?
        grep -E "planned:|completed|errored|infrastructure|ceiling|max-run|Traceback|Error|drift|arming" "$PASSLOG" | tail -12
        if [ "$rc" -ne 0 ]; then
          echo "UNARMED (exit $rc) again after retry during pass $k — stopping (resume with START=$k)"
          exit 11
        fi
      else
        echo "UNARMED (exit 11) during pass $k, already retried once this run — stopping (resume with START=$k)"
        exit 11
      fi
      ;;
    12)
      echo "BANK INVALID (exit 12) during pass $k — stopping"
      exit 12
      ;;
    14)
      echo "RUN BUDGET (exit 14) during pass $k — stopping (resume with START=$k)"
      exit 14
      ;;
    *)
      echo "fathom run exited $rc during pass $k — stopping (resume with START=$k)"
      exit "$rc"
      ;;
  esac
  if grep -q "fixture drift" "$PASSLOG"; then echo "FIXTURE DRIFT during pass $k — stopping; restore fixtures/ and void the trial"; exit 4; fi
  read -r spent forecast done_passes <<< "$(iter2_stats)"
  _require_numeric "$spent" "spend"
  echo "cumulative est spend on the iter2 cells: \$$spent  (completed passes: $done_passes)"
  EXPOLOG="$STREAMS/iter2-exposure-$k.txt"
  if ! uv run python tools/stream_facts.py --ledger "$LEDGER" --streams "$STREAMS_ABS" \
      --task-dir-name "$BANK" --task-dir "$FATHOM_TASK_DIR" --exposure --fail-on-exposure > "$EXPOLOG" 2>&1; then
    cat "$EXPOLOG"
    echo "EXPOSURE after pass $k — stopping; void the exposed trial(s) before resuming"
    exit 7
  fi
  if [ ! -f "$STREAMS/iter2-arming.txt" ]; then
    ARMLOG="$STREAMS/iter2-arming.txt"
    uv run python tools/stream_facts.py --ledger "$LEDGER" --streams "$STREAMS_ABS" \
        --task-dir-name "$BANK" --task-dir "$FATHOM_TASK_DIR" --per-trial --arming-check --repeat 0 > "$ARMLOG" 2>&1
    arc=$?
    cat "$ARMLOG"
    if [ "$arc" -ne 0 ]; then rm -f "$ARMLOG"; echo "ARMING FAILED on the first completed pass — stopping"; exit 8; fi
  fi
  _require_numeric "$spent" "spend"
  if uv run python -c "import sys; sys.exit(0 if float('$spent') >= float('$SPEND_CAP') else 1)"; then echo "ITER2 SPEND CAP \$$SPEND_CAP reached — stopping"; exit 5; fi
done
echo "== ITER2 MATRIX DONE =="
