#!/bin/bash
# Nemotron 3 Super 120B-A12B (NVFP4) on the Spark node, both suites, both arms.
#
# No load/unload here: the server is not ours to restart, so the model is taken
# as resident and the window is READ and recorded rather than requested. Same
# discipline as macpair5.sh's B5_ASSUME_LOADED path -- the window is an
# experimental variable, so it is pinned to the results either way.
#
# Single-variable by construction: greedy on BOTH arms, one worker, no retries.
# The arm switch is chat_template_kwargs (probed -- reasoning_effort is silently
# ignored on THIS model, though it is the working switch on the other Nemotron).
set -u

REPO=/Volumes/Store/Developer/AER/llm/local-ai-benchmarks
# Node address comes from the environment: this is a public repo.
#   SPARK_HOST=host:port bash spark_nemotron3.sh
HOSTPORT="${SPARK_HOST:?set SPARK_HOST, e.g. SPARK_HOST=<host>:8000}"
URL=http://$HOSTPORT/v1/chat/completions
MODEL=nvidia/nemotron-3-super
KEY=nemotron3
OUT="$REPO/results/spark"
LOG=~/bench5/spark_nemotron3.log

export B4_URL="$URL"
export B4_OUT="$OUT" B4_CHOSEN_DIR="$OUT" B4_TMP="$OUT/tmp"
export B4_WORKERS=1
export B4_OFF_MECH=template
export B4_THINK_CAPABLE=nemotron
export B4_RETRIES=0
export B4_TIMEOUT=5400
mkdir -p "$OUT" "$B4_TMP"

# A dead or swapped-out server records connection errors as no-answer RESULTS and
# reports DONE -- this repo shipped two 0/104 "capability results" that way before
# the gate existed. So: prove a real completion, and prove it is the model we mean.
preflight() {
  RESIDENT=$(curl -s -m 20 http://$HOSTPORT/v1/models \
    | python3 -c "import json,sys
try:
    d=json.load(sys.stdin)['data'][0]; print(d['id'], d['max_model_len'])
except Exception: print('')" 2>/dev/null)
  [ -n "$RESIDENT" ] || { echo "PREFLIGHT: no model listed"; return 1; }
  echo "resident: $RESIDENT"
  WIN=$(echo "$RESIDENT" | awk '{print $2}')
  echo "$WIN" > "$OUT/window5_$KEY.txt"
  export B4_WINDOW="$WIN"

  BUSY=$(curl -s -m 15 http://$HOSTPORT/metrics \
    | awk '/^vllm:num_requests_running\{/{print $2}')
  echo "in-flight requests not ours: ${BUSY:-unknown}"
  case "${BUSY:-1}" in
    0|0.0) ;;
    *) echo "WARNING: node is serving other traffic -- results would be"
       echo "         concurrency-confounded. Refusing to start."; return 1;;
  esac

  ANS=$(curl -s -m 300 "$URL" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"reply with the single word ready\"}],\"max_tokens\":3000,\"temperature\":0,\"chat_template_kwargs\":{\"enable_thinking\":false}}" \
    | python3 -c "import json,sys
try:
    d=json.load(sys.stdin); print((d['choices'][0]['message'].get('content') or '').strip()[:40])
except Exception: print('')" 2>/dev/null)
  [ -n "$ANS" ] || { echo "PREFLIGHT: no completion -- refusing to record a dead server as results"; return 1; }
  echo "preflight ok: model answered '$ANS' at window $WIN"
}

{
echo "######## Nemotron 3 Super 120B-A12B -- Spark"; date
preflight || exit 1

PROF=$(cd "$REPO/harness" && python3 mkprofiles.py "$KEY=nemotron-3-super") || {
  echo "ABORT: no sampling profile"; exit 1; }
echo "profile: $PROF"

cd "$REPO/harness"

echo; echo "=================== HARD TIER (104 tasks)"
echo "---- $KEY off arm (thinking disabled via template, greedy)"
B4_THINK=0 B4_COT=0 B4_PROFILES="$PROF" \
  python3 -u b5.py run "$MODEL" "$OUT/hb_$KEY.json" || exit 1

echo "---- $KEY on arm (NATIVE thinking, greedy, budget 32000)"
B4_THINK=1 B4_COT=0 B4_BUDGET=32000 B4_BUDGET_MULT=1 B4_PROFILES="$PROF" \
  python3 -u b5.py run "$MODEL" "$OUT/ht_$KEY.json" || exit 1

echo; echo "--- grading hard tier"
python3 -u b5.py grade "$OUT/hb_$KEY.json" || echo "grade off failed"
python3 -u b5.py grade "$OUT/ht_$KEY.json" || echo "grade on failed"

preflight || exit 1
echo; echo "=================== B3 SUITE (600 tasks)"
echo "---- $KEY off arm"
B4_THINK=0 B4_COT=0 B4_PROFILES="$PROF" \
  python3 -u b3.py run "$MODEL" "$OUT/b_$KEY.json" || exit 1

echo "---- $KEY on arm (native thinking, budget 8000)"
B4_THINK=1 B4_COT=0 B4_BUDGET=8000 B4_BUDGET_MULT=1 B4_PROFILES="$PROF" \
  python3 -u b3.py run "$MODEL" "$OUT/t_$KEY.json" || exit 1

echo; echo "--- grading b3"
python3 -u b3.py grade "$OUT/b_$KEY.json" || echo "grade b3 off failed"
python3 -u b3.py grade "$OUT/t_$KEY.json" || echo "grade b3 on failed"

echo; echo "######## SPARK COMPLETE"; date
} 2>&1 | tee "$LOG"
