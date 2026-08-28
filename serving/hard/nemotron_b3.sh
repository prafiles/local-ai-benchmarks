#!/bin/bash
# Hand the b3 phase off from the running driver, so it runs with 0 retries.
#
# WHY THIS EXISTS. nemotron.sh was launched before the thinking arm revealed
# that this model fails to terminate on ~24% of hard-tier tasks. Its b3 phase
# therefore inherits macpair.sh's hardcoded B4_RETRIES=2, and editing the
# running script cannot change that: the whole body is one `{ ... } | tee`
# compound command, which bash parses in full before executing, so the live
# process is running from memory and ignores the file.
#
# Retries=2 on THIS model is both a confound and a time bomb. A retry is only
# ever spent on an empty answer, so a model that terminates never sees one --
# but this model returns empty on a quarter of tasks at 32000, and b3's floor is
# 8000, so the rate there will be higher, not lower. Every one of those tasks
# would be generated three times, and the 2nd and 3rd draws are HOTTER than the
# greedy off arm they are compared against. That is the Gemma 4 26B +22 -> +28
# confound, bought at triple the wall clock.
#
# So: wait for the hard tier to finish AND grade, stop the old driver before it
# reaches b3, and run b3 here with retries 0 and everything else identical.
set -u

REPO=/Volumes/Store/Developer/AER/local-ai-benchmarks
MODEL=nvidia-nemotron-3.5-lightning-30b-a3b
KEY=nemotron
CTX=40960
LOG=~/bench5/nemotron_b3.log

export B4_THINK_CAPABLE=nemotron
export LMS="$HOME/.lmstudio/bin/lms"

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
    echo "preflight attempt $i: no completion yet"; sleep 10
  done
  echo "PREFLIGHT FAILED -- refusing to record a dead server as results"
  return 1
}

{
echo "### b3 handoff armed $(date) -- waiting for the hard tier to finish and grade"

# The graded file is the signal: it only exists once the thinking arm completed
# AND grade() wrote it, so waiting on it cannot cut grading short.
while [ ! -f "$REPO/results/hard/ht_$KEY.graded.json" ]; do sleep 20; done
echo "### hard tier graded $(date)"

# Stop the old driver before its b3 phase gets anywhere. Kill the process group
# leader's children first so a half-loaded model does not linger.
PID=$(pgrep -f "bash nemotron.sh" | head -1)
if [ -n "${PID:-}" ]; then
  echo "### stopping old driver pid $PID before its b3 phase"
  pkill -f "b3.py run" 2>/dev/null
  kill "$PID" 2>/dev/null
  sleep 5
fi

preflight || exit 1
echo; echo "=================== B3 SUITE (600 tasks, both arms, retries 0)"
B4_OUT="$REPO/results/mac" B4_RETRIES=0 \
  bash "$REPO/serving/macpair.sh" "$KEY" "$MODEL" "$CTX" || {
    echo "B3 FAILED"; exit 1; }

echo; echo "--- grading b3"
cd "$REPO/harness"
python3 -u b3.py grade "$REPO/results/mac/b_$KEY.json" || echo "grade off arm failed"
python3 -u b3.py grade "$REPO/results/mac/t_$KEY.json" || echo "grade on arm failed"

echo; echo "### B3 COMPLETE"; date
} 2>&1 | tee "$LOG"
