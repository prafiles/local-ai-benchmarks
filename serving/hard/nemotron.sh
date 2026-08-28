#!/bin/bash
# Nemotron 3.5 Lightning 30B A3B (GGUF Q4_K_M) -- the complete benchmark.
#
# Both suites, both arms each: the 104-task hard tier first (it is the tier the
# project reports on now, and it is the shorter of the two), then the 600-task
# b3 suite for continuity with the older ranking.
#
# WHY THE ARMS ARE CLEAN HERE. Sampling was measured at the budget the run uses
# (32000, not 8000 -- tuning below the run's budget is what hid the Qwen3.5 and
# GLM spirals): 6 probes, one per category, greedy thinking, 0/6 capped and 0/6
# empty. So greedy works on BOTH arms and the pair differs in exactly one thing.
# Retries are therefore 0 on the hard tier: the retry ladder resamples hotter on
# an empty answer, and that is the confound that inflated Gemma 26B from +22 to
# +28. A model that does not return empties does not need it.
#
# THE ARM SWITCH WAS PROBED, NOT ASSUMED. reasoning_effort=none really suppresses
# reasoning on this build (0 chars vs 1397 at baseline); every chat_template_kwargs
# form is silently ignored; low/medium are byte-identical to sending nothing, so
# the ON arm sends nothing. See results/mac/chosen_nemotron.json.
set -u

REPO=/Volumes/Store/Developer/AER/local-ai-benchmarks
MODEL=nvidia-nemotron-3.5-lightning-30b-a3b
KEY=nemotron
CTX=40960          # every other GGUF run on this tier used 40960; GGUF honours
                   # --context-length, so the window is a control here, not an
                   # observation the way it is on MLX.
LOG=~/bench5/nemotron.log

export B4_THINK_CAPABLE=nemotron
export B4_CHOSEN_DIR="$REPO/results/mac"
export LMS="$HOME/.lmstudio/bin/lms"

# ---------------------------------------------------------------- preflight
# LM Studio's service and its HTTP server are independent processes. A dead
# server does not fail the run: b5.py records each "Connection refused" as a
# no-answer RESULT and reports DONE, which silently turns a dead server into a
# 0/104 capability score. This has happened three times on this project, so the
# gate is a real completion, not a port check.
preflight() {
  "$LMS" server start >/dev/null 2>&1
  for i in $(seq 1 30); do
    ANS=$(curl -s -m 120 http://localhost:1234/v1/chat/completions \
            -H 'Content-Type: application/json' \
            -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"reply with the single word ready\"}],\"max_tokens\":2000,\"temperature\":0,\"reasoning_effort\":\"none\"}" \
          | python3 -c "import json,sys
try:
    d=json.load(sys.stdin); print((d['choices'][0]['message'].get('content') or '').strip()[:40])
except Exception: print('')" 2>/dev/null)
    [ -n "$ANS" ] && { echo "preflight ok: model answered '$ANS'"; return 0; }
    echo "preflight attempt $i: no completion yet, retrying"; sleep 10
  done
  echo "PREFLIGHT FAILED -- refusing to run and record a dead server as results"
  return 1
}

{
echo "######################## NEMOTRON 3.5 COMPLETE BENCHMARK"; date
echo "model=$MODEL  ctx=$CTX  greedy both arms, retries 0 on the hard tier"

# ------------------------------------------------------- 1. hard tier (b5)
preflight || exit 1
echo; echo "=================== HARD TIER (104 tasks, both arms)"
B4_OUT="$REPO/results/hard" B4_RETRIES=0 \
  bash "$REPO/serving/macpair5.sh" "$KEY" "$MODEL" "$CTX" || {
    echo "HARD TIER FAILED"; exit 1; }

echo; echo "--- grading hard tier"
cd "$REPO/harness"
python3 -u b5.py grade "$REPO/results/hard/hb_$KEY.json" || echo "grade off arm failed"
python3 -u b5.py grade "$REPO/results/hard/ht_$KEY.json" || echo "grade on arm failed"

# ------------------------------------------------------ 2. 600-task suite
preflight || exit 1
echo; echo "=================== B3 SUITE (600 tasks, both arms)"
# Retries 0 here too, for the same two reasons as the hard tier and one more
# that is specific to this model. (1) A resample is drawn hotter than the greedy
# off arm it is compared against -- the Gemma 26B +22->+28 confound. (2) This
# model does not terminate on ~24% of hard-tier tasks, and b3's reasoning floor
# is 8000 rather than 32000, so the non-termination rate here will be higher,
# not lower. At retries=2 every one of those tasks would be generated three
# times, tripling an arm that is already the longest phase of the run for
# answers that the first attempt already showed will not arrive.
B4_OUT="$REPO/results/mac" B4_RETRIES=0 \
  bash "$REPO/serving/macpair.sh" "$KEY" "$MODEL" "$CTX" || {
    echo "B3 FAILED"; exit 1; }

echo; echo "--- grading b3"
cd "$REPO/harness"
python3 -u b3.py grade "$REPO/results/mac/b_$KEY.json" || echo "grade off arm failed"
python3 -u b3.py grade "$REPO/results/mac/t_$KEY.json" || echo "grade on arm failed"

echo; echo "######################## NEMOTRON COMPLETE"; date
} 2>&1 | tee "$LOG"
