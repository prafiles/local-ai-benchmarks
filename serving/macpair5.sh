#!/bin/bash
# Hard tier, both arms under ONE load. Same window discipline as macpair.sh --
# read that file for why the context window is held rather than requested.
#
# WHAT IS DIFFERENT HERE: the budgets.
#
# b3 gave a Python task 900 output tokens and a shell task 220, and the reasoning
# arm a floor of 8000. On the hard tier those numbers would measure the cap
# instead of the model. Two pieces of evidence say so. Qwen3.8-27B spent its
# entire 8000-token reasoning budget on 24 of the 600 b3 tasks and returned no
# answer at all -- on the 576 it did answer it scored 535 -> 556, so those 24
# were a budget artefact, not a capability result. And the hard tasks are simply
# longer: a streaming RFC 4180 parser or a recursive template-literal type does
# not fit in 900 tokens even written perfectly.
#
# So: per-task output budgets rise 3-4x (set in b5.py), and the reasoning floor
# rises from 8000 to 32000. That is a real cost -- roughly 4x the wall clock per
# reasoning task -- which is affordable only because the tier is 104 tasks rather
# than 600.
#
#   macpair5.sh <key> <model> [ctx-request]
set -u

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../harness" && pwd)"
OUT="${B4_OUT:?set B4_OUT}"
LMS="${LMS:-$HOME/.lmstudio/bin/lms}"
KEY="$1"; MODEL="$2"; CTX="${3:-32768}"

export B4_URL="${B4_URL:-http://localhost:1234/v1/chat/completions}"
export B4_TMP="${B4_TMP:-$OUT/tmp/run5}"
export B4_OUT="$OUT" B4_WORKERS=1
export B4_OFF_MECH=reasoning_effort
export B4_THINK_CAPABLE="${B4_THINK_CAPABLE:-qwen3.6,qwen3.8,glm-4.7}"
# A 32000-token trace at ~12 tok/s is 45 minutes. The b3 default of 1800s would
# time out mid-thought and record it as an empty answer -- which is exactly the
# artefact this tier's larger budgets exist to remove.
export B4_TIMEOUT="${B4_TIMEOUT:-5400}"
THINK_BUDGET="${B5_THINK_BUDGET:-32000}"
mkdir -p "$OUT" "$B4_TMP"; cd "$HARNESS"

actual_ctx() {
  "$LMS" ps --json 2>/dev/null | python3 -c "
import json,sys
rows=json.load(sys.stdin) or []
print(rows[0].get('contextLength') if rows else '')"
}

echo "######## HARD TIER  $KEY -- $MODEL"; date
if [ "${B5_ASSUME_LOADED:-0}" = "1" ]; then
  WIN=$(actual_ctx)
  [ -n "$WIN" ] || { echo "nothing loaded and B5_ASSUME_LOADED=1"; exit 1; }
  echo "using the already-resident model at window $WIN"
else
  "$LMS" unload --all >/dev/null 2>&1
  "$LMS" load "$MODEL" --context-length "$CTX" --parallel 1 --gpu max -y >/dev/null 2>&1
  WIN=$(actual_ctx)
  [ -n "$WIN" ] || { echo "LOAD FAILED $MODEL"; exit 1; }
  echo "loaded once: requested $CTX, actual window $WIN -- both arms will use it"
fi
echo "$WIN" > "$OUT/window5_$KEY.txt"

echo "---- $KEY off arm (reasoning suppressed, greedy) @ window $WIN"
B4_THINK=0 B4_COT=0 B4_PROFILES='{}' \
  python3 -u b5.py run "$MODEL" "$OUT/hb_$KEY.json" || exit 1

NOW=$(actual_ctx)
[ "$NOW" = "$WIN" ] || { echo "ABORT: window changed $WIN -> $NOW mid-run"; exit 1; }

echo "---- $KEY on arm (native thinking, budget $THINK_BUDGET) @ window $WIN"
B4_THINK=1 B4_COT=0 B4_BUDGET="$THINK_BUDGET" B4_BUDGET_MULT=1 B4_RETRIES=2 \
  B4_ESCALATE="${B4_ESCALATE:-1.0,1.15}" \
  B4_PROFILES="${B5_PROFILES:-$(python3 mkprofiles.py "$KEY=$MODEL" 2>/dev/null || echo '{}')}" \
  python3 -u b5.py run "$MODEL" "$OUT/ht_$KEY.json" || exit 1

FIN=$(actual_ctx)
[ "$FIN" = "$WIN" ] || echo "WARNING: window ended at $FIN, started $WIN"
echo "######## $KEY HARD TIER DONE -- both arms at window $WIN"; date
