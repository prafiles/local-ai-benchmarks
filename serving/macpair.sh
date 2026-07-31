#!/bin/bash
# Both arms of a model under ONE load, and the window recorded with the results.
#
# WHY THIS REPLACES RUNNING THE ARMS SEPARATELY.
#
# The context window is not inert. Measured on glm-4.7-flash: greedy is fully
# deterministic at a fixed window (40/40 identical on a repeat run), but only
# 374/600 of the same tasks match between a 32768 and a 128000 load. So the window
# is an experimental variable of the same kind as temperature.
#
# It also cannot be pinned by asking. `lms load --context-length 32768` returned an
# actual 32768 for three models one minute and 262144 for one of those same models
# the next -- the mapping depends on system state at load time, not on the request.
# gemma-4-26b's original arms were caught by exactly this: 3 of 25 sampled off-arm
# tasks failed to reproduce at the on arm's 262144, while all 8 control tasks
# reproduced at a fixed window, which says the two arms ran at different windows.
# With deltas of +26/+15/+12 out of 600 and a window effect touching 12-38% of
# outputs, that confound can exceed the signal it is meant to measure.
#
# Since the window cannot be requested reliably, it is instead HELD: load once,
# run both arms against that same resident model, never unload in between. The
# actual window is read back and written next to the results, so a future run can
# tell whether it is comparable rather than having to re-derive it by experiment.
#
#   macpair.sh <key> <model> [ctx-request]
set -u

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../harness" && pwd)"
OUT="${B4_OUT:?set B4_OUT}"
LMS="${LMS:-$HOME/.lmstudio/bin/lms}"
KEY="$1"; MODEL="$2"; CTX="${3:-32768}"

export B4_URL="${B4_URL:-http://localhost:1234/v1/chat/completions}"
export B4_TMP="${B4_TMP:-$OUT/tmp/run}"
export B4_OUT="$OUT" B4_CHOSEN_DIR="$OUT" B4_WORKERS=1
export B4_OFF_MECH=reasoning_effort
export B4_THINK_CAPABLE="${B4_THINK_CAPABLE:-qwen3.6,glm-4.7}"
mkdir -p "$OUT" "$B4_TMP"; cd "$HARNESS"

actual_ctx() {
  "$LMS" ps --json 2>/dev/null | python3 -c "
import json,sys
rows=json.load(sys.stdin) or []
print(rows[0].get('contextLength') if rows else '')"
}

echo "######## $KEY -- $MODEL"; date
"$LMS" unload --all >/dev/null 2>&1
"$LMS" load "$MODEL" --context-length "$CTX" --parallel 1 --gpu max -y >/dev/null 2>&1
WIN=$(actual_ctx)
[ -n "$WIN" ] || { echo "LOAD FAILED $MODEL"; exit 1; }
echo "loaded once: requested $CTX, actual window $WIN -- both arms will use it"
echo "$WIN" > "$OUT/window_$KEY.txt"

echo "---- $KEY off arm (reasoning suppressed, greedy) @ window $WIN"
B4_THINK=0 B4_COT=0 B4_PROFILES='{}' \
  python3 -u b3.py run "$MODEL" "$OUT/b_$KEY.json" || exit 1

if [ ! -f "$OUT/chosen_$KEY.json" ]; then
  echo "---- $KEY temperature sweep @ window $WIN"
  B4_HARD_CONFIGS="${B4_HARD_CONFIGS:-t0/greedy=0,-,- t0.6/k20=0.6,0.95,20 t0.8/k20=0.8,0.95,20 t1.0/k64=1.0,0.95,64}" \
    python3 -u hardtemp.py "$MODEL" 8000 2 2>&1 | tee "$OUT/hardtemp_$KEY.log"
  mv -f "$OUT/hardtemp.json" "$OUT/hardtemp_$KEY.json" 2>/dev/null
  echo "!! write $OUT/chosen_$KEY.json from the sweep, then re-run -- the model"
  echo "!! stays loaded, so the on arm will still get window $WIN" >&2
  exit 2
fi

# Guard against the window having moved under us (a TTL unload plus a JIT reload
# would silently give the on arm a different window from the off arm).
NOW=$(actual_ctx)
[ "$NOW" = "$WIN" ] || { echo "ABORT: window changed $WIN -> $NOW mid-run"; exit 1; }

echo "---- $KEY on arm (native thinking, budget 8000) @ window $WIN"
B4_THINK=1 B4_COT=0 B4_BUDGET=8000 B4_BUDGET_MULT=1 B4_RETRIES=2 \
  B4_ESCALATE="${B4_ESCALATE:-1.0,1.15}" \
  B4_PROFILES="$(python3 mkprofiles.py "$KEY=$MODEL")" \
  python3 -u b3.py run "$MODEL" "$OUT/t_$KEY.json" || exit 1

FIN=$(actual_ctx)
[ "$FIN" = "$WIN" ] || echo "WARNING: window ended at $FIN, started $WIN"
echo "######## $KEY DONE -- both arms at window $WIN"; date
