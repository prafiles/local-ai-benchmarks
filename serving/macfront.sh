#!/bin/bash
# Front-load every cheap step and every decision, so the expensive arms can then
# run unattended.
#
# The on arm costs ~4.3h per model (measured: median 1321 tokens and 26s per task
# on gemma-4-26b at 1 slot). The off arm costs ~0.3h and the temperature sweep
# ~0.3h, and only the sweep needs a judgement call -- which sampling profile to
# record in chosen_<key>.json. Running one model end-to-end at a time would put a
# decision point every 4.6h and leave the machine idle between a notification and
# an answer. So: all off arms and all sweeps first, all profiles written in one
# sitting, then a single uninterrupted chain of on arms.
#
# Off arms are also the half that cannot fail for interesting reasons -- greedy,
# reasoning suppressed, short answers -- so getting them all banked early means a
# later crash costs only reasoning runs, which are the resumable ones.
#
#   macfront.sh <key>=<model-id> [...]
set -u

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../harness" && pwd)"
OUT="${B4_OUT:?set B4_OUT}"
LMS="${LMS:-$HOME/.lmstudio/bin/lms}"
CTX="${CTX:-32768}"

export B4_URL="${B4_URL:-http://localhost:1234/v1/chat/completions}"
export B4_TMP="${B4_TMP:-$OUT/tmp/run}"
export B4_OUT="$OUT"
export B4_WORKERS=1
export B4_OFF_MECH=reasoning_effort
export B4_THINK_CAPABLE="${B4_THINK_CAPABLE:-qwen3.6}"

mkdir -p "$OUT" "$B4_TMP"
cd "$HARNESS"

for spec in "$@"; do
  KEY="${spec%%=*}"; MODEL="${spec#*=}"
  echo; echo "################ $KEY -- $MODEL"; date

  "$LMS" unload --all >/dev/null 2>&1
  "$LMS" load "$MODEL" --context-length "$CTX" --parallel 1 --gpu max -y >/dev/null 2>&1 \
    || { echo "LOAD FAILED $MODEL"; continue; }
  echo "loaded at ctx=$CTX, 1 slot"

  echo "---- $KEY off arm (reasoning suppressed, greedy)"
  B4_THINK=0 B4_COT=0 B4_PROFILES='{}' \
    python3 -u b3.py run "$MODEL" "$OUT/b_$KEY.json" || echo "OFF ARM FAILED $KEY"

  # Does thinking terminate at temperature 0 on this model? If it does, both arms
  # can run at identical sampling and the temperature confound that the published
  # report has to declare simply does not apply here. Worth one extra config to
  # find out rather than inheriting a conclusion measured on other models.
  echo "---- $KEY temperature sweep (greedy included)"
  B4_HARD_CONFIGS='t0/greedy=0,-,- t0.6/k20=0.6,0.95,20 t0.8/k20=0.8,0.95,20 t1.0/k64=1.0,0.95,64' \
    python3 -u hardtemp.py "$MODEL" 8000 2 2>&1 | tee "$OUT/hardtemp_$KEY.log"
  mv "$OUT/hardtemp.json" "$OUT/hardtemp_$KEY.json" 2>/dev/null
done

echo; echo "################ FRONT-LOAD DONE"; date
echo "write chosen_<key>.json for each model, then run the on arms"
