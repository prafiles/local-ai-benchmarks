#!/bin/bash
# Qwen3.8-Flash-Next, hard tier only, BOTH arms, on a node that is also serving
# live traffic.
#
# WHY BOTH ARMS AGAIN. The earlier off arm finished cleanly (104/104, 0 caps, 0
# empties) but it ran BEFORE the vLLM tuning. Pairing a pre-tuning off arm with
# a post-tuning thinking arm would put a serving-config change inside the very
# comparison the pair exists to make -- the same class of error as comparing a
# budget-3000 run against a budget-5000 one and calling the difference noise.
# So both arms are re-run under the current configuration.
#
# WHY THIS ONE DOES NOT REFUSE TO START. Every other driver here aborts when the
# node has traffic in flight. This node now serves live traffic permanently and
# must not be touched, so refusing would mean never measuring it. The confound
# is therefore RECORDED instead of avoided: a sampler writes the in-flight count
# every 30s for the life of the run, so the contention is a column in the
# results rather than a guess afterwards.
#
# What that does and does not cost:
#   - OUR concurrency is still 1. B4_WORKERS=1, one request outstanding at a
#     time, so the harness contributes no parallelism of its own.
#   - The SERVER still batches our request with live traffic, and batching
#     changes numerics -- this project measured that directly: vLLM's own
#     batch-invariant mode tops out at 71% byte-identical and costs 2-3 tasks.
#     So byte-reproducibility is not expected here and is not claimed.
#   - Both arms run under the same conditions, so the confound is symmetric
#     rather than sitting on one side of the comparison.
set -u

REPO=/Volumes/Store/Developer/AER/llm/local-ai-benchmarks
HOSTPORT="${SPARK_HOST:-10.0.0.21:8000}"
MODEL=Qwen/Qwen3.8-Flash-Next
KEY=q38flash
OUT="$REPO/results/spark"
LOG=~/bench5/spark_q38flash_shared.log
CONT="$OUT/contention_$KEY.tsv"

export B4_URL="http://$HOSTPORT/v1/chat/completions"
export B4_OUT="$OUT" B4_CHOSEN_DIR="$OUT" B4_TMP="$OUT/tmp"
export B4_WORKERS=1
export B4_OFF_MECH=template
export B4_THINK_CAPABLE=qwen3.8
export B4_RETRIES=0
export B4_TIMEOUT=5400
export B4_WINDOW=262144
mkdir -p "$OUT" "$B4_TMP"

# Contention sampler. Our run holds at most 1 request, so running<=1 is us alone
# and running>1 means we shared the batch. Runs for the life of the driver.
( while :; do
    curl -s -m 10 "http://$HOSTPORT/metrics" 2>/dev/null | awk -v t="$(date '+%F %T')" '
      /^vllm:num_requests_running\{/{r=$2} /^vllm:num_requests_waiting\{/{w=$2}
      END{printf "%s\t%s\t%s\n", t, r, w}' >> "$CONT"
    sleep 30
  done ) &
SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null' EXIT
[ -s "$CONT" ] || printf "time\trunning\twaiting\n" > "$CONT"

{
echo "######## Qwen3.8-Flash-Next -- hard tier, shared node, 1 worker"; date

# Preflight proves the server answers and is the model we mean. It does NOT
# gate on traffic here -- that is the deliberate difference from the other
# drivers, and the sampler above is what makes it defensible.
RESIDENT=$(curl -s -m 20 "http://$HOSTPORT/v1/models" | python3 -c "import json,sys
try:
    d=json.load(sys.stdin)['data'][0]; print(d['id'], d['max_model_len'])
except Exception: print('')" 2>/dev/null)
[ -n "$RESIDENT" ] || { echo "PREFLIGHT: no model listed"; exit 1; }
echo "resident: $RESIDENT"
echo "$RESIDENT" | grep -q "Qwen3.8-Flash-Next" || { echo "PREFLIGHT: unexpected model"; exit 1; }
echo "live traffic at start: $(curl -s -m 10 "http://$HOSTPORT/metrics" | awk '/^vllm:num_requests_running\{/{print $2}')"

ANS=$(curl -s -m 300 "$B4_URL" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"reply with the single word ready\"}],\"max_tokens\":3000,\"temperature\":0,\"chat_template_kwargs\":{\"enable_thinking\":false}}" \
  | python3 -c "import json,sys
try:
    d=json.load(sys.stdin); print((d['choices'][0]['message'].get('content') or '').strip()[:40])
except Exception: print('')" 2>/dev/null)
[ -n "$ANS" ] || { echo "PREFLIGHT: no completion -- refusing to record a dead server as results"; exit 1; }
echo "preflight ok: model answered '$ANS'"

cd "$REPO/harness"
PROF=$(python3 mkprofiles.py "$KEY=qwen3.8-flash-next") || { echo "ABORT: no profile"; exit 1; }
echo "profile: $PROF"

echo; echo "---- off arm (thinking disabled via template, greedy, 1 worker)"
B4_THINK=0 B4_COT=0 B4_PROFILES="$PROF" \
  python3 -u b5.py run "$MODEL" "$OUT/hb_$KEY.json" || exit 1

echo; echo "---- on arm (NATIVE thinking, greedy, budget 32000, 1 worker)"
B4_THINK=1 B4_COT=0 B4_BUDGET=32000 B4_BUDGET_MULT=1 B4_PROFILES="$PROF" \
  python3 -u b5.py run "$MODEL" "$OUT/ht_$KEY.json" || exit 1

echo; echo "--- grading"
python3 -u b5.py grade "$OUT/hb_$KEY.json" || echo "grade off failed"
python3 -u b5.py grade "$OUT/ht_$KEY.json" || echo "grade on failed"

echo; echo "--- contention over the run"
# -F'\t' is required, not cosmetic: the timestamp contains a space, so default
# field splitting makes $2 the TIME and the test silently compares a clock string
# against 1. That reported 0% shared -- a false claim of EXCLUSIVITY -- on a run
# that was actually shared 98% of the time.
awk -F'\t' 'NR>1{n++; r=$2+0; if(r>1) shared++; if(r>mx) mx=r} END{
  printf "  %d samples, %d with other traffic in the batch (%.0f%%), max concurrent %d\n",
         n, shared, n?100*shared/n:0, mx}' "$CONT"

echo; echo "######## Q38FLASH HARD TIER COMPLETE"; date
} 2>&1 | tee "$LOG"
