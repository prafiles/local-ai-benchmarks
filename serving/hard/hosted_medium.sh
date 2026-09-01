#!/bin/bash
# Sonnet 5 and Luna on the hard tier: one arm each, medium effort, 32K limit.
#
# Single arm, so these are standalone capability scores in the same category as
# the thinking-only models -- not reasoning deltas. Both APIs also fix their own
# temperature (Luna rejects 0, Sonnet deprecates the field), so neither is greedy
# and both carry the wide non-greedy noise floor this project measured: 4-8 tasks
# per repeat.
#
# Everything goes through api_proxy.py so b5.py, the task set, the extractor and
# the graders are byte-identical to every local run.
set -u
REPO=/Volumes/Store/Developer/AER/llm/local-ai-benchmarks
OUT="$REPO/results/hosted"
source ~/.bench_anthropic_env
source ~/.bench_openai_env

export B4_URL=http://localhost:8900/v1/chat/completions
export B4_OUT="$OUT" B4_CHOSEN_DIR="$OUT" B4_TMP="$OUT/tmp"
export B4_WORKERS=1
export B4_OFF_MECH=reasoning_effort
export B4_THINK_EFFORT=medium
export B4_THINK_CAPABLE=luna,sonnet
export B4_RETRIES=0
export B4_TIMEOUT=5400
mkdir -p "$OUT" "$B4_TMP"

# The proxy must be up and answering before 104 tasks are spent against it: a
# dead endpoint records connection errors as no-answer RESULTS and reports DONE.
pgrep -f api_proxy.py >/dev/null || { cd ~/bench5 && nohup python3 -u api_proxy.py >> proxy.log 2>&1 & sleep 4; }

{
echo "######## hosted models, hard tier, medium effort, 32K"; date
cd "$REPO/harness"

for PAIR in "luna=gpt-5.6-luna" "sonnet5=claude-sonnet-5"; do
  KEY="${PAIR%%=*}"; MODEL="${PAIR#*=}"
  echo; echo "=================== $KEY -- $MODEL"

  ANS=$(curl -s -m 600 "$B4_URL" -H 'content-type: application/json' \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"reply with the single word ready\"}],\"max_tokens\":2000,\"reasoning_effort\":\"medium\"}" \
    | python3 -c "import json,sys
try:
    d=json.load(sys.stdin); print((d['choices'][0]['message'].get('content') or '').strip()[:40])
except Exception: print('')" 2>/dev/null)
  [ -n "$ANS" ] || { echo "PREFLIGHT FAILED for $MODEL -- skipping"; continue; }
  echo "preflight ok: '$ANS'"

  PROF=$(python3 mkprofiles.py "$KEY=$MODEL") || { echo "no profile for $KEY"; continue; }
  echo "profile: $PROF"

  B4_THINK=1 B4_COT=0 B4_BUDGET=32000 B4_BUDGET_MULT=1 B4_PROFILES="$PROF" \
    python3 -u b5.py run "$MODEL" "$OUT/ht_$KEY.json" || { echo "$KEY RUN FAILED"; continue; }
  python3 -u b5.py grade "$OUT/ht_$KEY.json" || echo "$KEY grade failed"
done

echo; echo "######## HOSTED COMPLETE"; date
} 2>&1 | tee ~/bench5/hosted_medium.log
