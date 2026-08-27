#!/bin/bash
# The complete concurrency x instance x batch-invariance matrix, on q35's off arm.
#
# WHY THIS EXISTS. The project concluded "4 workers destroys reproducibility, 1
# worker fixes it" from 46/104 identical at 4 workers against 104/104 at 1. Those
# two numbers were not measured the same way:
#
#   46/104   hb_q35 (cudapair5.sh) vs hb_q35.run2 (cuda_phase2.sh)
#            -> two DIFFERENT container instances
#   104/104  hb_q35.w1a vs hb_q35.w1b (cuda_phase3.sh, a for-loop)
#            -> the SAME container instance, twice
#
# Within-instance was compared against cross-instance and the worker count took
# the credit. Today's 1-worker run settles that it was wrong: identical flags,
# identical KV cache (119,954 tokens), 1 worker -- and 29/104 against w1a, WORSE
# than 4 workers managed. Outputs agree for 17-515 chars then diverge
# mid-generation: floating-point reduction order, not settings.
#
# vLLM documents the cause and ships a fix. Kernels pick different reduction
# schedules for different batch shapes; float addition is not associative; so
# temperature 0 does not imply bit-identical logits across serving conditions.
# VLLM_BATCH_INVARIANT=1 forces a fixed reduction order. Present in 0.22.1 --
# verified in the running container, not assumed.
#
# THE MATRIX. 3 worker counts x 2 kernel modes = 6 conditions. Each condition
# gets three runs: a and b back-to-back in ONE instance, then c in a FRESH one.
# a-vs-b isolates concurrency; c-vs-a isolates the restart. 15 new runs (stock
# 1w is already covered by w1a / w1b / w1).
#
# The off arm is the probe throughout: greedy, fast, and reproducibility IS the
# question. A thinking arm would add its spiral as a confound.
set -u
cd /root/bench2
OUT=/root/b5out
export B4_OUT=$OUT B4_TMP=/root/b5tmp B4_CHOSEN_DIR=$OUT
export B5_WARN_HOURS=4 B5_ABORT_HOURS=6
export B4_RETRIES=0 B4_WINDOW=40960
MODEL=RedHatAI/Qwen3.5-9B-FP8-dynamic
mkdir -p $OUT /root/b5tmp

restore() {
  echo; echo "######## restoring gemma4-vllm"
  docker rm -f bench-model >/dev/null 2>&1
  cd /root/vllm-new && docker compose up -d
  sleep 5; docker ps --format "{{.Names}}\t{{.Status}}" | grep -i gemma4 || echo "RESTORE CHECK FAILED"
}
trap restore EXIT INT TERM

echo "waiting for cuda_w1.sh to finish..."
while pgrep -f 'cuda_w[1].sh' >/dev/null; do sleep 120; done
echo "w1 sweep finished $(date)"

# cuda_w1.sh's exit trap restores gemma4-vllm, which binds port 8000. launch()
# only removes bench-model, so without this every cell dies instantly with
# "Bind for 0.0.0.0:8000 failed: port is already allocated" -- and the matrix
# burns through all five conditions in about ten seconds. The trap at the bottom
# of this script brings the container back when the matrix is done.
cd /root/vllm-new && docker compose down; cd /root/bench2

