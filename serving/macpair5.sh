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
#
# B5_ARMS=off|on|both (default both) selects which arms to run under the single
# load. The cross-model sweep uses off: every model in the comparison has to be
# measured the same way, and the reasoning arm is a separate axis that not every
# model even has.
set -u

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../harness" && pwd)"
OUT="${B4_OUT:?set B4_OUT}"
LMS="${LMS:-$HOME/.lmstudio/bin/lms}"
KEY="$1"; MODEL="$2"; CTX="${3:-32768}"
ARMS="${B5_ARMS:-both}"

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

# Hand the measured window to the harness so a reasoning budget larger than the
# window is clamped to what fits instead of being rejected by the server. This
# is a no-op at 208384/262144; it matters at 32768, where the 20 SQL prompts
# (~930 tokens of schema each) plus a 32000-token floor overflow by ~170.
export B4_WINDOW="$WIN"

if [ "$ARMS" = "off" ] || [ "$ARMS" = "both" ]; then
  echo "---- $KEY off arm (reasoning suppressed, greedy) @ window $WIN"
  B4_THINK=0 B4_COT=0 B4_PROFILES='{}' \
    python3 -u b5.py run "$MODEL" "$OUT/hb_$KEY.json" || exit 1

  NOW=$(actual_ctx)
  [ "$NOW" = "$WIN" ] || { echo "ABORT: window changed $WIN -> $NOW mid-run"; exit 1; }
fi

if [ "$ARMS" = "on" ] || [ "$ARMS" = "both" ]; then
  # "On" is not one thing. A model with a trained thinking mode gets it enabled;
  # a model without one gets the prompted-CoT arm, which b3 reports separately
  # because asking in the prompt is not the same as a trained mode. Sending
  # B4_THINK=1 to a model that cannot think produces an arm b5.py labels "plain"
  # -- a duplicate of the off arm, an hour of GPU for nothing.
  NATIVE=$(python3 -c "import b3,sys; print(1 if b3.can_think(sys.argv[1]) else 0)" "$MODEL")
  # A missing chosen_<key>.json must not fall back to default sampling in
  # silence: for a thinking arm that is the difference between a measured
  # temperature and an unmeasured one.
  PROF="${B5_PROFILES:-$(python3 mkprofiles.py "$KEY=$MODEL")}" || {
    echo "ABORT: no sampling profile for $KEY -- run hardtemp.py and write chosen_$KEY.json"
    exit 1; }
  if [ "$NATIVE" = "1" ]; then
    echo "---- $KEY on arm (NATIVE thinking, budget $THINK_BUDGET) @ window $WIN"
    ARM_ENV="B4_THINK=1 B4_COT=0"
  else
    echo "---- $KEY on arm (prompted CoT -- no native thinking mode) @ window $WIN"
    ARM_ENV="B4_THINK=0 B4_COT=1"
  fi
  # Retries are per-model, not a constant. One resample of a non-terminating
  # task costs a full budget of generation, so on a model that will not stop,
  # RETRIES=2 triples the arm. It was hardcoded here, which silently overrode
  # the caller and made a "0 retries" re-run of GLM run 3 attempts anyway.
  env $ARM_ENV B4_BUDGET="$THINK_BUDGET" B4_BUDGET_MULT=1 \
    B4_RETRIES="${B4_RETRIES:-2}" \
    B4_ESCALATE="${B4_ESCALATE:-1.0,1.15}" B4_PROFILES="$PROF" \
    python3 -u b5.py run "$MODEL" "$OUT/ht_$KEY.json" || exit 1
fi

FIN=$(actual_ctx)
[ "$FIN" = "$WIN" ] || echo "WARNING: window ended at $FIN, started $WIN"
echo "######## $KEY HARD TIER DONE -- arms=$ARMS at window $WIN"; date
