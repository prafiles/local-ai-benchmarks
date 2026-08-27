#!/bin/bash
# A second off arm for GLM-4.7-Flash GGUF, with room to finish its answers.
#
# The standard off arm caps ~47% of its tasks: the model writes long ANSWERS
# (0 reasoning traces -- checked, reasoning_effort does suppress correctly here),
# and the per-task budgets are 5000/1500/800/1000. Its thinking arm meanwhile
# runs at 32000. So the off->on gap for this model is partly budget, not
# reasoning. Every other model caps 0-3 times, which is why this never mattered
# before.
#
# This does NOT replace the standard arm. That one stays, because it is what is
# comparable across models; this one is what makes the within-model delta mean
# something. Different key, nothing overwritten.
set -u
REPO=/Volumes/Store/Developer/AER/local-ai-benchmarks
LMS="$HOME/.lmstudio/bin/lms"
MODEL=glm-4.7-flash
WIN=40960

# Gate on the sweep PROCESS being gone, not on a log marker. The first version
# waited for "GGUF SWEEP DONE|SWEEP ABORTED", which only the happy path writes:
# glm47gguf's thinking arm aborted via a b5.py RuntimeError, run_one returned 1,
# and the driver exited through `|| exit 1` without printing either marker. The
# waiter would have sat there forever. Silence is not success.
echo "waiting for the main sweep process to exit..."
while pgrep -f "sweep_res[t].sh" >/dev/null; do sleep 60; done
echo "sweep process gone $(date) -- starting the raised-budget off arm"

export B4_OUT="$REPO/results/hard" B4_TMP="$REPO/results/hard/tmp/run5"
export B4_URL=http://localhost:1234/v1/chat/completions
export B4_WORKERS=1 B4_OFF_MECH=reasoning_effort B4_TIMEOUT=5400
export B4_WINDOW="$WIN"
mkdir -p "$B4_TMP"

"$LMS" unload --all >/dev/null 2>&1
"$LMS" load "$MODEL" --context-length "$WIN" --parallel 1 --gpu max -y >/dev/null 2>&1
curl -s -m 180 http://localhost:1234/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"'"$MODEL"'","messages":[{"role":"user","content":"say ok"}],"max_tokens":5}' \
  | grep -q '"content"' || { echo "!!!! PREFLIGHT FAILED"; exit 1; }
echo "preflight ok"

cd "$REPO/harness"
# 4x: py/js/ts 5000->20000, sql 1500->6000, git 1000->4000, sh 800->3200.
# BUDGET_MULT reached the off arm only as of today's b3 change; before it, the
# thinking arm was the only one that could be given more room.
B4_THINK=0 B4_COT=0 B4_PROFILES='{}' B4_BUDGET_MULT=4 B4_RETRIES=0 \
  python3 -u b5.py run "$MODEL" "$B4_OUT/hb_glm47gguf.b4x.json" || exit 1
python3 -u b5.py grade "$B4_OUT/hb_glm47gguf.b4x.json"
echo "######## GLM RAISED-BUDGET OFF ARM DONE"; date