wait_up() {
  for i in $(seq 1 150); do
    docker logs bench-model 2>&1 | grep -q "Application startup complete" && return 0
    docker logs bench-model 2>&1 | grep -qE "ValueError|Traceback|OutOfMemory|EngineDeadError" && return 1
    sleep 10
  done; return 1
}
launch() {
  docker rm -f bench-model >/dev/null 2>&1; sleep 5
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
    -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    $1 vllm/vllm-openai:v0.22.1 \
    --model $MODEL --host 0.0.0.0 --port 8000 \
    --max-model-len 40960 --gpu-memory-utilization 0.93 --max-num-seqs 8 \
    --max-num-batched-tokens 4096 --enforce-eager --dtype auto --kv-cache-dtype fp8 \
    --limit-mm-per-prompt '{"image": 0, "video": 0}' \
    --reasoning-parser qwen3 --trust-remote-code >/dev/null
  wait_up || { echo "!!!! LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -15; return 1; }
  docker logs bench-model 2>&1 | grep -E "GPU KV cache size" | tail -1
}
preflight() {
  for i in $(seq 1 30); do
    curl -s -m 60 http://localhost:8000/v1/chat/completions -H 'Content-Type: application/json' \
      -d '{"model":"'"$MODEL"'","messages":[{"role":"user","content":"say ok"}],"max_tokens":5}' \
      | grep -q '"content"' && return 0
    sleep 10
  done; echo "!!!! PREFLIGHT FAILED"; return 1
}
off_arm() {
  [ -f "$OUT/hb_$1.graded.json" ] && { echo "---- $1 already done, skipping"; return 0; }
  echo "---- off arm  key=$1  workers=$2  $(date '+%H:%M:%S')"
  preflight || return 1
  B4_THINK=0 B4_COT=0 B4_PROFILES='{}' B4_WORKERS=$2 \
    python3 -u b5.py run "$MODEL" "$OUT/hb_$1.json" || { echo "!!!! $1 nonzero"; return 1; }
  python3 -u b5.py grade "$OUT/hb_$1.json" | tail -2
}

# $1 label  $2 env args  $3 workers  $4 key prefix
condition() {
  echo; echo "=============== $1"
  launch "$2" && { off_arm "$4a" "$3"; off_arm "$4b" "$3"; } || return 1
  echo "--- fresh instance for the cross-restart cell"
  launch "$2" && off_arm "$4c" "$3"
}

echo "######## COMPLETE CONCURRENCY MATRIX"; date

condition "stock kernels, 2 workers"            ""                          2 q35.w2
condition "stock kernels, 4 workers"            ""                          4 q35.w4
condition "batch-invariant, 1 worker"           "-e VLLM_BATCH_INVARIANT=1" 1 q35.bi1
condition "batch-invariant, 2 workers"          "-e VLLM_BATCH_INVARIANT=1" 2 q35.bi2
condition "batch-invariant, 4 workers"          "-e VLLM_BATCH_INVARIANT=1" 4 q35.bi4

echo; echo "######## MATRIX RESULTS"
python3 - <<'PY'
import json, os
def items(k):
    p="/root/b5out/hb_%s.json"%k
    return json.load(open(p))["items"] if os.path.exists(p) else None
def score(k):
    p="/root/b5out/hb_%s.graded.json"%k
    if not os.path.exists(p): return "--"
    g=json.load(open(p))["results"]
    return str(sum(1 for v in g.values() if v["ok"])) if len(g)==104 else "part"
def rep(a,b):
    x,y=items(a),items(b)
    if not x or not y: return "     --     "
    c=[k for k in x if k in y]
    s=sum(1 for k in c if (x[k].get("text") or "")==(y[k].get("text") or ""))
    return "%3d/%-3d (%3.0f%%)" % (s,len(c),100*s/max(len(c),1))
print()
print("  %-26s %-16s %-16s %s" % ("condition","same instance","across restart","scores"))
print("  " + "-"*76)
for lbl,a,b,c in [
  ("stock       1 worker",  "q35.w1a","q35.w1b","q35.w1"),
  ("stock       2 workers", "q35.w2a","q35.w2b","q35.w2c"),
  ("stock       4 workers", "q35.w4a","q35.w4b","q35.w4c"),
  ("invariant   1 worker",  "q35.bi1a","q35.bi1b","q35.bi1c"),
  ("invariant   2 workers", "q35.bi2a","q35.bi2b","q35.bi2c"),
  ("invariant   4 workers", "q35.bi4a","q35.bi4b","q35.bi4c"),
]:
    print("  %-26s %-16s %-16s %s / %s / %s"
          % (lbl, rep(a,b), rep(c,a), score(a), score(b), score(c)))
print()
print("  same instance  = two passes, one server process  -> isolates concurrency")
print("  across restart = third pass, fresh server        -> isolates the restart")
PY
echo; echo "######## MATRIX DONE"; date
